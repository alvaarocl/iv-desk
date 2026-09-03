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


# ---------- the scoring-window expiration cutoff ----------
#
# The P&L window snapshots total equity at the close of Thu 3 Sep and Fri-4-Sep expirations are
# excluded. `pick_expiration` used to fall back to the nearest expiration whatever it was, so on
# Thu 3 Sep it returned Fri 4 Sep and every trade of the final session landed outside the
# measurement. These pin the fix.

CUTOFF = date(2026, 9, 3)


class _FrozenDate(date):
    """Lets a test pin `date.today()` inside agent.signal without touching the real clock."""

    _today = date(2026, 9, 1)

    @classmethod
    def today(cls) -> date:
        return cls._today


@pytest.fixture
def at_date(monkeypatch):
    def _set(d: date):
        monkeypatch.setattr(_FrozenDate, "_today", d)
        monkeypatch.setattr(sg, "date", _FrozenDate)

        def fake_contracts(underlying, **kw):
            # SPY has daily expirations; hand back the next two weeks of weekdays.
            out = []
            for i in range(14):
                e = date.fromordinal(d.toordinal() + i)
                if e.weekday() < 5:
                    out.append({"expiration_date": e.isoformat()})
            return out

        monkeypatch.setattr(sg.broker, "option_contracts", fake_contracts)

    return _set


@pytest.mark.parametrize("today, expected", [
    (date(2026, 9, 1), "2026-09-02"),   # Tue  -> Wed, 1 DTE
    (date(2026, 9, 2), "2026-09-03"),   # Wed  -> Thu, 1 DTE
    (date(2026, 9, 3), "2026-09-03"),   # Thu  -> same day. NOT Fri 4 Sep.
])
def test_expiration_never_crosses_the_scoring_cutoff(at_date, today, expected):
    at_date(today)
    assert sg.pick_expiration("SPY", 766.0, last_expiration=CUTOFF) == expected


def test_the_old_fallback_no_longer_leaks_a_post_cutoff_expiration(at_date):
    """Fri 4 Sep: nothing on or before the cutoff is left, so the desk must stand down."""
    at_date(date(2026, 9, 4))
    assert sg.pick_expiration("SPY", 766.0, last_expiration=CUTOFF) is None


def test_no_contracts_at_all_is_a_stand_down_not_a_guess(at_date, monkeypatch):
    at_date(date(2026, 9, 1))
    monkeypatch.setattr(sg.broker, "option_contracts", lambda underlying, **kw: [])
    assert sg.pick_expiration("SPY", 766.0, last_expiration=CUTOFF) is None


def test_missing_expiration_stands_the_signal_down_before_any_other_gate():
    """A rich, perfectly tradeable surface must still not trade past the cutoff."""
    bars = range_bars()
    rv = sg.rv_forecast(bars)
    chain, oi = make_chain(iv=rv * 2.0, call_gamma=0.06, put_gamma=0.02)
    data = make_data(bars, chain, oi)
    data["expiration"] = None

    s = sg.build_signal("SPY", data, params())
    assert s.stand_down == "expiration"
    assert s.sell_premium is False and s.structure == "none"
    assert s.expiration == ""


# ---------- _fallback_structure — shared by the real gate ladder and the shadow-debate ----------


@pytest.mark.parametrize("regime, bias, expected", [
    ("range", "neutral", "iron_condor"),
    ("range", "bullish", "iron_condor"),   # regime == "range" wins regardless of bias
    ("range", "bearish", "iron_condor"),
    ("chop", "neutral", "iron_condor"),
    ("chop", "bullish", "put_credit_spread"),
    ("chop", "bearish", "call_credit_spread"),
])
def test_fallback_structure_matches_the_real_gate_ladder(regime, bias, expected):
    assert sg._fallback_structure(regime, bias) == expected


# ---------- _backfill_missing_greeks — 0DTE IV/greeks Alpaca doesn't publish ----------
#
# Verified live 3 Sep: Alpaca's free feed carries zero greeks/IV for same-day-expiring
# contracts (0 of 192 real SPY 0DTE contracts), which is exactly what `pick_expiration`'s
# cutoff-day fallback produces on the last scored session. These pin the fix: real mid-price
# in, real (Black-Scholes) IV/delta/gamma out, and never touching a contract Alpaca already
# measured.

from datetime import datetime as _dt
from datetime import time as _time
from zoneinfo import ZoneInfo as _ZoneInfo

from agent import blackscholes as _bs

_ET = _ZoneInfo("America/New_York")
_0DTE_EXP = "2026-09-03"
_0DTE_NOW = _dt(2026, 9, 3, 11, 0, tzinfo=_ET)  # ~5h to the 16:00 ET close — today's real gap


