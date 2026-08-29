"""Risk Officer — deterministic gates. No LLM ever calls into discretion here.

Owner: lane A. Every function returns (ok: bool, reason: str). `evaluate` is the single entry point.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .calendar import in_event_blackout


@dataclass
class PortfolioState:
    nav: float
    peak_nav: float
    open_risk: float          # sum of max-loss across open positions ($)
    n_positions: int
    net_delta: float          # delta-adjusted notional as a fraction of NAV
    day_pnl: float            # realized + unrealized today ($)


@dataclass
class ProposedTrade:
    underlying: str
    structure: str
    max_loss: float           # $ at the proposed size
    net_delta: float          # same units as PortfolioState.net_delta
    is_0dte: bool
    is_satellite: bool


def evaluate(trade: ProposedTrade, pf: PortfolioState, params, now_et: datetime) -> tuple[bool, str]:
    dd = 1 - pf.nav / pf.peak_nav if pf.peak_nav else 0.0

    checks = [
        (trade.max_loss <= params.risk_per_trade * pf.nav,
         f"per-trade risk {trade.max_loss:.0f} > {params.risk_per_trade * pf.nav:.0f}"),
        (pf.open_risk + trade.max_loss <= params.max_portfolio_risk * pf.nav,
         "portfolio risk cap"),
        (pf.n_positions < params.max_positions, "max concurrent positions"),
        (abs(pf.net_delta + trade.net_delta) <= params.max_net_delta,
         f"portfolio delta band {abs(pf.net_delta + trade.net_delta):.2f} > {params.max_net_delta}"),
        (pf.day_pnl > -params.daily_loss_breaker * pf.nav, "daily loss circuit breaker tripped"),
        (dd < params.dd_halt, f"drawdown {dd:.1%} >= hard halt"),
        (not in_event_blackout(now_et), "macro event blackout"),
        (not (trade.is_0dte and now_et.strftime("%H:%M") >= params.no_new_0dte_after_et),
         "no new 0DTE after cutoff"),
    ]
    for ok, reason in checks:
        if not ok:
            return False, reason
    return True, "ok"


def size_multiplier(pf: PortfolioState, params) -> float:
    """Drawdown throttle: full size, half size, or zero."""
    dd = 1 - pf.nav / pf.peak_nav if pf.peak_nav else 0.0
    if dd >= params.dd_halt:
        return 0.0
    if dd >= params.dd_throttle:
        return 0.5
    return 1.0
