"""Main loop — invoked by cron (GitHub Actions) every 15 min during RTH.

  1. exits first        — manage_exits() on the open book (deterministic, no LLM)
  2. portfolio gates    — daily breaker / drawdown / event blackout → if tripped, exits-only
  3. signal per name    — build_signal() (deterministic)
  4. open decision      — only if sell_premium and a slot is free: pick structure, size via
                          Risk Officer, (debate hook), commit. dry_run logs without ordering.
  5. journal + equity   — append everything to data/

Stateless: rebuilds its view from the Alpaca account + data/trades.jsonl each run. Idempotent.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from . import broker, risk
from . import execution as ex
from . import signal as sg
from .config import UNIVERSE, Params, desk_mode
from .journal import append, record_equity

ET = ZoneInfo("America/New_York")


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


def run_once() -> None:
    params = Params.load()
    mode = desk_mode()
    now = datetime.now(ET)
    stamp = now.isoformat()

    clk = broker.clock()
    if not clk.get("is_open"):
        append({"ts": stamp, "event": "market_closed"})
        return

    # 1. exits
    for act in ex.manage_exits(params, mode):
        append({"ts": stamp, "event": "exit", **act})

    # 2. portfolio gates
    pf = _portfolio_state(params)
    record_equity(pf.nav, pf.day_pnl)
    mult = risk.size_multiplier(pf, params)
    breaker = pf.day_pnl <= -params.daily_loss_breaker * pf.nav
    append({"ts": stamp, "event": "portfolio", "nav": pf.nav, "day_pnl": round(pf.day_pnl, 2),
            "open_risk": pf.open_risk, "n_pos": pf.n_positions, "size_mult": mult, "breaker": breaker})
    if breaker or mult == 0.0:
        append({"ts": stamp, "event": "exits_only", "reason": "breaker" if breaker else "drawdown_halt"})
        return

    # 3 + 4. per-underlying
    for u in UNIVERSE:
        data = sg.fetch(u, params)
        s = sg.build_signal(u, data, params)
        rec = {k: v for k, v in s.__dict__.items() if k != "chain"}
        append({"ts": stamp, "event": "signal", **rec})

        if not s.sell_premium or pf.n_positions >= params.max_positions:
            continue
        sel = _pick(s, params)
        if not sel:
            append({"ts": stamp, "event": "no_structure", "underlying": u})
            continue
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
            continue

        thesis = f"{u} stays inside {sel['strikes']} through {s.expiration}: {s.notes}"
        # TODO: debate(s, sel) → may veto / adjust before commit
        t = ex.open_trade(s, sel, n, thesis, mode)
        pf.n_positions += 1
        pf.open_risk += proposed.max_loss
        append({"ts": stamp, "event": "opened", "mode": mode, "trade": t.id if t else None,
                "underlying": u, "structure": s.structure, "contracts": n,
                "credit": round(sel["credit"], 2), "max_loss": round(proposed.max_loss, 0),
                "strikes": sel["strikes"], "thesis": thesis})


def _pick(s: sg.Signal, params: Params) -> dict | None:
    w = params.width_iwm if s.underlying == "IWM" else params.width_spy
    if s.structure == "iron_condor":
        return ex.select_condor(s.chain, params.short_delta, w)
    if s.structure == "put_credit_spread":
        return ex.select_vertical(s.chain, "P", params.short_delta, w)
    if s.structure == "call_credit_spread":
        return ex.select_vertical(s.chain, "C", params.short_delta, w)
    return None


if __name__ == "__main__":
    run_once()
