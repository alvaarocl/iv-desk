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
from . import marketdata as md
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
    computes is wrong. Detect any unexpected equity position and stand down.
    """
    eq = [p for p in broker.positions() if p.get("asset_class") == "us_equity"]
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

    # 2. assignment check — an early assignment invalidates every risk figure below
    assigned = _assignment_alert()
    if assigned:
        append({"ts": stamp, "event": "exits_only", "reason": "early_assignment", **assigned})
        return

    # 3. portfolio gates
    pf = _portfolio_state(params)
    record_equity(pf.nav, pf.day_pnl)
    mult = risk.size_multiplier(pf, params)
    breaker = pf.day_pnl <= -params.daily_loss_breaker * pf.nav
    append({"ts": stamp, "event": "portfolio", "nav": pf.nav, "day_pnl": round(pf.day_pnl, 2),
            "open_risk": pf.open_risk, "n_pos": pf.n_positions, "size_mult": mult, "breaker": breaker})
    if breaker or mult == 0.0:
        append({"ts": stamp, "event": "exits_only", "reason": "breaker" if breaker else "drawdown_halt"})
        return

    # 4 + 5. per-underlying
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
        leg_delta = _legs_delta(sel["legs"], n, s.chain, s.spot)
        if leg_delta is None:
            append({"ts": stamp, "event": "rejected", "underlying": u, "reason": "missing greeks"})
            continue
        proposed = risk.ProposedTrade(
            underlying=u, structure=s.structure, max_loss=(sel["width"] - sel["credit"]) * 100 * n,
            net_delta=leg_delta / pf.nav,
            is_0dte=s.expiration == now.strftime("%Y-%m-%d"), is_satellite=False,
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
