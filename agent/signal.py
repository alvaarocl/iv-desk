"""Signal layer — deterministic. Reads the option surface, not the price chart.

VRP (implied vs forecast realized vol) decides *whether* to sell premium.
GEX (dealer gamma from open interest) decides *what structure* and *how aggressively*.
Regime + skew shape the strikes. No network here beyond the passed-in data, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

from . import broker
from . import marketdata as md


@dataclass
class Signal:
    underlying: str
    spot: float
    sell_premium: bool
    structure: str          # iron_condor | put_credit_spread | call_credit_spread | debit_spread | none
    bias: str               # bullish | bearish | neutral
    conviction: float       # 0..1
    regime: str             # trending_up | trending_down | range | chop
    expiration: str         # YYYY-MM-DD
    vrp: float
    atm_iv: float
    rv_hat: float
    gex: float
    gex_sign: int
    skew: float
    notes: str
    chain: dict = field(default_factory=dict, repr=False)


# ---------- realized-vol forecast ----------

def yang_zhang_rv(bars: list[dict], window: int = 20) -> float:
    o = np.array([b["o"] for b in bars], float)
    h = np.array([b["h"] for b in bars], float)
    lo = np.array([b["l"] for b in bars], float)
    c = np.array([b["c"] for b in bars], float)
    if len(c) < window + 2:
        window = len(c) - 2
    n = window
    log_ho, log_lo, log_co = np.log(h / o), np.log(lo / o), np.log(c / o)
    log_oc = np.log(o[1:] / c[:-1])
    log_cc = np.log(c[1:] / c[:-1])
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    sigma_o2 = np.var(log_oc[-n:], ddof=1)
    sigma_c2 = np.var(log_cc[-n:], ddof=1)
    sigma_rs2 = np.mean((log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co))[-n:])
    return float(np.sqrt(max(sigma_o2 + k * sigma_c2 + (1 - k) * sigma_rs2, 1e-9) * 252))


def ewma_rv(bars: list[dict], lam: float = 0.94) -> float:
    c = np.array([b["c"] for b in bars], float)
    r = np.diff(np.log(c))
    w = (1 - lam) * lam ** np.arange(len(r))[::-1]
    return float(np.sqrt(np.sum(w * r**2) / np.sum(w) * 252))


def rv_forecast(bars: list[dict]) -> float:
    """Blend Yang-Zhang (range-efficient) with EWMA (recency-weighted)."""
    return 0.5 * yang_zhang_rv(bars) + 0.5 * ewma_rv(bars)


# ---------- surface reads ----------

def atm_iv(chain: dict, spot: float) -> float:
    """Average IV of the ~6 strikes nearest spot (call+put), robust to one bad quote."""
    rows = []
    for sym, s in chain.items():
        iv = s.get("impliedVolatility")
        if iv is None or iv <= 0:
            continue
        _, _, _, k = md.parse_occ(sym)
        rows.append((abs(k - spot), float(iv)))
    if not rows:
        return float("nan")
    rows.sort()
    near = [iv for _, iv in rows[:6]]
    return float(np.median(near))


def iv_at_delta(chain: dict, target_delta: float, cp: str) -> float | None:
    best, best_d = None, 1e9
    for sym, s in chain.items():
        g, iv = s.get("greeks"), s.get("impliedVolatility")
        _, _, c, _ = md.parse_occ(sym)
        if not g or iv is None or c != cp:
            continue
        d = abs(abs(g["delta"]) - target_delta)
        if d < best_d:
            best, best_d = iv, d
    return float(best) if best is not None else None


def compute_gex(chain: dict, oi: dict[str, int], spot: float, band: float) -> float:
    """SpotGamma-style aggregate dealer gamma exposure, +/- band of spot. Calls +, puts -."""
    lo, hi = spot * (1 - band), spot * (1 + band)
    total = 0.0
    for sym, s in chain.items():
        g = s.get("greeks")
        if not g or sym not in oi:
            continue
        _, _, cp, k = md.parse_occ(sym)
        if not (lo <= k <= hi):
            continue
        sign = 1.0 if cp == "C" else -1.0
        total += g["gamma"] * oi[sym] * 100 * spot**2 * 0.01 * sign
    return total


def classify_regime(bars: list[dict], gex_sign: int) -> tuple[str, str]:
    c = np.array([b["c"] for b in bars], float)
    ema20 = _ema(c, 20)
    ema50 = _ema(c, min(50, len(c)))
    adx = _adx(bars, 14)
    last = c[-1]
    trending = adx > 22
    up = last > ema20 > ema50
    down = last < ema20 < ema50
    if trending and up:
        return "trending_up", "bearish"      # fade-the-move bias for call side
    if trending and down:
        return "trending_down", "bullish"
    if gex_sign > 0 and adx < 18:
        return "range", "neutral"
    return "chop", "neutral"


def _ema(x: np.ndarray, n: int) -> float:
    a = 2 / (n + 1)
    e = x[0]
    for v in x[1:]:
        e = a * v + (1 - a) * e
    return float(e)


def _adx(bars: list[dict], n: int = 14) -> float:
    h = np.array([b["h"] for b in bars], float)
    lo = np.array([b["l"] for b in bars], float)
    c = np.array([b["c"] for b in bars], float)
    up, dn = h[1:] - h[:-1], lo[:-1] - lo[1:]
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum.reduce([h[1:] - lo[1:], np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])])
    atr = _rma(tr, n)
    pdi = 100 * _rma(plus_dm, n) / (atr + 1e-9)
    mdi = 100 * _rma(minus_dm, n) / (atr + 1e-9)
    dx = 100 * np.abs(pdi - mdi) / (pdi + mdi + 1e-9)
    return float(dx if np.isscalar(dx) else np.mean(dx))


def _rma(x: np.ndarray, n: int) -> float:
    if len(x) < n:
        return float(np.mean(x)) if len(x) else 0.0
    r = np.mean(x[:n])
    for v in x[n:]:
        r = (r * (n - 1) + v) / n
    return float(r)


# ---------- data fetch ----------

def pick_expiration(underlying: str, spot: float, min_dte: int = 1, max_dte: int = 3) -> str:
    today = date.today()
    cons = broker.option_contracts(
        underlying,
        expiration_date_gte=today.isoformat(),
        type_="call",
        strike_gte=spot * 0.99,
        strike_lte=spot * 1.01,
    )
    exps = sorted({c["expiration_date"] for c in cons})
    fallback = exps[0] if exps else today.isoformat()
    for e in exps:
        dte = (date.fromisoformat(e) - today).days
        if min_dte <= dte <= max_dte:
            return e
        if dte == 0 and not fallback:
            fallback = e
    return fallback


def fetch(underlying: str, params) -> dict:
    spot = md.stock_price(underlying)
    exp = pick_expiration(underlying, spot)
    lo, hi = spot * (1 - params.gex_band - 0.02), spot * (1 + params.gex_band + 0.02)
    chain = md.option_chain_snapshot(underlying, expiration_date=exp, strike_gte=lo, strike_lte=hi)
    cons = broker.option_contracts(underlying, expiration_date=exp, strike_gte=lo, strike_lte=hi)
    oi = {c["symbol"]: int(c["open_interest"]) for c in cons if c["open_interest"]}
    bars = md.daily_bars(underlying, 55)
    return {"spot": spot, "expiration": exp, "chain": chain, "oi": oi, "bars": bars}


# ---------- main ----------

def build_signal(underlying: str, data: dict, params) -> Signal:
    spot, chain, oi, bars = data["spot"], data["chain"], data["oi"], data["bars"]
    iv = atm_iv(chain, spot)
    rv = rv_forecast(bars)
    vrp = iv - rv
    gex = compute_gex(chain, oi, spot, params.gex_band)
    gex_sign = 1 if gex >= 0 else -1
    put_iv = iv_at_delta(chain, 0.25, "P")
    call_iv = iv_at_delta(chain, 0.25, "C")
    skew = (put_iv - call_iv) if (put_iv and call_iv) else 0.0
    regime, bias = classify_regime(bars, gex_sign)

    rich = vrp >= params.vrp_min
    sell = rich and gex_sign > 0
    if not rich:
        structure = "none"
    elif gex_sign < 0:
        structure = "debit_spread"          # trending tape — satellite only, directional
        sell = False
    elif regime == "range":
        structure = "iron_condor"
    elif bias == "bullish":
        structure = "put_credit_spread"
    elif bias == "bearish":
        structure = "call_credit_spread"
    else:
        structure = "iron_condor"

    conviction = float(np.clip(
        0.35 + 4 * max(vrp, 0) + (0.15 if regime == "range" else 0.0) + min(abs(skew), 0.05), 0, 1
    ))

    return Signal(
        underlying=underlying, spot=spot, sell_premium=sell, structure=structure, bias=bias,
        conviction=conviction, regime=regime, expiration=data["expiration"], vrp=round(vrp, 4),
        atm_iv=round(iv, 4), rv_hat=round(rv, 4), gex=gex, gex_sign=gex_sign, skew=round(skew, 4),
        notes=f"IV {iv:.1%} vs RV_hat {rv:.1%}; GEX {'+' if gex_sign>0 else '-'} {abs(gex):.2e}; "
              f"regime {regime}; skew {skew:+.1%}",
        chain=chain,
    )
