"""Main loop — invoked by cron (GitHub Actions) every 15 min during RTH.

  0. account guard      — refuse to run against the wrong paper account
  1. reconcile          — Alpaca is the source of truth: resolve pending orders, spot assignments
  2. exits              — manage_exits() on the open book (deterministic, no LLM)
  3. portfolio gates    — daily breaker / drawdown / event blackout → if tripped, exits-only
  4. signal per name    — build_signal() (deterministic)
  5. open decision      — only if sell_premium and a slot is free: pick structure, size via
                          Risk Officer, (debate hook), commit. dry_run logs without ordering.
  6. journal + equity   — append everything to data/

Stateless: rebuilds its view from the Alpaca account + data/trades.jsonl each run. Idempotent.
Every per-underlying step is isolated: one bad quote or HTTP timeout must not kill the loop.
"""

from __future__ import annotations

import os
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from . import broker, risk
from . import execution as ex
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
        net_delta=0.0,  # TODO: aggregate leg deltas from chain
        day_pnl=nav - float(acct["last_equity"]),
    )


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

    Two failure modes, both unrecoverable: trading the testing account in live mode scores
    nothing, and touching the competition account early (or by hand) breaks the requirement that
    its history be 100% agent-driven.
    """
    acct = broker.account()
    actual = acct.get("account_number")
    if mode == "live" and COMPETITION_ACCOUNT and actual != COMPETITION_ACCOUNT:
        raise broker.BrokerError(
            f"ACCOUNT MISMATCH — live mode expects {COMPETITION_ACCOUNT!r}, credentials point at "
            f"{actual!r}. Refusing to place any order."
        )
    if actual == COMPETITION_ACCOUNT and COMPETITION_ACCOUNT and now < COMPETITION_OPEN_ET:
        raise broker.BrokerError(
            f"TOO EARLY — {actual!r} is the competition account and the P&L window opens "
            f"{COMPETITION_OPEN_ET:%Y-%m-%d %H:%M %Z}. Refusing to touch it."
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

    # An assignment leaves real shares in the account; stop opening anything until a human looks.
    try:
        assigned = ex.has_unexpected_equity()
    except Exception:  # noqa: BLE001 - unknown assignment state must not stop exits
        assigned = False
    if assigned:
        append({"ts": stamp, "event": "exits_only", "reason": "unexpected_equity_position"})

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
            "open_risk": pf.open_risk, "n_pos": pf.n_positions, "size_mult": mult, "breaker": breaker})
    if exits_only or breaker or mult == 0.0 or assigned:
        reason = ("kill_switch" if exits_only else "breaker" if breaker
                  else "drawdown_halt" if mult == 0.0 else "assignment")
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
    sel = _pick(s, data, params)
    if not sel:
        append({"ts": stamp, "event": "no_structure", "underlying": u,
                "reason": "no liquid strikes at target delta/width"})
        return
    n = ex.size(sel["width"], sel["credit"], pf.nav, params.risk_per_trade, mult)
    cr_frac = sel["credit"] / sel["width"] if sel["width"] else 0
    proposed = risk.ProposedTrade(
        underlying=u, structure=s.structure, max_loss=(sel["width"] - sel["credit"]) * 100 * n,
        net_delta=0.0, is_0dte=s.expiration == now.strftime("%Y-%m-%d"), is_satellite=False,
    )
    ok, why = risk.evaluate(proposed, pf, params, now)
    if not (ok and n >= 1 and cr_frac >= params.min_credit_frac):
        append({"ts": stamp, "event": "rejected", "underlying": u, "reason": why,
                "size": n, "credit_frac": round(cr_frac, 3)})
        return

    thesis = f"{u} stays inside {sel['strikes']} through {s.expiration}: {s.notes}"
    # TODO: debate(s, sel) → may veto / adjust before commit
    t = ex.open_trade(s, sel, n, thesis, mode)
    pf.n_positions += 1
    pf.open_risk += proposed.max_loss
    append({"ts": stamp, "event": "opened", "mode": mode, "trade": t.id if t else None,
            "status": t.status if t else None, "underlying": u, "structure": s.structure,
            "contracts": n, "credit": round(sel["credit"], 2),
            "max_loss": round(proposed.max_loss, 0), "strikes": sel["strikes"], "thesis": thesis})


def _pick(s: sg.Signal, data: dict, params: Params) -> dict | None:
    w = params.width_iwm if s.underlying == "IWM" else params.width_spy
    oi = data.get("oi", {})
    if s.structure == "iron_condor":
        return ex.select_condor(s.chain, params.short_delta, w, oi, params)
    if s.structure == "put_credit_spread":
        return ex.select_vertical(s.chain, "P", params.short_delta, w, oi, params)
    if s.structure == "call_credit_spread":
        return ex.select_vertical(s.chain, "C", params.short_delta, w, oi, params)
    return None


if __name__ == "__main__":
    run_once()
