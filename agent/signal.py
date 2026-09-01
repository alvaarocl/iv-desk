"""Signal layer — deterministic. Reads the option surface, not the price chart.

VRP (implied vs forecast realized vol) decides *whether* to sell premium.
GEX (dealer gamma from open interest) decides *what structure* and *how aggressively*.
Regime + skew shape the strikes. No network here beyond the passed-in data, no LLM.

Three gates, each of which can independently say "stand down", and each of which writes its
reason into `Signal.notes` so `data/journal.jsonl` shows the desk *deciding* not to trade
rather than just being silent:

  1. VRP     — IV / RV_hat must clear `vrp_ratio_min` (relative, not absolute; see issue #6).
  2. GEX     — normalized dealer gamma must clear +`gex_min`; the band around zero is a dead
               zone that returns regime "chop" instead of flip-flopping on a T-2 datapoint.
  3. Regime  — trending tape means no short premium at all unless `params.fade_trend` (#12).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from . import broker
from . import marketdata as md

# The P&L window is measured on total equity at the close of Thu 3 Sep, and Alpaca confirmed in
# Discord that Fri-4-Sep expirations are excluded from the measurement. A position expiring after
# the snapshot is therefore strictly bad: it cannot realize inside the window, and it still marks
# to market against the scored equity as premium we sold and have not yet earned. So the desk may
# never open past this date — the rule was a locked decision in CLAUDE.md/STATUS.md that had no
# code behind it until now. Overridable so the tests (and any future window) do not need an edit.
LAST_EXPIRATION = date.fromisoformat(os.environ.get("DESK_LAST_EXPIRATION", "2026-09-03"))


@dataclass
class Signal:
    underlying: str
    spot: float
    sell_premium: bool
    structure: str          # iron_condor | put_credit_spread | call_credit_spread | none
    bias: str               # bullish | bearish | neutral
    regime: str             # trending_up | trending_down | range | chop
    expiration: str         # YYYY-MM-DD
    vrp: float              # IV - RV_hat, informational only (journal / write-up)
    vrp_ratio: float        # IV / RV_hat — this is what the gate actually reads
    atm_iv: float
    rv_hat: float
    gex: float              # raw dollar GEX, informational
    gex_sign: int           # raw sign of `gex`, informational
    gex_norm: float         # net / gross gamma notional, in [-1, 1]
    gex_state: int          # +1 long gamma / 0 dead zone / -1 short gamma, after `gex_min`
    skew: float
    stand_down: str         # "" when trading, else the gate that blocked: vrp | gex | trend | data
    notes: str
    chain: dict = field(default_factory=dict, repr=False)


# ---------- realized-vol forecast ----------

def yang_zhang_rv(bars: list[dict], window: int = 20) -> float:
    """Yang-Zhang realized vol, annualized.

    Every component is built on the *same* n periods. A "period" needs the previous close
    (for the overnight gap), so with N bars there are only N-1 usable periods and the last
    n of them are `[-n:]` of arrays that were all sliced off the same alignment. The old
    version mixed length-N arrays (log_ho/log_lo/log_co) with length-(N-1) ones
    (log_oc/log_cc), so the range terms were one day ahead of the gap terms — issue #6.

    Also: the middle term is the *open-to-close* variance, not close-to-close. Using
    close-to-close double-counts the overnight gap that sigma_o already carries, which
    inflates RV_hat and biases the VRP gate toward never firing.
    """
    o = np.array([b["o"] for b in bars], float)
    h = np.array([b["h"] for b in bars], float)
    lo = np.array([b["l"] for b in bars], float)
    c = np.array([b["c"] for b in bars], float)
    if len(c) < 3:
        return float("nan")                      # not enough history for a 2-period variance
    n = min(window, len(c) - 1)

    o_n, h_n, l_n, c_n = o[-n:], h[-n:], lo[-n:], c[-n:]
    c_prev = c[-n - 1:-1]
    log_oc = np.log(o_n / c_prev)                # overnight: previous close -> open
    log_co = np.log(c_n / o_n)                   # open -> close
    log_ho = np.log(h_n / o_n)
    log_lo = np.log(l_n / o_n)

    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    sigma_o2 = np.var(log_oc, ddof=1)
    sigma_c2 = np.var(log_co, ddof=1)
    sigma_rs2 = np.mean(log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co))
    return float(np.sqrt(max(sigma_o2 + k * sigma_c2 + (1 - k) * sigma_rs2, 1e-9) * 252))


def ewma_rv(bars: list[dict], lam: float = 0.94) -> float:
    c = np.array([b["c"] for b in bars], float)
    if len(c) < 2:
        return float("nan")
    r = np.diff(np.log(c))
    w = (1 - lam) * lam ** np.arange(len(r))[::-1]
    return float(np.sqrt(np.sum(w * r**2) / np.sum(w) * 252))


def rv_forecast(bars: list[dict]) -> float:
    """Blend Yang-Zhang (range-efficient) with EWMA (recency-weighted).

    Known limitation, kept deliberately: this is a 20-session annualized number compared
    against 1-3 DTE implied vol. The horizons do not match. We do not rescale because the
    gate is a *ratio* (`vrp_ratio_min`) and the horizon bias is roughly multiplicative and
    stable, so it is absorbed by calibrating the ratio on the backtest (#5) instead of by
    a term-structure model we cannot validate in four sessions.
    """
    yz, ew = yang_zhang_rv(bars), ewma_rv(bars)
    if not np.isfinite(yz) or not np.isfinite(ew):
        return float("nan")
    return 0.5 * yz + 0.5 * ew


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


def compute_gex(chain: dict, oi: dict[str, int], spot: float, band: float) -> tuple[float, float]:
    """Aggregate dealer gamma exposure within +/- `band` of spot. Calls +, puts -.

    Returns `(gex, gex_norm)`:

    * `gex` — SpotGamma-style dollars of dealer delta to re-hedge per 1% move.
    * `gex_norm` — `gex` divided by the *gross* (absolute) gamma notional of the same
      strikes, so it lands in [-1, 1]: +1 = all dealer gamma is long, -1 = all short,
      0 = call and put gamma cancel exactly.

    Why normalize this way (issue #10). The raw dollar figure scales with spot**2, with
    the open-interest level, and with the vol regime (gamma itself moves with IV and DTE).
    A fixed dollar threshold therefore means three different things for SPY vs IWM, for
    September vs March, and for a quiet tape vs a busy one. Dividing by gross gamma
    notional cancels all three at once and leaves a pure *imbalance ratio* — which is the
    quantity the regime gate actually cares about ("are dealers net long gamma here, and
    by enough to matter?"), is directly comparable across the universe, and degrades
    gracefully when the open interest is stale (Alpaca only publishes it at T-2).

    Alternative considered: dividing by spot**2 alone. Rejected because it still scales
    with OI, so SPY and IWM would need different thresholds.
    """
    lo, hi = spot * (1 - band), spot * (1 + band)
    net = 0.0
    gross = 0.0
    for sym, s in chain.items():
        g = s.get("greeks")
        if not g or sym not in oi:
            continue
        _, _, cp, k = md.parse_occ(sym)
        if not (lo <= k <= hi):
            continue
        sign = 1.0 if cp == "C" else -1.0
        contrib = g["gamma"] * oi[sym] * 100 * spot**2 * 0.01
        net += contrib * sign
        gross += abs(contrib)
    return net, (net / gross if gross > 0 else 0.0)


def gex_state(gex_norm: float, gex_min: float) -> int:
    """+1 dealers long gamma with magnitude, -1 short with magnitude, 0 = dead zone.

    The dead zone is the whole point: open interest is T-2, so a `gex_norm` of +0.01 and
    one of -0.01 are the same reading with different noise, and a bare sign test made the
    desk flip between "sell condors" and "stand down" every 15 minutes.
    """
    if gex_norm >= gex_min:
        return 1
    if gex_norm <= -gex_min:
        return -1
    return 0


def classify_regime(bars: list[dict], state: int, fade_trend: bool = False) -> tuple[str, str]:
    """-> (regime, bias). `state` is the output of `gex_state`, not a bare sign.

    `bias` is the honest read of the tape: a trending-up market is `bullish`. Under
    `fade_trend=True` (the legacy behaviour, see issue #12) it is deliberately inverted so
    that `build_signal` sells the side the market is running into.
    """
    c = np.array([b["c"] for b in bars], float)
    if state == 0:
        return "chop", "neutral"                 # GEX dead zone — no defensible regime call
    ema20 = _ema(c, 20)
    ema50 = _ema(c, min(50, len(c)))
    adx = _adx(bars, 14)
    last = c[-1]
    trending = adx > 22
    up = last > ema20 > ema50
    down = last < ema20 < ema50
    if trending and up:
        return "trending_up", ("bearish" if fade_trend else "bullish")
    if trending and down:
        return "trending_down", ("bullish" if fade_trend else "bearish")
    if state > 0 and adx < 18:
        return "range", "neutral"
    return "chop", "neutral"


def _ema(x: np.ndarray, n: int) -> float:
    a = 2 / (n + 1)
    e = x[0]
    for v in x[1:]:
        e = a * v + (1 - a) * e
    return float(e)


def _adx(bars: list[dict], n: int = 14) -> float:
    """Wilder's ADX: DX smoothed with an n-period RMA.

    The previous implementation collapsed +DI/-DI to scalars and returned a single DX,
    which is a much noisier and much higher number than an ADX — so the `> 22` threshold
    in strategy-spec.md did not mean what it said (issue #12). Everything below is now a
    series; only the final value is collapsed.
    """
    h = np.array([b["h"] for b in bars], float)
    lo = np.array([b["l"] for b in bars], float)
    c = np.array([b["c"] for b in bars], float)
    if len(c) < n + 2:
        return 0.0
    up, dn = h[1:] - h[:-1], lo[:-1] - lo[1:]
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = np.maximum.reduce([h[1:] - lo[1:], np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])])
    atr = _rma(tr, n)
    pdi = 100 * _rma(plus_dm, n) / (atr + 1e-9)
    mdi = 100 * _rma(minus_dm, n) / (atr + 1e-9)
    dx = 100 * np.abs(pdi - mdi) / (pdi + mdi + 1e-9)
    adx = _rma(dx, n)
    if adx.size:
        return float(adx[-1])
    return float(dx[-1]) if dx.size else 0.0


def _rma(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing, as a series. Returns length max(len(x) - n + 1, 0)."""
    if len(x) < n:
        return np.array([])
    out = np.empty(len(x) - n + 1)
    r = float(np.mean(x[:n]))
    out[0] = r
    for i, v in enumerate(x[n:], start=1):
        r = (r * (n - 1) + float(v)) / n
        out[i] = r
    return out


# ---------- data fetch ----------

def pick_expiration(
    underlying: str,
    spot: float,
    min_dte: int = 1,
    max_dte: int = 3,
    last_expiration: date | None = None,
) -> str | None:
    """Nearest expiration in [min_dte, max_dte] that still lands on or before the scoring cutoff.

    Returns None rather than a fallback when nothing qualifies. The old code fell back to
    `exps[0]` (the nearest expiration, whatever it was), which on Thu 3 Sep would have handed
    back Fri 4 Sep — every trade of the final session opened outside the measured window. A
    stand-down is the only safe answer: an expiration we cannot score is worse than no trade.

    On the cutoff day itself the 1-3 DTE band is empty by construction, so same-day expiry is
    accepted as a second pass. That is deliberate 0DTE, and it stays governed by the existing
    `no_new_0dte_after_et` gate in risk.evaluate().
    """
    cutoff = LAST_EXPIRATION if last_expiration is None else last_expiration
    today = date.today()
    cons = broker.option_contracts(
        underlying,
        expiration_date_gte=today.isoformat(),
        type_="call",
        strike_gte=spot * 0.99,
        strike_lte=spot * 1.01,
    )
    dated = sorted(
        (date.fromisoformat(e) for e in {c["expiration_date"] for c in cons}) if cons else []
    )
    eligible = [e for e in dated if e <= cutoff]
    for e in eligible:
        if min_dte <= (e - today).days <= max_dte:
            return e.isoformat()
    # Cutoff day: nothing left in the preferred band, so take same-day expiry if it exists.
    for e in eligible:
        if (e - today).days == 0:
            return e.isoformat()
    return None


def fetch(underlying: str, params) -> dict:
    spot = md.stock_price(underlying)
    exp = pick_expiration(underlying, spot)
    if exp is None:
        # Past the scoring cutoff: skip the chain and open-interest calls entirely. build_signal
        # turns this into an explicit `expiration` stand-down rather than a silent "data" one.
        return {"spot": spot, "expiration": None, "chain": {}, "oi": {}, "bars": []}
    lo, hi = spot * (1 - params.gex_band - 0.02), spot * (1 + params.gex_band + 0.02)
    chain = md.option_chain_snapshot(underlying, expiration_date=exp, strike_gte=lo, strike_lte=hi)
    cons = broker.option_contracts(underlying, expiration_date=exp, strike_gte=lo, strike_lte=hi)
    oi = {c["symbol"]: int(c["open_interest"]) for c in cons if c["open_interest"]}
    bars = md.daily_bars(underlying, 55)
    return {"spot": spot, "expiration": exp, "chain": chain, "oi": oi, "bars": bars}


# ---------- main ----------

def _fallback_structure(regime: str, bias: str) -> str:
    """The structure a signal would trade once it clears every gate, given regime/bias.

    Factored out so `build_signal`'s real gate ladder and the shadow-debate counterfactual in
    `desk.py` (a candidate that GEX vetoed but would otherwise have cleared) always pick the same
    structure — one source of truth instead of two copies that can drift apart.
    """
    if regime == "range" or bias not in ("bullish", "bearish"):
        return "iron_condor"
    return "put_credit_spread" if bias == "bullish" else "call_credit_spread"


def build_signal(underlying: str, data: dict, params) -> Signal:
    spot, chain, oi, bars = data["spot"], data["chain"], data["oi"], data["bars"]
    iv = atm_iv(chain, spot)
    rv = rv_forecast(bars)
    have_vol = bool(np.isfinite(iv) and np.isfinite(rv) and iv > 0 and rv > 0)
    vrp = float(iv - rv) if have_vol else float("nan")
    ratio = float(iv / rv) if have_vol else float("nan")

    gex, gex_norm = compute_gex(chain, oi, spot, params.gex_band)
    state = gex_state(gex_norm, params.gex_min)
    put_iv = iv_at_delta(chain, 0.25, "P")
    call_iv = iv_at_delta(chain, 0.25, "C")
    skew = (put_iv - call_iv) if (put_iv and call_iv) else 0.0
    regime, bias = classify_regime(bars, state, params.fade_trend)

    # --- the stand-down gates, in order of how cheap they are to evaluate ---
    structure, sell, stand_down = "none", False, ""
    if not data.get("expiration"):
        stand_down = "expiration"                # nothing left on or before the scoring cutoff
    elif not have_vol:
        stand_down = "data"                      # no usable IV or not enough bar history
    elif ratio < params.vrp_ratio_min:
        stand_down = "vrp"                       # options are not rich *relative to* realized
    elif state <= 0:
        stand_down = "gex"                       # dealers short gamma, or inside the dead zone
    elif regime in ("trending_up", "trending_down") and not params.fade_trend:
        stand_down = "trend"                     # issue #12: no short premium into a trend
    else:
        structure, sell = _fallback_structure(regime, bias), True

    if have_vol:
        head = f"IV {iv:.1%} vs RV_hat {rv:.1%} (ratio {ratio:.2f} vs {params.vrp_ratio_min:.2f})"
    else:
        head = "IV/RV unavailable"
    notes = (f"{head}; GEX_norm {gex_norm:+.3f} (|min| {params.gex_min:.2f}, state {state:+d}); "
             f"regime {regime}; skew {skew:+.1%}"
             + (f"; STAND DOWN [{stand_down}]" if stand_down else f"; {structure}"))

    return Signal(
        underlying=underlying, spot=spot, sell_premium=sell, structure=structure, bias=bias,
        regime=regime, expiration=data["expiration"] or "",
        vrp=round(vrp, 4), vrp_ratio=round(ratio, 3),
        atm_iv=round(iv, 4), rv_hat=round(rv, 4),
        gex=gex, gex_sign=(1 if gex >= 0 else -1), gex_norm=round(gex_norm, 4), gex_state=state,
        skew=round(skew, 4), stand_down=stand_down, notes=notes, chain=chain,
    )
