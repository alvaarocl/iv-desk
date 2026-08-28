"""Signal layer — deterministic. Reads the option surface, not the price chart.

Owner: lane A. Depends on Day-0 probe 2 (do snapshots carry greeks/IV?).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Signal:
    underlying: str
    sell_premium: bool
    structure: str          # iron_condor | put_credit_spread | call_credit_spread | debit_spread | none
    bias: str               # bullish | bearish | neutral
    conviction: float       # 0..1
    regime: str             # trending_up | trending_down | range | chop
    vrp: float
    gex_sign: int           # +1 dealers long gamma, -1 short
    atm_iv: float
    rv_hat: float
    skew: float
    notes: str


def yang_zhang_rv(open_, high, low, close, window: int = 20) -> float:
    """Annualized Yang-Zhang realized-vol estimate over `window` days. Returns a fraction (e.g. 0.12)."""
    o, h, l, c = (np.asarray(x, float) for x in (open_, high, low, close))
    log_ho, log_lo, log_co = np.log(h / o), np.log(l / o), np.log(c / o)
    log_oc = np.log(o[1:] / c[:-1])
    log_cc = np.log(c[1:] / c[:-1])
    n = window
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    sigma_o2 = np.var(log_oc[-n:], ddof=1)
    sigma_c2 = np.var(log_cc[-n:], ddof=1)
    sigma_rs2 = np.mean((log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co))[-n:])
    return float(np.sqrt((sigma_o2 + k * sigma_c2 + (1 - k) * sigma_rs2) * 252))


def ewma_rv(close, lam: float = 0.94) -> float:
    r = np.diff(np.log(np.asarray(close, float)))
    w = (1 - lam) * lam ** np.arange(len(r))[::-1]
    return float(np.sqrt(np.sum(w * r**2) / np.sum(w) * 252))


def compute_gex(chain_greeks: dict, oi: dict, spot: float, band: float) -> float:
    """SpotGamma-style aggregate dealer gamma exposure over strikes within +/- band of spot.

    chain_greeks: {occ_symbol: {"gamma": float, "type": "C"|"P", "strike": float}}
    oi:           {occ_symbol: int}
    """
    total = 0.0
    lo, hi = spot * (1 - band), spot * (1 + band)
    for sym, g in chain_greeks.items():
        if not (lo <= g["strike"] <= hi) or sym not in oi:
            continue
        sign = 1.0 if g["type"] == "C" else -1.0
        total += g["gamma"] * oi[sym] * 100 * spot**2 * 0.01 * sign
    return total


def build_signal(underlying: str, market_data: dict, params) -> Signal:
    """market_data: everything fetched by execution.fetch_market_data(underlying).

    TODO(lane A): assemble RV forecast, VRP, GEX, skew, regime → Signal.
    Keep this pure and unit-tested — no network, no LLM.
    """
    raise NotImplementedError
