"""Execution — strike selection, mleg order building/submission, deterministic exit manager.

Owner: lane A. No LLM anywhere in this module.
Trades are tracked in data/trades.jsonl (our source of truth for exits); Alpaca positions are
the reconciliation check.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import broker
from . import marketdata as md

ET = ZoneInfo("America/New_York")
TRADES = Path(__file__).resolve().parent.parent / "data" / "trades.jsonl"


@dataclass
class Trade:
    id: str
    underlying: str
    structure: str
    expiration: str
    legs: list[dict]          # [{symbol, side, ratio_qty, position_intent}]
    contracts: int
    entry_credit: float       # per 1-lot, dollars (positive = we received)
    width: float
    max_loss: float           # total dollars at risk
    thesis: str
    opened_at: str
    status: str = "open"      # open | closed
    exit_reason: str | None = None
    exit_debit: float | None = None
    pnl: float | None = None


# ---------- strike selection ----------

def _mid(snap: dict) -> float:
    q = snap.get("latestQuote") or {}
    bp, ap = q.get("bp"), q.get("ap")
    if bp and ap:
        return (bp + ap) / 2
    t = snap.get("latestTrade") or {}
    return t.get("p", 0.0)


def _by_type_delta(chain: dict, cp: str) -> list[tuple[float, float, str, float]]:
    """-> sorted list of (abs_delta, strike, symbol, mid) for one option type."""
    out = []
    for sym, s in chain.items():
        g = s.get("greeks")
        _, _, c, k = md.parse_occ(sym)
        if c != cp or not g:
            continue
        out.append((abs(g["delta"]), k, sym, _mid(s)))
    return sorted(out)


def select_condor(chain: dict, short_delta: float, width: float) -> dict | None:
    puts = _by_type_delta(chain, "P")
    calls = _by_type_delta(chain, "C")
    if not puts or not calls:
        return None
    sp = min(puts, key=lambda r: abs(r[0] - short_delta))
    sc = min(calls, key=lambda r: abs(r[0] - short_delta))
    lp = min((r for r in puts if r[1] < sp[1] - 0.01), key=lambda r: abs((sp[1] - r[1]) - width), default=None)
    lc = min((r for r in calls if r[1] > sc[1] + 0.01), key=lambda r: abs((r[1] - sc[1]) - width), default=None)
    if not lp or not lc:
        return None
    credit = (sp[3] - lp[3]) + (sc[3] - lc[3])
    put_w, call_w = sp[1] - lp[1], lc[1] - sc[1]
    return {
        "legs": [
            {"symbol": sp[2], "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
            {"symbol": lp[2], "side": "buy", "ratio_qty": "1", "position_intent": "buy_to_open"},
            {"symbol": sc[2], "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
            {"symbol": lc[2], "side": "buy", "ratio_qty": "1", "position_intent": "buy_to_open"},
        ],
        "credit": credit,
        "width": max(put_w, call_w),
        "strikes": {"sp": sp[1], "lp": lp[1], "sc": sc[1], "lc": lc[1]},
    }


def select_vertical(chain: dict, cp: str, short_delta: float, width: float) -> dict | None:
    legs_src = _by_type_delta(chain, cp)
    if not legs_src:
        return None
    short = min(legs_src, key=lambda r: abs(r[0] - short_delta))
    if cp == "P":
        long_ = min((r for r in legs_src if r[1] < short[1] - 0.01),
                    key=lambda r: abs((short[1] - r[1]) - width), default=None)
        intent = "put_credit_spread"
    else:
        long_ = min((r for r in legs_src if r[1] > short[1] + 0.01),
                    key=lambda r: abs((r[1] - short[1]) - width), default=None)
        intent = "call_credit_spread"
    if not long_:
        return None
    credit = short[3] - long_[3]
    return {
        "legs": [
            {"symbol": short[2], "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
            {"symbol": long_[2], "side": "buy", "ratio_qty": "1", "position_intent": "buy_to_open"},
        ],
        "credit": credit,
        "width": abs(short[1] - long_[1]),
        "strikes": {"short": short[1], "long": long_[1]},
        "kind": intent,
    }


def size(width: float, credit: float, nav: float, risk_per_trade: float, mult: float) -> int:
    """Contracts such that total max loss <= risk_per_trade * nav * mult."""
    per_contract_loss = (width - credit) * 100
    if per_contract_loss <= 0:
        return 0
    budget = risk_per_trade * nav * mult
    return max(int(budget // per_contract_loss), 0)


# ---------- submission ----------

def open_trade(sig, sel: dict, contracts: int, thesis: str, mode: str) -> Trade | None:
    if contracts < 1:
        return None
    credit = round(sel["credit"], 2)
    tid = f"{sig.underlying}-{datetime.now(ET):%Y%m%dT%H%M%S}"
    t = Trade(
        id=tid, underlying=sig.underlying, structure=sig.structure, expiration=sig.expiration,
        legs=sel["legs"], contracts=contracts, entry_credit=credit * 100, width=sel["width"],
        max_loss=(sel["width"] - credit) * 100 * contracts, thesis=thesis,
        opened_at=datetime.now(ET).isoformat(),
    )
    if mode == "live":
        # limit at ~92% of mid credit so it rests just inside the market; loop repricing handles the rest
        broker.submit_mleg(t.legs, contracts, limit_price=max(credit * 0.92, 0.01))
    _append(t)
    return t


def manage_exits(params, mode: str) -> list[dict]:
    """Deterministic. Close at take-profit / stop / expiry-day. Returns actions taken."""
    actions = []
    now = datetime.now(ET)
    for t in _load_open():
        chain = md.option_chain_snapshot(t.underlying, expiration_date=t.expiration)
        debit = _combo_cost_to_close(t, chain)          # $ per 1-lot to buy it back
        if debit is None:
            continue
        credit = t.entry_credit
        take = credit * (1 - params.take_profit_frac)
        stop = credit * params.stop_multiple
        exp_day = date.fromisoformat(t.expiration) == now.date()
        reason = None
        if debit <= take:
            reason = "take_profit"
        elif debit >= stop:
            reason = "stop"
        elif exp_day and now.strftime("%H:%M") >= "15:45":
            reason = "expiry_close"
        if not reason:
            continue
        if mode == "live":
            close_legs = [
                {**leg, "side": "buy" if leg["side"] == "sell" else "sell",
                 "position_intent": leg["position_intent"].replace("_open", "_close")}
                for leg in t.legs
            ]
            broker.submit_mleg(close_legs, t.contracts, limit_price=max(debit * 1.08, 0.01))
        t.status = "closed"
        t.exit_reason = reason
        t.exit_debit = round(debit * t.contracts, 2)
        t.pnl = round(credit * t.contracts - debit * t.contracts, 2)
        _rewrite(t)
        actions.append({"trade": t.id, "reason": reason, "pnl": t.pnl})
    return actions


def _combo_cost_to_close(t: Trade, chain: dict) -> float | None:
    total = 0.0
    for leg in t.legs:
        s = chain.get(leg["symbol"])
        if not s:
            return None
        m = _mid(s)
        total += m if leg["side"] == "sell" else -m   # buy back shorts, sell longs
    return total


# ---------- trade log ----------

def _append(t: Trade) -> None:
    TRADES.parent.mkdir(exist_ok=True)
    with TRADES.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(t)) + "\n")


def _load_all() -> list[Trade]:
    if not TRADES.exists():
        return []
    seen: dict[str, Trade] = {}
    for line in TRADES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            seen[d["id"]] = Trade(**d)
    return list(seen.values())


def _load_open() -> list[Trade]:
    return [t for t in _load_all() if t.status == "open"]


def _rewrite(updated: Trade) -> None:
    all_ = {t.id: t for t in _load_all()}
    all_[updated.id] = updated
    with TRADES.open("w", encoding="utf-8") as f:
        for t in all_.values():
            f.write(json.dumps(asdict(t)) + "\n")
