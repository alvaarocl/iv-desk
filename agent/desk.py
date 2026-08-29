"""Main loop — invoked by cron (GitHub Actions) every 15 min during RTH.

  0. account guard      — refuse to run against the wrong paper account
  1. reconcile          — Alpaca is the source of truth: resolve pending orders, spot assignments
  2. exits              — manage_exits() on the open book (deterministic, no LLM)
  3. portfolio gates    — daily breaker / drawdown / event blackout / assignment → exits-only
  4. signal per name    — build_signal() (deterministic)
  5. open decision      — pick structure, size via Risk Officer, LLM desk debates (trim/veto
                          only), commit. dry_run logs without ordering.
  6. journal + equity   — append everything to data/

Stateless: rebuilds its view from the Alpaca account + data/trades.jsonl each run. Idempotent.
Every per-underlying step is isolated: one bad quote or HTTP timeout must not kill the loop.
"""

from __future__ import annotations

import os
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from . import broker, debate, risk
from . import execution as ex
from . import marketdata as md
from . import signal as sg
from .config import UNIVERSE, Params, desk_mode
from .journal import append, record_equity

ET = ZoneInfo("America/New_York")

# The competition account (PAPER UC3M). Live mode must never touch anything else, and this
# account must never be touched before the P&L window opens.
COMPETITION_ACCOUNT = os.environ.get("ALPACA_ACCOUNT_ID", "").strip()
COMPETITION_OPEN_ET = datetime(2026, 8, 31, 9, 30, tzinfo=ET)


def _portfolio_state(params: Params) -> risk.PortfolioState:
    acct = broker.account()
    nav = float(acct["equity"])
    open_trades = ex._load_open()
    open_risk = sum(t.max_loss for t in open_trades)
    peak = _peak_nav(nav)
    return risk.PortfolioState(
        nav=nav, peak_nav=peak, open_risk=open_risk, n_positions=len(open_trades),
        net_delta=_book_delta(open_trades, nav),
        day_pnl=nav - float(acct["last_equity"]),
    )


def _legs_delta(legs: list[dict], contracts: int, chain: dict, spot: float) -> float | None:
    """Delta-adjusted notional ($) of a set of legs. Short legs carry the opposite sign.

    Returns None if any leg has no greeks — a missing quote must not silently read as flat.
    """
    total = 0.0
    for leg in legs:
        g = (chain.get(leg["symbol"]) or {}).get("greeks")
        if not g:
            return None
        sign = -1.0 if leg["side"] == "sell" else 1.0
        total += sign * g["delta"] * 100 * contracts * spot
    return total


def _book_delta(open_trades: list, nav: float) -> float:
    """Net delta of the open book as a fraction of NAV. 0.30 == 30% of NAV directional."""
    if not open_trades or nav <= 0:
        return 0.0
    chains: dict[tuple[str, str], dict] = {}
    spots: dict[str, float] = {}
    total = 0.0
    for t in open_trades:
        key = (t.underlying, t.expiration)
        if key not in chains:
            chains[key] = md.option_chain_snapshot(t.underlying, expiration_date=t.expiration)
        if t.underlying not in spots:
            spots[t.underlying] = md.stock_price(t.underlying)
        d = _legs_delta(t.legs, t.contracts, chains[key], spots[t.underlying])
        if d is None:
            append({"event": "delta_unavailable", "trade": t.id})
            continue
        total += d
    return total / nav


def _assignment_alert() -> dict | None:
    """SPY/QQQ/IWM options are American-style: a short ITM leg can be assigned early.

    If that happens we are holding shares, not a condor, and every risk figure the desk
    computes is wrong. Detect any unexpected equity position so the loop can stand down.
    `ex.reconcile` also flags this — checking here as well keeps the stand-down independent
    of reconcile succeeding.
    """
    try:
        eq = [p for p in broker.positions() if p.get("asset_class") == "us_equity"]
    except Exception:  # noqa: BLE001 - unknown assignment state must not stop exits
        return None
    if not eq:
        return None
    return {
        "symbols": [p["symbol"] for p in eq],
        "market_value": round(sum(float(p.get("market_value") or 0) for p in eq), 2),
    }


