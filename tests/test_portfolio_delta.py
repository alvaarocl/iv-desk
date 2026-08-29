"""Delta aggregation and the portfolio delta gate (issues #11, #25)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from agent import desk, risk
from agent.config import Params

ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 9, 2, 11, 0, tzinfo=ET)  # sesión limpia: sin evento macro en +/-2h


def _chain(**deltas: float) -> dict:
    return {sym: {"greeks": {"delta": d}} for sym, d in deltas.items()}


def _legs(*pairs: tuple[str, str]) -> list[dict]:
    return [{"symbol": s, "side": side} for s, side in pairs]


def test_short_legs_flip_the_sign():
    chain = _chain(SHORT_PUT=-0.18, LONG_PUT=-0.10)
    # sold put: short a -0.18 delta => +0.18 exposure; bought put adds -0.10
    d = desk._legs_delta(_legs(("SHORT_PUT", "sell"), ("LONG_PUT", "buy")), 1, chain, 100.0)
    assert d == pytest.approx((0.18 - 0.10) * 100 * 1 * 100.0)


def test_balanced_condor_is_near_flat():
    chain = _chain(SP=-0.18, LP=-0.10, SC=0.18, LC=0.10)
    d = desk._legs_delta(
        _legs(("SP", "sell"), ("LP", "buy"), ("SC", "sell"), ("LC", "buy")), 1, chain, 100.0
    )
    assert d == pytest.approx(0.0, abs=1e-9)


def test_missing_greeks_returns_none_not_zero():
    """A missing quote must not read as a flat book — that would silently pass the gate."""
    assert desk._legs_delta(_legs(("SP", "sell"), ("GONE", "buy")), 1, _chain(SP=-0.18), 100.0) is None


def _pf(net_delta: float) -> risk.PortfolioState:
    return risk.PortfolioState(
        nav=100_000, peak_nav=100_000, open_risk=0.0, n_positions=0,
        net_delta=net_delta, day_pnl=0.0,
    )


def _trade(net_delta: float, max_loss: float = 200.0) -> risk.ProposedTrade:
    return risk.ProposedTrade(
        underlying="SPY", structure="iron_condor", max_loss=max_loss,
        net_delta=net_delta, is_0dte=False, is_satellite=False,
    )


def test_delta_gate_rejects_a_third_spread_on_the_same_side():
    params = Params()
    ok, why = risk.evaluate(_trade(0.05), _pf(0.20), params, NOW)
    assert ok, why
    rejected, why = risk.evaluate(_trade(0.15), _pf(0.20), params, NOW)
    assert not rejected and "delta band" in why


def test_delta_gate_is_not_scaled_away_at_nav_100k():
    """The old gate multiplied the cap by nav/100k, which made it a no-op at other NAVs."""
    params = Params()
    pf = risk.PortfolioState(
        nav=10_000, peak_nav=10_000, open_risk=0.0, n_positions=0, net_delta=0.40, day_pnl=0.0
    )
    # max_loss pequeño a propósito: el gate de riesgo por trade no debe adelantarse al de delta
    ok, why = risk.evaluate(_trade(0.0, max_loss=20.0), pf, params, NOW)
    assert not ok and "delta band" in why
