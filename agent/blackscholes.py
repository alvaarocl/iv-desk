"""Black-Scholes — pure math, no package dependencies beyond `math`.

Exists for exactly one reason: Alpaca's free/indicative feed does not publish greeks or
implied volatility for options expiring same-day (0DTE) — verified live 3 Sep against the
real chain (0 of 192 SPY 0DTE contracts carried greeks, vs 153 of 216 for the next
expiration). `signal.py` backfills those two fields from the real mid-price we do have,
inverting Black-Scholes for the missing implied vol and computing delta/gamma from it. No
`scipy` dependency — the normal CDF/PDF are `math.erf`, already stdlib.

`implied_vol` uses bisection, not Newton-Raphson. As time-to-expiry approaches zero, vega
(the Newton step's denominator) approaches zero too, so Newton either diverges or oscillates
right where this module is needed most. Bisection only needs `bs_price` to be monotonic in
sigma (it is, for sigma > 0), so it degrades gracefully instead of blowing up. It returns
`None` — never an extrapolated guess — whenever the observed price violates no-arbitrage
bounds or isn't reachable inside the search range.
"""

from __future__ import annotations

import math

SQRT_2 = math.sqrt(2.0)
SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / SQRT_2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    v = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / v
    return d1, d1 - v


def bs_price(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
    """European option price. Falls back to discounted intrinsic value at the T/sigma
    boundary (T<=0 or sigma<=0) instead of dividing by zero."""
    if T <= 0.0 or sigma <= 0.0:
        intrinsic = max(0.0, S - K) if is_call else max(0.0, K - S)
        return intrinsic
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    disc_K = K * math.exp(-r * T)
    if is_call:
        return S * _norm_cdf(d1) - disc_K * _norm_cdf(d2)
    return disc_K * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def bs_delta(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
    if T <= 0.0 or sigma <= 0.0:
        # Expired / degenerate: delta is a step function of moneyness.
        if is_call:
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1.0


def bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0.0 or sigma <= 0.0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))


def bs_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Price change per unit of sigma. Same for calls and puts."""
    if T <= 0.0 or sigma <= 0.0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return S * _norm_pdf(d1) * math.sqrt(T)


def implied_vol(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    is_call: bool,
    *,
    lo: float = 0.01,
    hi: float = 5.0,
    tol: float = 1e-4,
    max_iter: int = 60,
) -> float | None:
    """Invert `bs_price` for sigma via bisection over `[lo, hi]`.

    Returns None — never a guess — when:
      * `T` or `price` is non-positive,
      * `price` sits at or below the discounted-intrinsic no-arbitrage floor (an unsolvable
        or already-expired-looking quote),
      * the target isn't bracketed by `[lo, hi]` (price achievable at `hi` is still below it,
        or price at `lo` is already above it) — the true answer would be an extrapolation, or
      * the recovered point has near-zero vega — deep ITM/OTM and/or very short-dated
        contracts have a price curve that goes nearly flat in sigma, so a converged *price*
        (within `tol`) can sit under a wide range of very different sigmas. Verified live:
        every case where a synthetic round-trip test (fix sigma, price it, invert, compare)
        disagreed with its own input had vega below ~0.005 — the inversion is not wrong, the
        question is underdetermined at that vega, and returning a number would be false
        confidence, not a measurement.
    """
    if T <= 0.0 or price <= 0.0:
        return None

    disc_K = K * math.exp(-r * T)
    floor = max(0.0, S - disc_K) if is_call else max(0.0, disc_K - S)
    if price <= floor:
        return None
    # A call can never be worth more than the spot; a put never more than the discounted
    # strike. Above that the quote itself is not a Black-Scholes-consistent price.
    ceiling = S if is_call else disc_K
    if price >= ceiling:
        return None

    f_lo = bs_price(S, K, T, r, lo, is_call) - price
    f_hi = bs_price(S, K, T, r, hi, is_call) - price
    if f_lo > 0.0 or f_hi < 0.0:
        return None

    VEGA_FLOOR = 5e-3

    def _confident(sigma: float) -> float | None:
        return sigma if bs_vega(S, K, T, r, sigma) >= VEGA_FLOOR else None

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = bs_price(S, K, T, r, mid, is_call) - price
        if abs(f_mid) < tol:
            return _confident(mid)
        if f_mid > 0.0:
            hi = mid
        else:
            lo = mid
    return _confident((lo + hi) / 2.0)