def _peak_nav(current: float) -> float:
    from pathlib import Path
    f = Path(__file__).resolve().parent.parent / "data" / "peak_nav.txt"
    peak = current
    if f.exists():
        peak = max(current, float(f.read_text().strip() or current))
    f.write_text(str(peak))
    return peak


def _guard_account(mode: str, now: datetime) -> dict:
    """Hard stop on trading the wrong account, in either direction.

    Two failure modes, both unrecoverable: trading the testing account in an order-placing mode
    scores nothing, and placing an order on the competition account before the window breaks the
    requirement that its trading history be 100% agent-driven from Mon 09:30 ET.

    `dry_run` places nothing (see execution.open_trade / manage_exits / reconcile — every order
    call is gated on `mode == "live"`), so it is allowed against the competition account before
    the window: that is exactly how the CI pipeline is smoke-tested over the weekend. Only the
    order-placing modes are blocked early.
    """
    places_orders = mode in ("live", "exits_only")
    acct = broker.account()
    actual = acct.get("account_number")
    if places_orders and COMPETITION_ACCOUNT and actual != COMPETITION_ACCOUNT:
        raise broker.BrokerError(
            f"ACCOUNT MISMATCH — {mode} mode expects {COMPETITION_ACCOUNT!r}, credentials point "
            f"at {actual!r}. Refusing to place any order."
        )
    if places_orders and actual == COMPETITION_ACCOUNT and now < COMPETITION_OPEN_ET:
        raise broker.BrokerError(
            f"TOO EARLY — {actual!r} is the competition account and the P&L window opens "
            f"{COMPETITION_OPEN_ET:%Y-%m-%d %H:%M %Z}. Refusing to place an order."
        )
    return acct


def run_once() -> None:
    params = Params.load()
    mode = desk_mode()
    exits_only = mode == "exits_only"      # kill switch: manage the book, open nothing
    order_mode = "live" if mode in ("live", "exits_only") else "dry_run"
    now = datetime.now(ET)
    stamp = now.isoformat()

    # 0. account guard — before any network call that could place an order
    try:
        acct = _guard_account(order_mode, now)
        append({"ts": stamp, "event": "account", "account": acct.get("account_number"),
                "mode": mode, "equity": acct.get("equity")})
    except Exception as exc:
        append({"ts": stamp, "event": "fatal", "stage": "account_guard", "error": str(exc)})
        raise

    clk = broker.clock()
    if not clk.get("is_open"):
        append({"ts": stamp, "event": "market_closed"})
        return

    # 1. reconcile against the broker before trusting the local book
    try:
        for evt in ex.reconcile(order_mode):
            append({"ts": stamp, "event": "reconcile", **evt})
    except Exception as exc:  # noqa: BLE001 - a cron loop must survive any single stage
        append({"ts": stamp, "event": "error", "stage": "reconcile", "error": str(exc),
                "trace": traceback.format_exc(limit=3)})

    # An early assignment leaves real shares in the account; still run exits on whatever option
    # legs remain, but open nothing new until a human looks.
    assigned = _assignment_alert()
    if assigned:
        append({"ts": stamp, "event": "exits_only", "reason": "early_assignment", **assigned})

    # 2. exits
    try:
        for act in ex.manage_exits(params, order_mode):
            append({"ts": stamp, "event": "exit", **act})
    except Exception as exc:  # noqa: BLE001 - a cron loop must survive any single stage
        append({"ts": stamp, "event": "error", "stage": "exits", "error": str(exc),
                "trace": traceback.format_exc(limit=3)})

    # 3. portfolio gates
    pf = _portfolio_state(params)
    record_equity(pf.nav, pf.day_pnl)
    mult = risk.size_multiplier(pf, params)
    breaker = pf.day_pnl <= -params.daily_loss_breaker * pf.nav
    append({"ts": stamp, "event": "portfolio", "nav": pf.nav, "day_pnl": round(pf.day_pnl, 2),
            "open_risk": pf.open_risk, "n_pos": pf.n_positions, "net_delta": round(pf.net_delta, 3),
            "size_mult": mult, "breaker": breaker})
    if exits_only or breaker or mult == 0.0 or assigned:
        reason = ("kill_switch" if exits_only else "breaker" if breaker
                  else "drawdown_halt" if mult == 0.0 else "early_assignment")
        append({"ts": stamp, "event": "exits_only", "reason": reason})
        return

    # 4 + 5. per-underlying — isolated so one bad chain cannot end the loop
    for u in UNIVERSE:
        try:
            _consider(u, params, pf, mult, order_mode, now, stamp)
        except Exception as exc:  # noqa: BLE001 - one bad chain must not end the loop
            append({"ts": stamp, "event": "error", "stage": "underlying", "underlying": u,
                    "error": str(exc), "trace": traceback.format_exc(limit=3)})


