"""Pure Black-Scholes math — no chain, no network. Exists to backfill 0DTE greeks/IV that
Alpaca's feed doesn't publish (see agent/signal.py's `_backfill_missing_greeks`)."""

from __future__ import annotations

import math

import pytest

from agent import blackscholes as bs

S, K, T, R = 100.0, 100.0, 1.0, 0.05


# ---------- round trip: the property that actually matters ----------


@pytest.mark.parametrize("sigma, K, T, is_call", [
    (0.20, 100.0, 1.0, True),
    (0.20, 100.0, 1.0, False),
    (0.35, 95.0, 0.5, True),
    (0.15, 105.0, 0.5, False),
    (0.60, 100.0, 0.01, True),          # short-dated, high vol
    (0.12, 100.0, 4 / (365.25 * 24), True),   # ~4 hours to expiry — today's real scenario
    (0.12, 100.0, 4 / (365.25 * 24), False),
])
def test_implied_vol_recovers_the_sigma_that_generated_the_price(sigma, K, T, is_call):
    price = bs.bs_price(S, K, T, R, sigma, is_call)
    recovered = bs.implied_vol(price, S, K, T, R, is_call)
    assert recovered is not None
    assert recovered == pytest.approx(sigma, abs=5e-4)


def test_recovers_across_a_grid_of_strikes_and_maturities():
    """Not just one lucky case — a spread of moneyness and short maturities."""
    for K_ in (80.0, 90.0, 100.0, 110.0, 120.0):
        for T_ in (1 / 365.25, 0.05, 0.5, 1.0):
            for sigma_ in (0.10, 0.25, 0.50):
                for is_call in (True, False):
                    price = bs.bs_price(S, K_, T_, R, sigma_, is_call)
                    if price <= 0:
                        continue
                    recovered = bs.implied_vol(price, S, K_, T_, R, is_call)
                    if recovered is None:
                        continue  # deep ITM/OTM can be genuinely unsolvable near the bounds
                    assert recovered == pytest.approx(sigma_, abs=2e-3)


# ---------- shape sanity: delta and gamma ----------


def test_call_delta_between_0_and_1():
    d = bs.bs_delta(S, K, T, R, 0.2, is_call=True)
    assert 0.0 <= d <= 1.0


def test_put_delta_between_minus_1_and_0():
    d = bs.bs_delta(S, K, T, R, 0.2, is_call=False)
    assert -1.0 <= d <= 0.0


def test_deep_itm_call_delta_near_one():
    assert bs.bs_delta(S, 50.0, T, R, 0.2, is_call=True) > 0.95


def test_deep_otm_call_delta_near_zero():
    assert bs.bs_delta(S, 200.0, T, R, 0.2, is_call=True) < 0.05


def test_gamma_is_never_negative():
    for K_ in (80.0, 100.0, 120.0):
        assert bs.bs_gamma(S, K_, T, R, 0.2) >= 0.0


def test_gamma_peaks_near_the_money():
    atm = bs.bs_gamma(S, 100.0, T, R, 0.2)
    otm = bs.bs_gamma(S, 150.0, T, R, 0.2)
    itm = bs.bs_gamma(S, 50.0, T, R, 0.2)
    assert atm > otm and atm > itm


# ---------- refuses to invent a number ----------


def test_price_at_or_below_intrinsic_floor_is_unsolvable():
    # A call struck deep ITM priced at exactly its discounted-intrinsic floor implies zero
    # time value -> no finite sigma reproduces it inside a sane search range.
    K_ = 50.0
    disc_K = K_ * math.exp(-R * T)
    floor_price = S - disc_K
    assert bs.implied_vol(floor_price, S, K_, T, R, is_call=True) is None


def test_price_above_spot_is_not_a_valid_call_quote():
    assert bs.implied_vol(S + 1.0, S, K, T, R, is_call=True) is None


def test_zero_or_negative_time_returns_none():
    assert bs.implied_vol(5.0, S, K, 0.0, R, is_call=True) is None
    assert bs.implied_vol(5.0, S, K, -0.01, R, is_call=True) is None


def test_zero_or_negative_price_returns_none():
    assert bs.implied_vol(0.0, S, K, T, R, is_call=True) is None
    assert bs.implied_vol(-1.0, S, K, T, R, is_call=True) is None


def test_price_needing_more_than_500_percent_vol_returns_none():
    # An absurdly rich price for the strike/maturity — outside the [1%, 500%] search bracket.
    assert bs.implied_vol(S * 0.99, S, K, 1 / 365.25, R, is_call=True) is None


def test_near_zero_vega_declines_rather_than_guesses():
    """Deep OTM + short-dated: the price curve is nearly flat in sigma, so a converged price
    sits under a wide range of sigmas. Confirmed via a real failing case (K=90, T~4h, sigma=0.25
    call) before the vega floor was added — this pins that fix."""
    K_, T_ = 90.0, 1 / 365.25 * 4 / 24  # ~4 hours, matches today's real 0DTE scenario
    vega = bs.bs_vega(S, K_, T_, R, 0.25)
    assert vega < 5e-3, "test setup should land in the low-vega regime"
    price = bs.bs_price(S, K_, T_, R, 0.25, is_call=True)
    assert bs.implied_vol(price, S, K_, T_, R, is_call=True) is None


def test_realistic_atm_0dte_recovers_confidently():
    """The case that actually matters: near-the-money, hours to the close — where the desk's
    short strikes live. Must NOT be caught by the vega floor."""
    T_ = 4 / (365.25 * 24)  # ~4 hours to the 4pm ET close
    for sigma_ in (0.10, 0.15, 0.20, 0.30):
        price = bs.bs_price(S, K, T_, R, sigma_, is_call=True)
        recovered = bs.implied_vol(price, S, K, T_, R, is_call=True)
        assert recovered is not None
        assert recovered == pytest.approx(sigma_, abs=2e-3)


# ---------- degenerate T/sigma never crashes ----------


def test_bs_price_at_zero_time_is_pure_intrinsic():
    assert bs.bs_price(S, 90.0, 0.0, R, 0.2, is_call=True) == pytest.approx(10.0)
    assert bs.bs_price(S, 110.0, 0.0, R, 0.2, is_call=True) == pytest.approx(0.0)


def test_bs_delta_and_gamma_at_zero_time_do_not_raise():
    assert bs.bs_delta(S, 90.0, 0.0, R, 0.2, is_call=True) == 1.0
    assert bs.bs_delta(S, 110.0, 0.0, R, 0.2, is_call=True) == 0.0
    assert bs.bs_gamma(S, 100.0, 0.0, R, 0.2) == 0.0
