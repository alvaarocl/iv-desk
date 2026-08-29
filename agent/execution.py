"""Execution — strike selection, mleg order building/submission, deterministic exit manager.

Owner: lane/ejecucion. No LLM anywhere in this module.

**Units.** Two currencies live here and mixing them was a live bug (issue #2):

- *per-share* prices (what Alpaca quotes and what `limit_price` expects) — suffixed `_ps`.
- *dollars per 1-lot* = per-share x 100 — everything stored on `Trade` and every threshold
  comparison. Never compare across the two.

**Order lifecycle.** Alpaca orders are asynchronous: a 200 confirms receipt, not execution
(issue #3). A trade is only `open` once its entry order reports `filled`; until then it is
`pending_open` and holds its risk budget but is never treated as a position.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import broker
from . import marketdata as md

ET = ZoneInfo("America/New_York")
TRADES = Path(__file__).resolve().parent.parent / "data" / "trades.jsonl"

# Liquidity gate (strategy-spec.md). Kept module-local so `config.Params` stays lane/senal's file;
# a `Params` field of the same name wins when it exists.
MIN_OI = 500
MAX_SPREAD_FRAC = 0.10

# How long to wait for an entry/exit fill inside one loop before leaving it pending.
FILL_POLL_ATTEMPTS = 4
FILL_POLL_SLEEP_S = 1.5

# A resting entry older than this is cancelled rather than chased across loops.
PENDING_ENTRY_MAX_MIN = 20

OPEN_STATES = ("pending_open", "open", "pending_close")
DEAD_ORDER_STATES = ("canceled", "cancelled", "expired", "rejected", "replaced", "done_for_day")


@dataclass
class Trade:
    id: str
    underlying: str
    structure: str
    expiration: str
    legs: list[dict]              # [{symbol, side, ratio_qty, position_intent}]
    contracts: int
    entry_credit: float           # $ per 1-lot, positive = we collect
    width: float                  # per-share width of the widest wing
    max_loss: float               # total $ at risk across all contracts
    thesis: str
    opened_at: str
    client_order_id: str = ""
    entry_order_id: str | None = None
    exit_order_id: str | None = None
    status: str = "pending_open"  # pending_open | open | pending_close | closed | cancelled
    exit_reason: str | None = None
    exit_debit: float | None = None
    pnl: float | None = None
    notes: list[str] = field(default_factory=list)


# ---------- quotes & liquidity ----------

def _mid_ps(snap: dict) -> float | None:
    """Per-share mid from a two-sided quote, or None.

    Never falls back to 0.0: a zero silently inflates the condor credit, which then inflates
    sizing and can push a garbage structure past the credit gate (issue #22).
    """
    q = snap.get("latestQuote") or {}
    bid, ask = q.get("bp"), q.get("ap")
    if bid and ask and bid > 0 and ask > 0 and ask >= bid:
        return (bid + ask) / 2
    return None


def _spread_frac(snap: dict) -> float | None:
    q = snap.get("latestQuote") or {}
    bid, ask = q.get("bp"), q.get("ap")
    if not (bid and ask and bid > 0 and ask > 0 and ask >= bid):
        return None
    mid = (bid + ask) / 2
    return (ask - bid) / mid if mid > 0 else None


def _liquid(sym: str, snap: dict, oi: dict[str, int], min_oi: int, max_spread: float) -> bool:
    # Open interest is T-2 and not always present for every strike. When we have an OI table,
    # enforce the floor; when it's absent entirely (backtest, or OI feed down), fall back to the
    # spread test alone rather than rejecting every strike.
    if oi and oi.get(sym, 0) <= min_oi:
        return False
    sf = _spread_frac(snap)
    return sf is not None and sf <= max_spread


def _by_type_delta(
    chain: dict, cp: str, oi: dict[str, int], min_oi: int, max_spread: float
) -> list[tuple[float, float, str, float]]:
    """-> sorted [(abs_delta, strike, symbol, mid_ps)] for one option type, liquid contracts only."""
    out = []
    for sym, s in chain.items():
        g = s.get("greeks")
        if not g:
            continue
        _, _, c, k = md.parse_occ(sym)
        if c != cp:
            continue
        mid = _mid_ps(s)
        if mid is None or mid <= 0:
            continue
        if not _liquid(sym, s, oi, min_oi, max_spread):
            continue
        out.append((abs(g["delta"]), k, sym, mid))
    return sorted(out)


def _gate(params) -> tuple[int, float]:
    return (
        int(getattr(params, "min_oi", MIN_OI)),
        float(getattr(params, "max_spread_frac", MAX_SPREAD_FRAC)),
    )


# ---------- strike selection ----------

def select_condor(chain: dict, short_delta: float, width: float, oi: dict, params) -> dict | None:
    min_oi, max_spread = _gate(params)
    puts = _by_type_delta(chain, "P", oi, min_oi, max_spread)
    calls = _by_type_delta(chain, "C", oi, min_oi, max_spread)
    if not puts or not calls:
        return None
    sp = min(puts, key=lambda r: abs(r[0] - short_delta))
    sc = min(calls, key=lambda r: abs(r[0] - short_delta))
    lp = min((r for r in puts if r[1] < sp[1] - 0.01),
             key=lambda r: abs((sp[1] - r[1]) - width), default=None)
    lc = min((r for r in calls if r[1] > sc[1] + 0.01),
             key=lambda r: abs((r[1] - sc[1]) - width), default=None)
    if not lp or not lc:
        return None
    credit_ps = (sp[3] - lp[3]) + (sc[3] - lc[3])
    if credit_ps <= 0:
        return None
    return {
        "legs": [
            {"symbol": sp[2], "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
            {"symbol": lp[2], "side": "buy", "ratio_qty": "1", "position_intent": "buy_to_open"},
            {"symbol": sc[2], "side": "sell", "ratio_qty": "1", "position_intent": "sell_to_open"},
            {"symbol": lc[2], "side": "buy", "ratio_qty": "1", "position_intent": "buy_to_open"},
        ],
        "credit": credit_ps,
        "width": max(sp[1] - lp[1], lc[1] - sc[1]),
        "strikes": {"sp": sp[1], "lp": lp[1], "sc": sc[1], "lc": lc[1]},
    }


def select_vertical(
    chain: dict, cp: str, short_delta: float, width: float, oi: dict, params
) -> dict | None:
    min_oi, max_spread = _gate(params)
    legs_src = _by_type_delta(chain, cp, oi, min_oi, max_spread)
    if not legs_src:
        return None
    short = min(legs_src, key=lambda r: abs(r[0] - short_delta))
    if cp == "P":
        long_ = min((r for r in legs_src if r[1] < short[1] - 0.01),
                    key=lambda r: abs((short[1] - r[1]) - width), default=None)
        kind = "put_credit_spread"
    else:
        long_ = min((r for r in legs_src if r[1] > short[1] + 0.01),
                    key=lambda r: abs((r[1] - short[1]) - width), default=None)
        kind = "call_credit_spread"
    if not long_:
        return None
    credit_ps = short[3] - long_[3]
    if credit_ps <= 0:
        return None
    return {
        "legs": [
            {"symbol": short[2], "side": "sell", "ratio_qty": "1",
             "position_intent": "sell_to_open"},
            {"symbol": long_[2], "side": "buy", "ratio_qty": "1", "position_intent": "buy_to_open"},
        ],
        "credit": credit_ps,
        "width": abs(short[1] - long_[1]),
        "strikes": {"short": short[1], "long": long_[1]},
        "kind": kind,
    }


def size(width_ps: float, credit_ps: float, nav: float, risk_per_trade: float, mult: float) -> int:
    """Contracts such that total max loss <= risk_per_trade * nav * mult. Inputs per-share."""
    per_contract_loss = (width_ps - credit_ps) * 100
    if per_contract_loss <= 0:
        return 0
    budget = risk_per_trade * nav * mult
    return max(int(budget // per_contract_loss), 0)


# ---------- submission ----------

def _client_order_id(underlying: str, expiration: str, structure: str, now: datetime) -> str:
    """Deterministic per trade intent, so a re-run or manual dispatch cannot double-submit."""
    return f"ivd-{underlying}-{expiration}-{structure[:4]}-{now:%Y%m%d-%H%M}"[:48]


def _close_legs(legs: list[dict]) -> list[dict]:
    return [
        {**leg,
         "side": "buy" if leg["side"] == "sell" else "sell",
         "position_intent": leg["position_intent"].replace("_open", "_close")}
        for leg in legs
    ]


def _await_fill(order_id: str) -> dict | None:
    """Poll briefly for a terminal state. Returns the last order seen (None if it vanished)."""
    last = None
    for i in range(FILL_POLL_ATTEMPTS):
        last = broker.get_order(order_id=order_id)
        if not last:
            return None
        if last.get("status") in ("filled",) + DEAD_ORDER_STATES:
            return last
        if i < FILL_POLL_ATTEMPTS - 1:
            time.sleep(FILL_POLL_SLEEP_S)
    return last


def _filled_credit_ps(order: dict, fallback_ps: float) -> float:
    """Per-share credit actually collected. mleg credits come back signed; magnitude is ours."""
    raw = order.get("filled_avg_price")
    try:
        return abs(float(raw)) if raw not in (None, "") else fallback_ps
    except (TypeError, ValueError):
        return fallback_ps


def open_trade(sig, sel: dict, contracts: int, thesis: str, mode: str) -> Trade | None:
    """Submit the entry as a signed-credit mleg limit and persist the resulting lifecycle state."""
    if contracts < 1:
        return None
    now = datetime.now(ET)
    credit_ps = round(sel["credit"], 2)
    coid = _client_order_id(sig.underlying, sig.expiration, sig.structure, now)
    t = Trade(
        id=coid,
        underlying=sig.underlying, structure=sig.structure, expiration=sig.expiration,
        legs=sel["legs"], contracts=contracts,
        entry_credit=credit_ps * 100,
        width=sel["width"],
        max_loss=(sel["width"] - credit_ps) * 100 * contracts,
        thesis=thesis, opened_at=now.isoformat(), client_order_id=coid,
    )

    if mode != "live":
        t.status = "open"          # dry_run: book it locally so the rest of the loop exercises
        t.notes.append("dry_run — no order placed")
        _append(t)
        return t

    if broker.get_order(client_order_id=coid):
        t.notes.append("duplicate client_order_id — not resubmitted")
        _append(t)
        return t

    # Signed limit: NEGATIVE opens a credit structure. Sitting ~8% inside the mid leaves room
    # for the repricing pass without crossing the spread on entry.
    limit_ps = -abs(credit_ps * 0.92)
    order = broker.submit_mleg(t.legs, contracts, limit_ps, client_order_id=coid)
    t.entry_order_id = order.get("id")

    final = _await_fill(t.entry_order_id) if t.entry_order_id else None
    status = (final or {}).get("status")
    if status == "filled":
        got_ps = _filled_credit_ps(final, credit_ps)
        t.entry_credit = got_ps * 100
        t.max_loss = (t.width - got_ps) * 100 * contracts
        t.status = "open"
    elif status in DEAD_ORDER_STATES:
        t.status = "cancelled"
        t.notes.append(f"entry {status}")
    else:
        t.status = "pending_open"
    _append(t)
    return t


# ---------- reconciliation (issue #3) ----------

def reconcile(mode: str) -> list[dict]:
    """Alpaca is the source of truth. Resolve pending orders and flag anything unexpected.

    Runs before exits so the book the exit manager sees matches the broker.
    """
    events: list[dict] = []
    now = datetime.now(ET)

    for t in _load_active():
        if t.status == "pending_open" and t.entry_order_id:
            o = broker.get_order(order_id=t.entry_order_id)
            st = (o or {}).get("status")
            if st == "filled":
                got_ps = _filled_credit_ps(o, t.entry_credit / 100)
                t.entry_credit = got_ps * 100
                t.max_loss = (t.width - got_ps) * 100 * t.contracts
                t.status = "open"
                _rewrite(t)
                events.append({"trade": t.id, "resolved": "entry_filled"})
            elif not o or st in DEAD_ORDER_STATES:
                t.status = "cancelled"
                t.notes.append(f"entry resolved {st or 'missing'}")
                _rewrite(t)
                events.append({"trade": t.id, "resolved": f"entry_{st or 'missing'}"})
            else:
                age_min = (now - datetime.fromisoformat(t.opened_at)).total_seconds() / 60
                if age_min > PENDING_ENTRY_MAX_MIN and mode == "live":
                    broker.cancel_order(t.entry_order_id)
                    t.status = "cancelled"
                    t.notes.append(f"entry stale after {age_min:.0f}m — cancelled")
                    _rewrite(t)
                    events.append({"trade": t.id, "resolved": "entry_stale_cancelled"})

        elif t.status == "pending_close" and t.exit_order_id:
            o = broker.get_order(order_id=t.exit_order_id)
            st = (o or {}).get("status")
            if st == "filled":
                debit_ps = _filled_credit_ps(o, (t.exit_debit or 0) / 100 / max(t.contracts, 1))
                _finalize_close(t, debit_ps)
                events.append({"trade": t.id, "resolved": "exit_filled", "pnl": t.pnl})
            elif not o or st in DEAD_ORDER_STATES:
                t.status = "open"          # close did not happen — put it back on the book
                t.exit_order_id = None
                t.notes.append(f"exit {st or 'missing'} — reopened for retry")
                _rewrite(t)
                events.append({"trade": t.id, "resolved": f"exit_{st or 'missing'}_retry"})

    events.extend(_unexpected_equity_positions())
    return events


def _unexpected_equity_positions() -> list[dict]:
    """Early assignment on an ITM short leg leaves real shares in the account (issue #25).

    We do not try to trade out of it here — we surface it so the loop can go exits-only.
    """
    out = []
    for p in broker.positions():
        if (p.get("asset_class") or "") != "us_option":
            out.append({
                "alert": "unexpected_equity_position",
                "symbol": p.get("symbol"), "qty": p.get("qty"),
                "market_value": p.get("market_value"),
            })
    return out


def has_unexpected_equity() -> bool:
    return bool(_unexpected_equity_positions())


# ---------- exits ----------

def _combo_cost_to_close(t: Trade, chain: dict) -> float | None:
    """$ per 1-lot to buy the structure back. None if any leg lacks a usable quote."""
    total_ps = 0.0
    for leg in t.legs:
        s = chain.get(leg["symbol"])
        if not s:
            return None
        m = _mid_ps(s)
        if m is None:
            return None
        total_ps += m if leg["side"] == "sell" else -m
    return total_ps * 100


def _finalize_close(t: Trade, debit_ps: float) -> None:
    t.status = "closed"
    t.exit_debit = round(debit_ps * 100 * t.contracts, 2)
    t.pnl = round(t.entry_credit * t.contracts - debit_ps * 100 * t.contracts, 2)
    _rewrite(t)


def manage_exits(params, mode: str) -> list[dict]:
    """Deterministic. Take-profit / stop / expiry-day close. All comparisons in $ per 1-lot."""
    actions = []
    now = datetime.now(ET)
    for t in _load_all():
        if t.status != "open":
            continue
        chain = md.option_chain_snapshot(t.underlying, expiration_date=t.expiration)
        debit = _combo_cost_to_close(t, chain)     # $ per 1-lot
        if debit is None:
            t.notes.append("no quote for every leg — exit skipped this loop")
            _rewrite(t)
            continue

        credit = t.entry_credit                     # $ per 1-lot
        take = credit * (1 - params.take_profit_frac)
        stop = credit * params.stop_multiple
        # Widened from a single >=15:45 run: GitHub cron is best-effort and a skipped run used to
        # mean the position rode into expiration (issue #23). Any run from 15:30 closes it.
        expiry_day = date.fromisoformat(t.expiration) == now.date()
        late = now.strftime("%H:%M") >= "15:30"

        if debit <= take:
            reason = "take_profit"
        elif debit >= stop:
            reason = "stop"
        elif expiry_day and late:
            reason = "expiry_close"
        else:
            continue

        if mode == "live":
            order = broker.submit_mleg(
                _close_legs(t.legs), t.contracts,
                limit_price=abs(debit / 100 * 1.08),        # buying back = positive (debit)
                client_order_id=f"{t.client_order_id}-x"[:48],
            )
            t.exit_order_id = order.get("id")
            t.status = "pending_close"
            t.exit_reason = reason
            t.exit_debit = round(debit * t.contracts, 2)
            _rewrite(t)
            final = _await_fill(t.exit_order_id) if t.exit_order_id else None
            if (final or {}).get("status") == "filled":
                t.exit_reason = reason
                _finalize_close(t, _filled_credit_ps(final, debit / 100))
                actions.append({"trade": t.id, "reason": reason, "pnl": t.pnl})
            else:
                actions.append({"trade": t.id, "reason": reason, "pending": True})
        else:
            t.exit_reason = reason
            _finalize_close(t, debit / 100)
            actions.append({"trade": t.id, "reason": reason, "pnl": t.pnl, "mode": "dry_run"})
    return actions


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
    """Trades holding real risk: filled, or with an entry still working."""
    return [t for t in _load_all() if t.status in OPEN_STATES]


_load_active = _load_open


def _rewrite(updated: Trade) -> None:
    all_ = {t.id: t for t in _load_all()}
    all_[updated.id] = updated
    TRADES.parent.mkdir(exist_ok=True)
    with TRADES.open("w", encoding="utf-8") as f:
        for t in all_.values():
            f.write(json.dumps(asdict(t)) + "\n")
