"""Signal-layer tests. Synthetic chains and bars only — no network, no clock dependence.

Covers the three gates changed in issues #6, #10 and #12, plus the dead code removed in #14.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from agent import signal as sg
from agent.config import Params

EXP = date(2026, 9, 2)


# ---------- synthetic fixtures ----------

def occ(root: str, exp: date, cp: str, strike: float) -> str:
    return f"{root}{exp:%y%m%d}{cp}{round(strike * 1000):08d}"


def make_chain(
    spot: float = 600.0,
    iv: float = 0.12,
    n_strikes: int = 12,
    call_gamma: float = 0.05,
    put_gamma: float = 0.05,
    oi_per_strike: int = 1000,
) -> tuple[dict, dict]:
    """A symmetric chain around `spot`. Gamma per side is the knob that drives GEX.

    Net GEX is proportional to (call_gamma - put_gamma) and gross to (call_gamma + put_gamma),
    so `gex_norm` lands on exactly (c - p) / (c + p) — easy to aim at a dead zone or past it.
    """
    chain: dict[str, dict] = {}
    oi: dict[str, int] = {}
    for i in range(-n_strikes, n_strikes + 1):
        k = spot + i
        call_delta = 1.0 / (1.0 + math.exp((k - spot) / 2.0))
        for cp, gamma, delta in (("C", call_gamma, call_delta), ("P", put_gamma, call_delta - 1.0)):
            sym = occ("SPY", EXP, cp, k)
            chain[sym] = {
                "impliedVolatility": iv,
                "greeks": {"delta": delta, "gamma": gamma},
                "latestQuote": {"bp": 1.0, "ap": 1.1},
            }
            oi[sym] = oi_per_strike
    return chain, oi


def _bars_from_closes(closes: list[float], intraday: float = 0.004) -> list[dict]:
    """Open at the previous close, symmetric intraday range. Deterministic."""
    bars = []
    prev = closes[0]
    for c in closes:
        o = prev
        hi = max(o, c) * (1 + intraday)
        lo = min(o, c) * (1 - intraday)
        bars.append({"o": o, "h": hi, "l": lo, "c": c})
        prev = c
    return bars


def range_bars(n: int = 60, base: float = 600.0, amp: float = 2.0) -> list[dict]:
    """Mean-reverting oscillation: +DI and -DI alternate, so ADX stays low."""
    closes = [base + amp * math.sin(i * 0.9) for i in range(n)]
    return _bars_from_closes(closes)


def trend_bars(n: int = 60, base: float = 600.0, step: float = 0.004) -> list[dict]:
    """Monotone uptrend: last > EMA20 > EMA50 and ADX well above the 22 threshold."""
    closes = [base * (1 + step) ** i for i in range(n)]
    return _bars_from_closes(closes, intraday=0.001)


def noisy_bars(n: int = 60, base: float = 600.0, sigma: float = 0.008, seed: int = 7) -> list[dict]:
    rng = np.random.default_rng(seed)
    closes, c = [], base
    for _ in range(n):
        c *= math.exp(rng.normal(0.0, sigma))
        closes.append(c)
    return _bars_from_closes(closes)


def make_data(bars: list[dict], chain: dict, oi: dict, spot: float = 600.0) -> dict:
    return {"spot": spot, "expiration": EXP.isoformat(), "chain": chain, "oi": oi, "bars": bars}


def params(**over) -> Params:
    return replace(Params(), **over)


# ---------- issue #6: Yang-Zhang alignment + relative VRP gate ----------

def test_yang_zhang_ignores_bars_older_than_the_window():
    """The off-by-one made the range terms lead the gap terms by a day.

    With aligned slices, a violent bar that sits outside the window must not reach the
    estimate at all.
    """
    calm = noisy_bars(40, sigma=0.005)
    shocked = [dict(calm[0]), *calm[1:]]
    shocked[0] = {"o": 600.0, "h": 900.0, "l": 300.0, "c": 620.0}
    assert sg.yang_zhang_rv(calm, window=20) == pytest.approx(
        sg.yang_zhang_rv(shocked, window=20), rel=1e-12
    )


def test_yang_zhang_sees_a_shock_inside_the_window():
    calm = noisy_bars(40, sigma=0.005)
    shocked = [*calm[:-2], {"o": 600.0, "h": 660.0, "l": 540.0, "c": 640.0}, calm[-1]]
    assert sg.yang_zhang_rv(shocked, window=20) > 2 * sg.yang_zhang_rv(calm, window=20)


def test_rv_forecast_is_nan_without_enough_history():
    assert math.isnan(sg.rv_forecast(_bars_from_closes([600.0, 601.0])))


def test_missing_vol_data_stands_down_instead_of_trading():
    chain, oi = make_chain(call_gamma=0.06, put_gamma=0.02)
    s = sg.build_signal("SPY", make_data(_bars_from_closes([600.0, 601.0]), chain, oi), params())
    assert s.stand_down == "data"
    assert s.sell_premium is False and s.structure == "none"


def test_vrp_ratio_gate_is_relative_not_absolute():
    """The whole point of #6: the same *relative* richness must decide in either vol regime.

    Two tapes whose realized vol differs by ~5x (4.8% vs 23%). In both, IV 30% over RV
    trades and IV 5% over RV does not — which an absolute points threshold cannot do: at
    4.8% RV, 5 vol points *is* a 2x ratio, and at 23% RV, 3 points is noise.
    """
    p = params(vrp_ratio_min=1.15)
    quiet, loud = range_bars(amp=0.5), range_bars(amp=16.0)
    assert sg.rv_forecast(loud) > 4 * sg.rv_forecast(quiet)

    for bars in (quiet, loud):
        rv = sg.rv_forecast(bars)
        rich_chain, oi = make_chain(iv=rv * 1.30, call_gamma=0.06, put_gamma=0.02)
        poor_chain, _ = make_chain(iv=rv * 1.05, call_gamma=0.06, put_gamma=0.02)

        rich = sg.build_signal("SPY", make_data(bars, rich_chain, oi), p)
        poor = sg.build_signal("SPY", make_data(bars, poor_chain, oi), p)

        assert rich.sell_premium is True, f"RV {rv:.1%}"
        assert rich.structure == "iron_condor" and rich.stand_down == ""
        assert poor.sell_premium is False, f"RV {rv:.1%}"
        assert poor.structure == "none" and poor.stand_down == "vrp"


def test_old_absolute_threshold_would_have_blocked_a_rich_low_vol_tape():
    """Regression guard for the exact failure mode of #6: IV 40% over RV at a 6% IV level.

    `vrp` in points is only 0.024 — under the old `vrp_min = 0.03` — yet the ratio is 1.40.
    """
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 1.40, call_gamma=0.06, put_gamma=0.02)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params())
    assert s.vrp_ratio == pytest.approx(1.40, abs=0.01)
    assert s.sell_premium is True


def test_vrp_points_are_still_reported_for_the_journal():
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 1.30, call_gamma=0.06, put_gamma=0.02)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params())
    assert s.vrp == pytest.approx(s.atm_iv - s.rv_hat, abs=1e-3)


# ---------- issue #10: normalized GEX and the dead zone ----------

def test_gex_norm_is_the_call_put_gamma_imbalance():
    chain, oi = make_chain(call_gamma=0.06, put_gamma=0.02)
    _, norm = sg.compute_gex(chain, oi, 600.0, 0.05)
    assert norm == pytest.approx((0.06 - 0.02) / (0.06 + 0.02))


def test_gex_norm_is_invariant_to_open_interest_and_spot_scale():
    """The reason for normalizing at all: one threshold has to work for SPY and for IWM."""
    a_chain, a_oi = make_chain(spot=600.0, call_gamma=0.06, put_gamma=0.02, oi_per_strike=1_000)
    b_chain, b_oi = make_chain(spot=600.0, call_gamma=0.06, put_gamma=0.02, oi_per_strike=90_000)
    _, a = sg.compute_gex(a_chain, a_oi, 600.0, 0.05)
    _, b = sg.compute_gex(b_chain, b_oi, 600.0, 0.05)
    assert a == pytest.approx(b)


def test_gex_state_dead_zone():
    assert sg.gex_state(0.02, 0.10) == 0
    assert sg.gex_state(-0.02, 0.10) == 0
    assert sg.gex_state(0.10, 0.10) == 1
    assert sg.gex_state(-0.30, 0.10) == -1


def test_gex_dead_zone_forces_chop_and_no_trade():
    """A barely-positive GEX used to be indistinguishable from +$50Bn and traded like it."""
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    # (0.0505 - 0.0495) / 0.1 = 0.01 -> inside a 0.10 dead zone
    chain, oi = make_chain(iv=rv * 1.60, call_gamma=0.0505, put_gamma=0.0495)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params(gex_min=0.10))
    assert s.gex_sign == 1                        # the old bare-sign test would have said "go"
    assert s.gex_state == 0
    assert s.regime == "chop"
    assert s.sell_premium is False and s.structure == "none" and s.stand_down == "gex"


def test_gex_dead_zone_does_not_flip_flop_on_a_sign_change():
    """Same magnitude, opposite sign: the desk must give the same answer both loops."""
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    p = params(gex_min=0.10)
    pos, oi = make_chain(iv=rv * 1.60, call_gamma=0.0505, put_gamma=0.0495)
    neg, _ = make_chain(iv=rv * 1.60, call_gamma=0.0495, put_gamma=0.0505)
    a = sg.build_signal("SPY", make_data(bars, pos, oi), p)
    b = sg.build_signal("SPY", make_data(bars, neg, oi), p)
    assert a.gex_sign != b.gex_sign               # raw sign does flip …
    assert (a.regime, a.structure) == (b.regime, b.structure) == ("chop", "none")


def test_short_gamma_with_magnitude_stands_down():
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 1.60, call_gamma=0.02, put_gamma=0.06)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params())
    assert s.gex_state == -1
    assert s.sell_premium is False and s.structure == "none" and s.stand_down == "gex"


def test_gex_min_is_honoured_from_params():
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 1.60, call_gamma=0.0505, put_gamma=0.0495)
    data = make_data(bars, chain, oi)
    assert sg.build_signal("SPY", data, params(gex_min=0.10)).sell_premium is False
    assert sg.build_signal("SPY", data, params(gex_min=0.005)).sell_premium is True


# ---------- issue #12: no short premium into a trend, and a real ADX ----------

def test_trending_tape_produces_no_structure():
    bars = trend_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 2.0, call_gamma=0.06, put_gamma=0.02)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params(fade_trend=False))
    assert s.regime == "trending_up"
    assert s.bias == "bullish"                    # honest read of the tape, not the inverted one
    assert s.structure == "none"
    assert s.sell_premium is False
    assert s.stand_down == "trend"


def test_fade_trend_flag_restores_the_legacy_behaviour():
    """Reversal must stay a one-flag change if the backtest ever justifies it."""
    bars = trend_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 2.0, call_gamma=0.06, put_gamma=0.02)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params(fade_trend=True))
    assert s.regime == "trending_up"
    assert s.bias == "bearish"
    assert s.structure == "call_credit_spread"
    assert s.sell_premium is True


def test_trend_gate_applies_to_downtrends_too():
    closes = [600.0 * (1 - 0.004) ** i for i in range(60)]
    bars = _bars_from_closes(closes, intraday=0.001)
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 2.0, call_gamma=0.06, put_gamma=0.02)
    s = sg.build_signal("SPY", make_data(bars, chain, oi), params())
    assert s.regime == "trending_down"
    assert s.structure == "none" and s.sell_premium is False


def test_adx_is_smoothed_and_separates_trend_from_chop():
    """A raw DX pins near 100 on any directional stretch; a smoothed ADX has to build up."""
    assert sg._adx(trend_bars(), 14) > 22
    assert sg._adx(range_bars(), 14) < 18


def test_adx_needs_history_and_degrades_quietly():
    assert sg._adx(range_bars(8), 14) == 0.0


# ---------- issue #14: dead code is gone ----------

def test_satellite_and_conviction_are_gone():
    assert not hasattr(Params(), "satellite_frac")
    assert not hasattr(Params(), "vrp_min")
    assert "conviction" not in sg.Signal.__dataclass_fields__


def test_debit_spread_is_never_proposed():
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    for cg, pg in ((0.06, 0.02), (0.02, 0.06), (0.05, 0.05)):
        chain, oi = make_chain(iv=rv * 1.60, call_gamma=cg, put_gamma=pg)
        s = sg.build_signal("SPY", make_data(bars, chain, oi), params())
        assert s.structure in ("iron_condor", "put_credit_spread", "call_credit_spread", "none")
        assert s.structure != "debit_spread"


def test_sell_premium_implies_a_tradeable_structure():
    """desk.py keys off sell_premium; the two must never disagree."""
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    for mult in (0.9, 1.05, 1.30, 2.0):
        for cg, pg in ((0.06, 0.02), (0.02, 0.06), (0.0505, 0.0495)):
            chain, oi = make_chain(iv=rv * mult, call_gamma=cg, put_gamma=pg)
            s = sg.build_signal("SPY", make_data(bars, chain, oi), params())
            assert s.sell_premium == (s.structure != "none")
            assert s.sell_premium == (s.stand_down == "")
