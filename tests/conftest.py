"""Shared fixtures. No network: every Alpaca call in the engine is stubbed here."""

from __future__ import annotations

import pytest

from agent.config import Params


@pytest.fixture
def params() -> Params:
    return Params()


def _snap(bid: float, ask: float, delta: float, gamma: float = 0.01) -> dict:
    return {
        "latestQuote": {"bp": bid, "ap": ask},
        "greeks": {"delta": delta, "gamma": gamma, "theta": -0.1, "vega": 0.1, "rho": 0.0},
        "impliedVolatility": 0.09,
    }


@pytest.fixture
def spy_chain() -> dict:
    """A small SPY chain around spot 775, expiring 2026-09-03.

    Puts below spot carry negative delta; calls above carry positive. Wide wings are deliberately
    given a one-sided quote so the liquidity gate has something to reject.
    """
    c: dict[str, dict] = {}
    # short put ~0.18Δ at 769, long put at 765 (spreads kept under the 10% liquidity gate)
    c["SPY260903P00769000"] = _snap(1.08, 1.12, -0.18)
    c["SPY260903P00765000"] = _snap(0.49, 0.51, -0.09)
    # short call ~0.18Δ at 781, long call at 785
    c["SPY260903C00781000"] = _snap(1.03, 1.07, 0.18)
    c["SPY260903C00785000"] = _snap(0.44, 0.46, 0.09)
    # an illiquid far strike: one-sided quote, should never be picked
    c["SPY260903P00760000"] = {"latestQuote": {"bp": 0.20, "ap": 0.0},
                               "greeks": {"delta": -0.04, "gamma": 0.002}, "impliedVolatility": 0.1}
    return c


@pytest.fixture
def oi_all_liquid() -> dict:
    return {
        "SPY260903P00769000": 5000, "SPY260903P00765000": 4000,
        "SPY260903C00781000": 5000, "SPY260903C00785000": 4000,
        "SPY260903P00760000": 3000,
    }