def _consider(u: str, params: Params, pf, mult: float, mode: str,
              now: datetime, stamp: str) -> None:
    data = sg.fetch(u, params)
    s = sg.build_signal(u, data, params)
    rec = {k: v for k, v in s.__dict__.items() if k != "chain"}
    append({"ts": stamp, "event": "signal", **rec})

    if not s.sell_premium or pf.n_positions >= params.max_positions:
        return
    sel = _pick(s, params, data.get("oi"))
    if not sel:
        append({"ts": stamp, "event": "no_structure", "underlying": u,
                "reason": "no liquid strikes at target delta/width"})
        return

    n = ex.size(sel["width"], sel["credit"], pf.nav, params.risk_per_trade, mult)
    cr_frac = sel["credit"] / sel["width"] if sel["width"] else 0
    leg_delta = _legs_delta(sel["legs"], n, s.chain, s.spot)
    if leg_delta is None:
        append({"ts": stamp, "event": "rejected", "underlying": u, "reason": "missing greeks"})
        return
    proposed = risk.ProposedTrade(
        underlying=u, structure=s.structure, max_loss=(sel["width"] - sel["credit"]) * 100 * n,
        net_delta=leg_delta / pf.nav,
        is_0dte=s.expiration == now.strftime("%Y-%m-%d"), is_satellite=False,
    )
    ok, why = risk.evaluate(proposed, pf, params, now)
    if not (ok and n >= 1 and cr_frac >= params.min_credit_frac):
        append({"ts": stamp, "event": "rejected", "underlying": u, "reason": why,
                "size": n, "credit_frac": round(cr_frac, 3)})
        return

    base_thesis = f"{u} stays inside {sel['strikes']} through {s.expiration}: {s.notes}"

    # The LLM desk debates. `n` is the ceiling risk.evaluate() already approved: the desk can
    # only trim or veto, never widen. See agent/debate.py.
    d = debate.review_open(s, sel, n, base_thesis)
    append({"ts": stamp, "event": "debate", "underlying": u, **d.to_record()})
    if not d.approved:
        return
    n, thesis = d.contracts, d.thesis
    if n < 1:
        return
    # The Desk Head may have trimmed the size — max_loss must follow, or the book over-reports
    # its own risk and blocks later trades.
    proposed.max_loss = (sel["width"] - sel["credit"]) * 100 * n

    t = ex.open_trade(s, sel, n, thesis, mode)
    pf.n_positions += 1
    pf.open_risk += proposed.max_loss
    append({"ts": stamp, "event": "opened", "mode": mode, "trade": t.id if t else None,
            "status": t.status if t else None, "underlying": u, "structure": s.structure,
            "contracts": n, "credit": round(sel["credit"], 2),
            "max_loss": round(proposed.max_loss, 0), "strikes": sel["strikes"], "thesis": thesis})


def _pick(s: sg.Signal, params: Params, oi: dict | None = None) -> dict | None:
    w = params.width_iwm if s.underlying == "IWM" else params.width_spy
    oi = oi or {}
    if s.structure == "iron_condor":
        return ex.select_condor(s.chain, params.short_delta, w, oi, params)
    if s.structure == "put_credit_spread":
        return ex.select_vertical(s.chain, "P", params.short_delta, w, oi, params)
    if s.structure == "call_credit_spread":
        return ex.select_vertical(s.chain, "C", params.short_delta, w, oi, params)
    return None


if __name__ == "__main__":
    run_once()