def _0dte_chain(spot: float, strikes: list[float], sigma: float = 0.15,
                *, with_greeks: set[float] | None = None) -> dict:
    """A synthetic 0DTE chain: real (Black-Scholes-consistent) quotes, but NO greeks/IV —
    exactly the shape Alpaca returns for same-day expiry. `with_greeks` strikes get Alpaca-style
    complete data instead, to test that the backfill leaves real data alone."""
    T = (_dt.combine(date.fromisoformat(_0DTE_EXP), _time(16, 0), tzinfo=_ET) - _0DTE_NOW
        ).total_seconds() / (365.25 * 24 * 3600)
    chain = {}
    for k in strikes:
        for cp, is_call in (("C", True), ("P", False)):
            sym = occ("SPY", date.fromisoformat(_0DTE_EXP), cp, k)
            price = _bs.bs_price(spot, k, T, 0.045, sigma, is_call)
            q = {"bp": round(price * 0.97, 4), "ap": round(price * 1.03, 4)}
            if with_greeks and k in with_greeks:
                chain[sym] = {
                    "latestQuote": q,
                    "impliedVolatility": 0.9999,  # sentinel: must survive untouched
                    "greeks": {"delta": 0.4242, "gamma": 0.4242},
                }
            else:
                chain[sym] = {"latestQuote": q}  # no greeks, no IV — the real 0DTE shape
    return chain


def test_backfill_fills_a_chain_alpaca_left_empty():
    spot = 771.0
    chain = _0dte_chain(spot, [spot - 2, spot, spot + 2], sigma=0.15)
    n = sg._backfill_missing_greeks(chain, spot, _0DTE_EXP, _0DTE_NOW)

    assert n == len(chain)  # every contract was missing data -> every one got filled
    for snap in chain.values():
        assert 0.0 < snap["impliedVolatility"] < 5.0
        assert -1.0 <= snap["greeks"]["delta"] <= 1.0
        assert snap["greeks"]["gamma"] >= 0.0


def test_backfill_recovers_the_sigma_it_was_priced_with():
    spot = 771.0
    chain = _0dte_chain(spot, [spot], sigma=0.18)  # ATM, single strike, both C and P
    sg._backfill_missing_greeks(chain, spot, _0DTE_EXP, _0DTE_NOW)
    for snap in chain.values():
        assert snap["impliedVolatility"] == pytest.approx(0.18, abs=0.02)


def test_backfill_never_touches_a_contract_alpaca_already_measured():
    spot = 771.0
    chain = _0dte_chain(spot, [spot - 2, spot, spot + 2], sigma=0.15,
                        with_greeks={spot})
    sg._backfill_missing_greeks(chain, spot, _0DTE_EXP, _0DTE_NOW)
    for sym, snap in chain.items():
        if "P00771000" in sym or "C00771000" in sym:
            # the sentinel values from _0dte_chain must survive completely unchanged
            assert snap["impliedVolatility"] == 0.9999
            assert snap["greeks"] == {"delta": 0.4242, "gamma": 0.4242}


def test_backfill_returns_zero_below_the_time_floor():
    """Two minutes from the close (or less), it doesn't even try — IV is not meaningfully
    defined that close to expiry, and the existing `data` stand-down is the safe fallback."""
    spot = 771.0
    chain = _0dte_chain(spot, [spot], sigma=0.15)
    almost_closed = _dt.combine(date.fromisoformat(_0DTE_EXP), _time(15, 59), tzinfo=_ET)
    n = sg._backfill_missing_greeks(chain, spot, _0DTE_EXP, almost_closed)
    assert n == 0
    for snap in chain.values():
        assert "greeks" not in snap and "impliedVolatility" not in snap


def test_build_signal_end_to_end_on_a_real_0dte_shaped_chain():
    """The actual 3 Sep scenario: a chain with real quotes but zero native greeks/IV must not
    stand down on `data` once fetch() has backfilled it."""
    spot = 771.0
    strikes = [spot + i for i in range(-6, 7)]
    chain = _0dte_chain(spot, strikes, sigma=0.15)
    iv_backfilled = sg._backfill_missing_greeks(chain, spot, _0DTE_EXP, _0DTE_NOW)
    assert iv_backfilled > 0

    oi = {sym: 1000 for sym in chain}
    bars = range_bars()  # calm, realistic RV so vrp_ratio isn't degenerate
    data = {"spot": spot, "expiration": _0DTE_EXP, "chain": chain, "oi": oi, "bars": bars,
            "iv_backfilled": iv_backfilled}

    s = sg.build_signal("SPY", data, params())
    assert s.stand_down != "data", s.notes
    assert np.isfinite(s.atm_iv) and s.atm_iv > 0
    assert s.iv_backfilled == iv_backfilled
    assert "Black-Scholes" in s.notes


def test_build_signal_still_stands_down_on_data_past_the_time_floor():
    spot = 771.0
    chain = _0dte_chain(spot, [spot - 2, spot, spot + 2], sigma=0.15)
    oi = {sym: 1000 for sym in chain}
    almost_closed = _dt.combine(date.fromisoformat(_0DTE_EXP), _time(15, 59), tzinfo=_ET)
    iv_backfilled = sg._backfill_missing_greeks(chain, spot, _0DTE_EXP, almost_closed)
    data = {"spot": spot, "expiration": _0DTE_EXP, "chain": chain, "oi": oi, "bars": range_bars(),
            "iv_backfilled": iv_backfilled}

    s = sg.build_signal("SPY", data, params())
    assert s.stand_down == "data"
    assert s.iv_backfilled == 0
