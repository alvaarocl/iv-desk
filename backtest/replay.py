"""Backtest-lite — does the strategy ever fire? (issue #5)

One binary question: over a ~60-session window, does IV Desk open a single position? The
answer is a FUNNEL TABLE that names the exact gate where every candidate dies, plus a
sensitivity sweep that says what each threshold would have to be for the desk to trade.

Design
------
* The funnel runs the *real* engine — `agent.signal.build_signal`, `agent.desk._pick`,
  `agent.desk._legs_delta`, `agent.execution.select_condor/select_vertical/size`,
  `agent.risk.evaluate`. Nothing under `agent/` is modified or reimplemented here, so the
  counts describe production behaviour, not a paraphrase of it.
* Data acquisition and gate evaluation are separated. A `DayData` (spot, reconstructed
  chain, OI proxy, underlying bars, close at expiry) is fetched or generated once and
  cached; the funnel is then a pure function of `(DayData[], Params)`. Parameter
  sensitivity is therefore free and needs no network — see `sensitivity()`.
* `--synthetic` generates a plausible price path and IV surface, so the whole pipeline can
  be exercised and the funnel validated with no API keys and no network.

Approximations (deliberate — the question is "does it fire?", not "how much does it make?")
  - Historical option *quotes* do not exist on the free tier, so the chain is rebuilt from
    daily bars: close -> implied vol by Black-Scholes inversion (r=0, no dividend) ->
    analytic delta/gamma. Close-as-mid is optimistic versus a real bid/ask, which biases
    the credit gate in the strategy's FAVOUR. If it still dies there, it dies for real.
  - Open interest is not published historically, so daily option *volume* stands in as the
    OI proxy for GEX. GEX is normalized (`gex_norm`) and used as a regime read, so the
    level matters far less than the sign — but treat the GEX row as the softest number here.
  - P&L holds every structure to expiry: no 50% take-profit, no 2x stop. Secondary output.

Usage
-----
    uv run python -m backtest.replay --synthetic     # no keys, no network
    uv run python -m backtest.replay                 # needs ALPACA_API_KEY / ALPACA_SECRET_KEY
    uv run python -m backtest.replay --selftest      # pipeline assertions, no network
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from agent import desk as dk
from agent import execution as ex
from agent import marketdata as md
from agent import risk
from agent import signal as sg
from agent.config import Params

ET = dk.ET
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = Path(__file__).resolve().parent / "cache"
NAV0 = 100_000.0

# Spot levels observed on 28 Aug 2026 (probes/RESULTS.md) — seeds for the synthetic tape.
SYNTH_SPOT = {"SPY": 774.9, "QQQ": 723.9, "IWM": 298.4}
SYNTH_VOL_SCALE = {"SPY": 1.00, "QQQ": 1.25, "IWM": 1.35}
_OVERNIGHT = 0.20      # share of daily variance that arrives in the overnight gap
_STEPS = 32            # intraday steps per synthetic session
TRADING_DAYS = 252.0


def year_frac(trading_days: int = 1) -> float:
    """Business time, not calendar time.

    `signal.rv_forecast` annualizes realized vol by 252, so the option side must use the
    same clock or the VRP gate compares two different units. One session is 1/252 of a
    year whether or not a weekend intervenes: a Friday->Monday option carries one session
    of risk, not three days of it. Pricing that session as 3/365 would inflate every
    premium by ~40% and hand the credit gate an edge it has not earned; pricing it as
    1/365 would deflate every premium by ~20%. Both are wrong in a way that changes the
    answer to issue #5, which is why this is a named function and not an inline constant.
    """
    return trading_days / TRADING_DAYS


# --------------------------------------------------------------------------------------
# Black-Scholes (r = 0, no dividend — at 1-3 DTE the carry terms are noise)
# --------------------------------------------------------------------------------------

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI


def bs(spot: float, strike: float, t: float, sigma: float, cp: str) -> tuple[float, float, float]:
    """-> (price, delta, gamma). `t` in years, `cp` in {'C','P'}."""
    if t <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        intrinsic = max(spot - strike, 0.0) if cp == "C" else max(strike - spot, 0.0)
        delta = (1.0 if spot > strike else 0.0) if cp == "C" else (-1.0 if spot < strike else 0.0)
        return intrinsic, delta, 0.0
    v = sigma * math.sqrt(t)
    d1 = (math.log(spot / strike) + 0.5 * v * v) / v
    d2 = d1 - v
    if cp == "C":
        price = spot * _cdf(d1) - strike * _cdf(d2)
        delta = _cdf(d1)
    else:
        price = strike * _cdf(-d2) - spot * _cdf(-d1)
        delta = _cdf(d1) - 1.0
    gamma = _pdf(d1) / (spot * v)
    return price, delta, gamma


def implied_vol(price: float, spot: float, strike: float, t: float, cp: str) -> float | None:
    """Bisection inversion. None when the price carries no usable vol information."""
    intrinsic = max(spot - strike, 0.0) if cp == "C" else max(strike - spot, 0.0)
    if t <= 0 or price <= intrinsic + 1e-4:
        return None
    lo, hi = 0.005, 4.0
    if bs(spot, strike, t, hi, cp)[0] < price:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if bs(spot, strike, t, mid, cp)[0] < price:
            lo = mid
        else:
            hi = mid
    iv = 0.5 * (lo + hi)
    return iv if 0.015 < iv < 3.5 else None


# --------------------------------------------------------------------------------------
# One (underlying, session) of replay input
# --------------------------------------------------------------------------------------

@dataclass
class DayData:
    day: str                       # session being evaluated, YYYY-MM-DD
    underlying: str
    spot: float
    expiration: str                # YYYY-MM-DD, 1-3 DTE
    chain: dict[str, dict] = field(default_factory=dict)   # Alpaca-snapshot shaped
    oi: dict[str, int] = field(default_factory=dict)
    bars: list[dict] = field(default_factory=list)         # underlying daily bars up to `day`
    exp_spot: float | None = None  # underlying close on `expiration`, for the P&L stub


def _chain_entry(price: float, iv: float, delta: float, gamma: float) -> dict:
    """Shaped like an Alpaca option snapshot, so agent/ code consumes it unchanged.

    A real snapshot always carries a two-sided `latestQuote`; the execution liquidity gate
    (issue #22) requires one, so the synthetic chain models a tight ~2%-of-mid spread.
    """
    half = max(price * 0.01, 0.01)
    return {
        "impliedVolatility": iv,
        "greeks": {"delta": delta, "gamma": gamma, "theta": 0.0, "vega": 0.0, "rho": 0.0},
        "latestQuote": {"bp": max(price - half, 0.01), "ap": price + half},
        "latestTrade": {"p": price},
    }


def occ(underlying: str, exp: date, cp: str, strike: float) -> str:
    return f"{underlying}{exp:%y%m%d}{cp}{round(strike * 1000):08d}"


# --------------------------------------------------------------------------------------
# Synthetic tape — exercises the whole pipeline with no network
# --------------------------------------------------------------------------------------

def _weekdays_ending(n: int, end: date) -> list[date]:
    out: list[date] = []
    d = end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def _vol_path(rng: Any, n: int, level: float, spike: bool) -> np.ndarray:
    """Slow mean-reverting vol around `level`, optionally with one realistic spike."""
    z = rng.standard_normal(n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.93 * x[i - 1] + 0.09 * z[i]
    vol = level * np.exp(x)
    if spike and n > 40:
        start = int(n * 0.62)
        for k in range(start, min(start + 12, n)):
            age = k - start
            vol[k] *= 1.0 + 2.2 * math.exp(-0.35 * age)
    return vol


def gen_synthetic(
    symbols: list[str],
    n_days: int,
    seed: int = 7,
    vol_level: float = 0.09,
    iv_ratio: float = 1.12,
    gex_bias: float = 0.18,
    spike: bool = True,
) -> list[DayData]:
    """A plausible low-vol 2026 tape where IV is priced as a RATIO over forward realized vol.

    `iv_ratio` is the whole point of the exercise: the empirical volatility risk premium is
    multiplicative (IV/RV ~ 1.05-1.20 on index options), while the pre-audit gate was an
    absolute number of vol points. The synthetic surface encodes the multiplicative version,
    so the funnel can show what an absolute threshold does to it.
    """
    rng = np.random.default_rng(seed)
    warm = 60
    total = warm + n_days + 2
    dates = _weekdays_ending(total, date.today() - timedelta(days=1))
    out: list[DayData] = []

    for u in symbols:
        s0 = SYNTH_SPOT.get(u, 400.0)
        vol = _vol_path(rng, total, vol_level * SYNTH_VOL_SCALE.get(u, 1.0), spike)
        dvol = vol / math.sqrt(252.0)
        close = np.empty(total)
        bars: list[dict] = []
        prev = s0
        # The bar generator has to be UNBIASED for the estimators signal.py uses, otherwise
        # the funnel measures the generator instead of the gates. Splitting the daily
        # variance into an overnight gap (`_OVERNIGHT`) plus a simulated intraday path makes
        # close-to-close variance exactly dvol**2 (so ewma_rv is unbiased) and the
        # Yang-Zhang components sum back to the same dvol**2 (so yang_zhang_rv is too).
        for i in range(total):
            gap = rng.normal(0.0, math.sqrt(_OVERNIGHT) * dvol[i])
            o = prev * math.exp(gap)
            step = math.sqrt((1.0 - _OVERNIGHT) / _STEPS) * dvol[i]
            path = o * np.exp(np.cumsum(rng.normal(0.0, step, _STEPS)))
            c = float(path[-1])
            bars.append({"t": dates[i].isoformat(), "o": o, "c": c,
                         "h": max(o, float(path.max())), "l": min(o, float(path.min()))})
            close[i] = c
            prev = c

        for i in range(warm, warm + n_days):
            day, exp = dates[i], dates[i + 1]
            dte = (exp - day).days
            if not 1 <= dte <= 3:
                continue
            spot = float(close[i])
            t = year_frac(1)                     # `exp` is the next session, by construction
            atm = float(vol[i + 1]) * iv_ratio * math.exp(rng.normal(0.0, 0.05))
            sd = atm * math.sqrt(t)
            band = max(0.03 * spot, 5.0 * sd * spot)
            chain: dict[str, dict] = {}
            oi: dict[str, int] = {}
            for raw_k in np.arange(math.floor(spot - band), math.ceil(spot + band) + 1.0, 1.0):
                strike = float(raw_k)
                z = math.log(strike / spot) / max(sd, 1e-6)
                iv = max(atm * (1.0 - 0.06 * z + 0.02 * z * z), 0.02)
                base_oi = 20_000.0 * math.exp(-0.5 * (z / 1.2) ** 2)
                for cp in ("C", "P"):
                    price, delta, gamma = bs(spot, strike, t, iv, cp)
                    sym = occ(u, exp, cp, strike)
                    chain[sym] = _chain_entry(round(max(price, 0.01), 2), iv, delta, gamma)
                    tilt = (1.0 + gex_bias) if cp == "C" else (1.0 - gex_bias)
                    n_oi = int(base_oi * tilt * float(rng.uniform(0.75, 1.25)))
                    if n_oi > 0:
                        oi[sym] = n_oi
            out.append(DayData(
                day=day.isoformat(), underlying=u, spot=spot, expiration=exp.isoformat(),
                chain=chain, oi=oi, bars=bars[max(0, i - 54):i + 1],
                exp_spot=float(close[i + 1]),
            ))
    return out


# --------------------------------------------------------------------------------------
# Live tape — Alpaca historical bars, cached to disk
# --------------------------------------------------------------------------------------

def require_keys() -> None:
    missing = [k for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY") if not os.environ.get(k)]
    if not missing:
        return
    sys.stderr.write("\n".join([
        "",
        "ERROR: cannot run the live replay — missing credentials: " + ", ".join(missing),
        "",
        "Fix it in one of two ways:",
        f"  1) cp {ROOT / '.env.example'} {ROOT / '.env'}   and fill in the two keys",
        "     (testing account PA3TQHQKM5AD — never the competition keys)",
        "  2) export ALPACA_API_KEY=... ALPACA_SECRET_KEY=...",
        "",
        "No keys to hand? The whole funnel runs offline on a synthetic tape:",
        "     uv run python -m backtest.replay --synthetic",
        "",
    ]) + "\n")
    raise SystemExit(2)


def stock_bars(symbol: str, start: date, end: date) -> list[dict]:
    """Paginated daily bars over an explicit window.

    Deliberately NOT `md.daily_bars()`. That helper asks for ~2x the lookback in CALENDAR
    days but caps `limit` at lookback+5, so for any lookback beyond ~13 the API returns the
    OLDEST page and the window silently ends weeks before today. Harmless to work around
    here; a real bug in production, where `signal.fetch` calls it with 55 and the RV
    forecast is therefore computed on stale bars. Reported separately — not fixed here,
    `agent/` belongs to another lane.
    """
    bars: list[dict] = []
    token: str | None = None
    while True:
        page = md._get(
            f"/v2/stocks/{symbol}/bars", timeframe="1Day", feed="sip",
            start=start.isoformat(), end=end.isoformat(), limit=10_000, page_token=token,
        )
        bars.extend(page.get("bars") or [])
        token = page.get("next_page_token")
        if not token:
            return bars


def _load_cached(path: Path) -> DayData | None:
    if not path.exists():
        return None
    try:
        return DayData(**json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, TypeError):
        return None


def build_chain_from_bars(
    underlying: str, spot: float, day: date, exp: date, band: float, step: float = 1.0
) -> tuple[dict[str, dict], dict[str, int]]:
    """Rebuild a chain for `day` from historical option daily bars + BS inversion."""
    t = year_frac(1)                             # `exp` is the next session, by construction
    strikes = [
        float(k) for k in np.arange(
            math.floor(spot * (1 - band)), math.ceil(spot * (1 + band)) + step, step
        )
    ]
    symbols = [occ(underlying, exp, cp, k) for k in strikes for cp in ("C", "P")]

    raw: dict[str, list[dict]] = {}
    for i in range(0, len(symbols), 40):
        try:
            raw.update(md.option_daily_bars(
                symbols[i:i + 40], start=day.isoformat(), limit=1000) or {})
        except Exception as exc:                                     # noqa: BLE001
            sys.stderr.write(f"  ! option bars {underlying} {day} chunk {i}: {exc}\n")

    chain: dict[str, dict] = {}
    oi: dict[str, int] = {}
    for sym, series in raw.items():
        bar = next((b for b in series if str(b.get("t", ""))[:10] == day.isoformat()), None)
        if not bar:
            continue
        price = float(bar.get("c") or 0.0)
        _, _, cp, strike = md.parse_occ(sym)
        iv = implied_vol(price, spot, strike, t, cp)
        if iv is None:
            continue
        _, delta, gamma = bs(spot, strike, t, iv, cp)
        chain[sym] = _chain_entry(price, iv, delta, gamma)
        vol = int(bar.get("v") or 0)
        if vol > 0:
            oi[sym] = vol                                            # volume as the OI proxy
    return chain, oi


def fetch_days(
    symbols: list[str], n_days: int, cache_dir: Path, band: float = 0.03, use_cache: bool = True
) -> list[DayData]:
    require_keys()
    cache_dir.mkdir(parents=True, exist_ok=True)
    today = date.today()
    hist_start = today - timedelta(days=int((n_days + 70) * 1.6))
    out: list[DayData] = []

    for u in symbols:
        bars = stock_bars(u, hist_start, today)
        if len(bars) < 60:
            sys.stderr.write(f"  ! {u}: only {len(bars)} daily bars returned, skipping\n")
            continue
        days = [str(b["t"])[:10] for b in bars]
        for i in range(max(55, len(bars) - 1 - n_days), len(bars) - 1):
            day, exp = date.fromisoformat(days[i]), date.fromisoformat(days[i + 1])
            if not 1 <= (exp - day).days <= 3:
                continue
            path = cache_dir / f"{u}-{days[i]}.json"
            if use_cache:
                cached = _load_cached(path)
                if cached is not None:
                    out.append(cached)
                    continue
            spot = float(bars[i]["c"])
            chain, oi = build_chain_from_bars(u, spot, day, exp, band)
            dd = DayData(
                day=days[i], underlying=u, spot=spot, expiration=days[i + 1], chain=chain,
                oi=oi, bars=bars[max(0, i - 54):i + 1], exp_spot=float(bars[i + 1]["c"]),
            )
            path.write_text(json.dumps(asdict(dd)), encoding="utf-8")
            out.append(dd)
            print(f"  fetched {u} {days[i]} -> exp {days[i + 1]}  {len(chain)} contracts")
    return out


# --------------------------------------------------------------------------------------
# The funnel
# --------------------------------------------------------------------------------------

STAGES: list[tuple[str, str]] = [
    ("evaluated", "underlying-sessions evaluated"),
    ("chain_ok", "chain + history usable (>=8 contracts, >=25 bars)"),
    ("data_ok", "IV and RV_hat both measurable      [gate: data]"),
    ("vrp_ok", "VRP rich      IV/RV_hat >= ratio   [gate: vrp]"),
    ("gex_ok", "dealer gamma  gex_norm >= gex_min  [gate: gex]"),
    ("trend_ok", "tape not trending                  [gate: trend]"),
    ("sell_premium", "signal.sell_premium is True"),
    ("structure", "structure built (strikes found)"),
    ("credit_ok", "credit gate   credit/width >= min_credit_frac"),
    ("size_ok", "sizing gate   >= 1 contract"),
    ("delta_ok", "leg deltas available"),
    ("risk_ok", "risk.evaluate() == ok"),
    ("opened", "TRADES OPENED"),
]

# stand_down reason -> the stage it kills
_STAND_DOWN_STAGE = {"data": "data_ok", "vrp": "vrp_ok", "gex": "gex_ok", "trend": "trend_ok"}
_STAND_DOWN_ORDER = ["data_ok", "vrp_ok", "gex_ok", "trend_ok"]


@dataclass
class FunnelResult:
    label: str
    rule: str = ""
    counts: Counter = field(default_factory=Counter)
    risk_reasons: Counter = field(default_factory=Counter)
    structures: Counter = field(default_factory=Counter)
    trades: list[dict] = field(default_factory=list)
    pnl: float = 0.0
    cr_fracs: list[float] = field(default_factory=list)
    ratios: list[float] = field(default_factory=list)
    ivs: list[float] = field(default_factory=list)
    rvs: list[float] = field(default_factory=list)
    gex_norms: list[float] = field(default_factory=list)

    @property
    def n_trades(self) -> int:
        return self.counts["opened"]


def _payoff(pos: dict) -> float:
    """Held to expiry. Positive = we keep (part of) the credit."""
    s = pos["exp_spot"]
    if s is None:
        return 0.0
    st, credit = pos["strikes"], pos["credit"]
    loss = 0.0
    if "sp" in st:                                                   # iron condor
        loss += min(max(st["sp"] - s, 0.0), st["sp"] - st["lp"])
        loss += min(max(s - st["sc"], 0.0), st["lc"] - st["sc"])
    else:                                                            # vertical
        short, long_ = st["short"], st["long"]
        if long_ < short:
            loss = min(max(short - s, 0.0), short - long_)
        else:
            loss = min(max(s - short, 0.0), long_ - short)
    return (credit - loss) * 100.0 * pos["contracts"]


def run_funnel(
    days: list[DayData],
    params: Params,
    label: str = "base",
    vrp_abs: float | None = None,
) -> FunnelResult:
    """Pure. Replays the real engine session by session and counts survivors at every gate.

    `vrp_abs` reproduces the PRE-AUDIT absolute gate (`iv - rv_hat >= x`) through today's
    relative code path, by setting `vrp_ratio_min = 1 + x / rv_hat` for that session — an
    exact restatement. That is how the "legacy" rows in the sensitivity table are computed,
    and it is what answers the original question in issue #5.
    """
    rule = (f"IV-RV >= {vrp_abs:.3f} (legacy absolute)" if vrp_abs is not None
            else f"IV/RV >= {params.vrp_ratio_min:.2f}")
    rule += (f" | gex_norm >= {params.gex_min:.2f} | credit/width >= {params.min_credit_frac:.2f}"
             f" | delta {params.short_delta:.2f}"
             f" | width {params.width_spy:g}/{params.width_iwm:g}"
             f" | fade_trend {params.fade_trend}")
    res = FunnelResult(label=label, rule=rule)

    by_day: dict[str, list[DayData]] = defaultdict(list)
    for d in days:
        by_day[d.day].append(d)

    nav = peak = NAV0
    book: list[dict] = []

    for day_str in sorted(by_day):
        today = date.fromisoformat(day_str)
        day_pnl = 0.0
        still: list[dict] = []
        for pos in book:
            if date.fromisoformat(pos["expiration"]) <= today:
                pnl = _payoff(pos)
                nav += pnl
                day_pnl += pnl
                res.pnl += pnl
                pos["pnl"] = round(pnl, 2)
            else:
                still.append(pos)
        book = still
        peak = max(peak, nav)
        now = datetime.combine(today, time(10, 0), tzinfo=ET)

        for dd in sorted(by_day[day_str], key=lambda x: x.underlying):
            res.counts["evaluated"] += 1
            if len(dd.chain) < 8 or len(dd.bars) < 25:
                continue
            res.counts["chain_ok"] += 1

            p = params
            if vrp_abs is not None:
                rv = sg.rv_forecast(dd.bars)
                p = replace(params, vrp_ratio_min=(1.0 + vrp_abs / rv) if rv > 0 else 1e9)

            data = {"spot": dd.spot, "expiration": dd.expiration, "chain": dd.chain,
                    "oi": dd.oi, "bars": dd.bars}
            s = sg.build_signal(dd.underlying, data, p)

            if math.isfinite(s.atm_iv) and math.isfinite(s.rv_hat) and s.rv_hat > 0:
                res.ivs.append(s.atm_iv)
                res.rvs.append(s.rv_hat)
                res.ratios.append(s.atm_iv / s.rv_hat)
            res.gex_norms.append(s.gex_norm)

            # The four stand-down gates, in the order build_signal evaluates them.
            killed_at = _STAND_DOWN_STAGE.get(s.stand_down)
            for stage in _STAND_DOWN_ORDER:
                if stage == killed_at:
                    break
                res.counts[stage] += 1
            if killed_at:
                continue
            if not s.sell_premium:
                continue
            res.counts["sell_premium"] += 1

            pf = risk.PortfolioState(
                nav=nav, peak_nav=peak, open_risk=sum(b["max_loss"] for b in book),
                n_positions=len(book), net_delta=0.0, day_pnl=day_pnl,
            )
            if pf.n_positions >= p.max_positions:
                res.risk_reasons["max concurrent positions (desk.py pre-check)"] += 1
                continue

            sel = dk._pick(s, p)
            if not sel or not sel.get("width"):
                continue
            res.counts["structure"] += 1
            res.structures[s.structure] += 1

            cr_frac = sel["credit"] / sel["width"]
            res.cr_fracs.append(cr_frac)
            if cr_frac < p.min_credit_frac:
                continue
            res.counts["credit_ok"] += 1

            mult = risk.size_multiplier(pf, p)
            n = ex.size(sel["width"], sel["credit"], nav, p.risk_per_trade, mult)
            if n < 1:
                continue
            res.counts["size_ok"] += 1

            leg_delta = dk._legs_delta(sel["legs"], n, s.chain, s.spot)
            if leg_delta is None:
                res.risk_reasons["missing greeks"] += 1
                continue
            res.counts["delta_ok"] += 1

            proposed = risk.ProposedTrade(
                underlying=dd.underlying, structure=s.structure,
                max_loss=(sel["width"] - sel["credit"]) * 100.0 * n,
                net_delta=leg_delta / nav, is_0dte=s.expiration == day_str, is_satellite=False,
            )
            ok, why = risk.evaluate(proposed, pf, p, now)
            if not ok:
                res.risk_reasons[why] += 1
                continue
            res.counts["risk_ok"] += 1

            pos = {
                "day": day_str, "underlying": dd.underlying, "structure": s.structure,
                "expiration": dd.expiration, "strikes": sel["strikes"],
                "credit": sel["credit"], "width": sel["width"], "contracts": n,
                "max_loss": proposed.max_loss, "exp_spot": dd.exp_spot,
                "vrp_ratio": s.vrp_ratio, "cr_frac": round(cr_frac, 3), "pnl": None,
            }
            book.append(pos)
            res.trades.append(pos)
            res.counts["opened"] += 1

    for pos in book:                                                 # settle the open tail
        pnl = _payoff(pos)
        res.pnl += pnl
        pos["pnl"] = round(pnl, 2)
    return res


# --------------------------------------------------------------------------------------
# Parameter sensitivity — network-free, reuses the cached/generated sessions
# --------------------------------------------------------------------------------------

def default_grid() -> list[tuple[str, dict]]:
    """(label, overrides). `vrp_abs` selects the legacy absolute VRP gate."""
    legacy = {"vrp_abs": 0.03, "gex_min": 0.0, "fade_trend": True,
              "min_credit_frac": 0.33, "width_spy": 4.0, "width_iwm": 2.0}
    return [
        ("CURRENT config.py", {}),
        ("LEGACY pre-audit (issue #5 question)", legacy),
        ("LEGACY but credit 0.33 -> 0.20", {**legacy, "min_credit_frac": 0.20}),
        ("LEGACY but width 4/2 -> 2/1", {**legacy, "width_spy": 2.0, "width_iwm": 1.0}),
        ("LEGACY but vrp 0.03 -> 0.00", {**legacy, "vrp_abs": 0.0}),
        ("LEGACY, credit 0.20 AND width 2/1",
         {**legacy, "min_credit_frac": 0.20, "width_spy": 2.0, "width_iwm": 1.0}),
        ("vrp_ratio_min 1.15 -> 1.30", {"vrp_ratio_min": 1.30}),
        ("vrp_ratio_min 1.15 -> 1.05", {"vrp_ratio_min": 1.05}),
        ("vrp_ratio_min 1.15 -> 1.00 (off)", {"vrp_ratio_min": 1.0}),
        ("gex_min 0.10 -> 0.30", {"gex_min": 0.30}),
        ("gex_min 0.10 -> 0.00 (bare sign)", {"gex_min": 0.0}),
        ("min_credit_frac 0.20 -> 0.30", {"min_credit_frac": 0.30}),
        ("min_credit_frac 0.20 -> 0.10", {"min_credit_frac": 0.10}),
        ("short_delta 0.18 -> 0.25", {"short_delta": 0.25}),
        ("width 2/1 -> 4/2 (wider wings)", {"width_spy": 4.0, "width_iwm": 2.0}),
        ("fade_trend True (legacy #12)", {"fade_trend": True}),
        ("ALL GATES OFF (upper bound)",
         {"vrp_ratio_min": 0.0, "gex_min": -1.0, "min_credit_frac": 0.0}),
    ]


def sensitivity(
    days: list[DayData], base: Params, grid: list[tuple[str, dict]] | None = None
) -> list[FunnelResult]:
    """Given a set of thresholds, say how many signals — and how many trades — survive."""
    rows: list[FunnelResult] = []
    for label, overrides in (grid if grid is not None else default_grid()):
        o = dict(overrides)
        vrp_abs = o.pop("vrp_abs", None)
        rows.append(run_funnel(days, replace(base, **o), label=label, vrp_abs=vrp_abs))
    return rows


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

def _pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:6.1f}%" if d else "     -"


def print_funnel(res: FunnelResult, params: Params) -> None:
    total = res.counts["evaluated"]
    counts = [res.counts[k] for k, _ in STAGES]
    killed = [0] + [max(counts[i - 1] - counts[i], 0) for i in range(1, len(counts))]
    worst = max(range(len(killed)), key=lambda i: killed[i]) if any(killed) else -1

    print()
    print("=" * 84)
    print(f"FUNNEL — {res.label}")
    print(f"  {res.rule}")
    print("=" * 84)
    print(f"{'#':>2}  {'STAGE':<52}{'PASS':>7}{'KILLED':>8}{'OF ALL':>8}")
    print("-" * 84)
    for i, (_, name) in enumerate(STAGES):
        mark = "   <<< DIES HERE" if i == worst else ""
        print(f"{i + 1:>2}  {name:<52}{counts[i]:>7}{killed[i]:>8}"
              f"{_pct(counts[i], total):>8}{mark}")
    print("-" * 84)

    if res.ratios:
        iv, rv, r = np.array(res.ivs), np.array(res.rvs), np.array(res.ratios)
        print(f"    ATM IV        median {np.median(iv):7.2%}  p90 {np.percentile(iv, 90):7.2%}")
        print(f"    RV_hat        median {np.median(rv):7.2%}  p90 {np.percentile(rv, 90):7.2%}")
        print(f"    IV/RV_hat     median {np.median(r):7.2f}  p90 {np.percentile(r, 90):7.2f}"
              f"  max {r.max():7.2f}   (threshold {params.vrp_ratio_min:.2f})")
        print(f"    IV-RV_hat     median {np.median(iv - rv):+7.4f}  "
              f"p90 {np.percentile(iv - rv, 90):+7.4f}  max {(iv - rv).max():+7.4f}"
              "   (legacy threshold +0.0300)")
    if res.gex_norms:
        g = np.array(res.gex_norms)
        print(f"    gex_norm      median {np.median(g):+7.3f}  p90 {np.percentile(g, 90):+7.3f}"
              f"   (threshold {params.gex_min:+.2f})")
    if res.cr_fracs:
        c = np.array(res.cr_fracs)
        print(f"    credit/width  median {np.median(c):7.3f}  p90 {np.percentile(c, 90):7.3f}"
              f"  max {c.max():7.3f}   (threshold {params.min_credit_frac:.3f})")
    if res.structures:
        print("    structures  : " + ", ".join(f"{k}={v}" for k, v in res.structures.items()))
    if res.risk_reasons:
        print("    risk vetoes : " + ", ".join(f"{k} x{v}" for k, v in res.risk_reasons.items()))
    print(f"    approx P&L held-to-expiry: ${res.pnl:,.0f} over {res.n_trades} trades / "
          f"{total} underlying-sessions")
    print()


def print_sensitivity(rows: list[FunnelResult]) -> None:
    print("=" * 100)
    print("PARAMETER SENSITIVITY — survivors at each gate under other thresholds")
    print("=" * 100)
    print(f"{'VARIANT':<40}{'VRP':>6}{'GEX':>6}{'TREND':>7}{'STRUCT':>8}{'CREDIT':>8}"
          f"{'SIZE':>6}{'RISK':>6}{'TRADES':>8}{'P&L $':>9}")
    print("-" * 100)
    for r in rows:
        c = r.counts
        print(f"{r.label:<40}{c['vrp_ok']:>6}{c['gex_ok']:>6}{c['trend_ok']:>7}"
              f"{c['structure']:>8}{c['credit_ok']:>8}{c['size_ok']:>6}{c['risk_ok']:>6}"
              f"{c['opened']:>8}{r.pnl:>9,.0f}")
    print("-" * 100)
    print("Columns are survivors AT that gate (cumulative), not deaths. TRADES answers issue #5.")
    print()


def print_trades(res: FunnelResult, limit: int = 12) -> None:
    if not res.trades:
        return
    print(f"{'DAY':<12}{'SYM':<5}{'STRUCTURE':<20}{'CREDIT':>8}{'W':>5}{'N':>4}"
          f"{'CR/W':>7}{'IV/RV':>7}{'PNL $':>9}")
    print("-" * 78)
    for t in res.trades[:limit]:
        print(f"{t['day']:<12}{t['underlying']:<5}{t['structure']:<20}{t['credit']:>8.2f}"
              f"{t['width']:>5.0f}{t['contracts']:>4}{t['cr_frac']:>7.3f}"
              f"{t['vrp_ratio']:>7.2f}{(t['pnl'] or 0.0):>9,.0f}")
    if len(res.trades) > limit:
        print(f"... and {len(res.trades) - limit} more")
    print()


# --------------------------------------------------------------------------------------
# Self-test — proves the funnel is wired, no network
# --------------------------------------------------------------------------------------

def selftest() -> int:
    fails: list[str] = []

    price, delta, gamma = bs(100.0, 100.0, 30 / 365.0, 0.20, "C")
    if not (2.0 < price < 3.0 and 0.45 < delta < 0.56 and gamma > 0):
        fails.append(f"bs() ATM call implausible: price={price} delta={delta} gamma={gamma}")
    back = implied_vol(price, 100.0, 100.0, 30 / 365.0, "C")
    if back is None or abs(back - 0.20) > 1e-3:
        fails.append(f"implied_vol() round-trip failed: {back}")

    days = gen_synthetic(["SPY"], 40, seed=1)
    if not days:
        fails.append("gen_synthetic produced no sessions")
        for f in fails:
            print(f"FAIL  {f}")
        return 1

    # The generator must be unbiased for the estimators signal.py uses, or the funnel is
    # measuring the tape generator rather than the gates.
    flat = gen_synthetic(["SPY"], 60, seed=3, vol_level=0.10, spike=False)
    rv = float(np.median([sg.rv_forecast(d.bars) for d in flat]))
    if not 0.085 <= rv <= 0.118:
        fails.append(f"rv_forecast recovers {rv:.3f} from a 0.100 tape — generator is biased")

    base = Params()
    strict = run_funnel(days, base, label="strict")
    if strict.counts["evaluated"] != len(days):
        fails.append("funnel did not evaluate every session")
    if strict.counts["chain_ok"] < len(days):
        fails.append("chain reconstruction unusable on synthetic data")
    if strict.counts["data_ok"] < len(days):
        fails.append("IV/RV not measurable on a clean synthetic surface")

    loose = run_funnel(days, replace(base, vrp_ratio_min=0.0, gex_min=-1.0, min_credit_frac=0.0),
                       label="loose")
    if loose.n_trades < 1:
        fails.append("zero trades even with every gate disabled — the pipeline is dead code")
    if loose.n_trades < strict.n_trades:
        fails.append("loosening every gate reduced trades — monotonicity broken")

    tight = run_funnel(days, replace(base, vrp_ratio_min=99.0), label="tight")
    if tight.n_trades != 0 or tight.counts["vrp_ok"] != 0:
        fails.append("an impossible VRP threshold still let candidates through")

    rows = sensitivity(days, base)
    if len(rows) != len(default_grid()):
        fails.append("sensitivity() dropped variants")
    if rows[-1].n_trades < rows[0].n_trades:
        fails.append("sensitivity grid is not monotone in the loosening direction")

    for f in fails:
        print(f"FAIL  {f}")
    if not fails:
        print(f"PASS  bs/iv round-trip · chain rebuild · gate monotonicity "
              f"(strict {strict.n_trades} <= loose {loose.n_trades} trades) · "
              f"sensitivity grid ({len(rows)} variants)")
    return 1 if fails else 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def _args(argv: list[str] | None = None) -> Any:
    ap = argparse.ArgumentParser(
        prog="backtest.replay",
        description="Backtest-lite: does IV Desk ever open a position? (issue #5)",
    )
    ap.add_argument("--synthetic", action="store_true",
                    help="generate a plausible tape instead of calling Alpaca (no keys, no net)")
    ap.add_argument("--selftest", action="store_true", help="run pipeline assertions and exit")
    ap.add_argument("--days", type=int, default=60, help="sessions to replay (default 60)")
    ap.add_argument("--symbols", default="SPY,QQQ,IWM")
    ap.add_argument("--seed", type=int, default=7, help="synthetic RNG seed")
    ap.add_argument("--vol-level", type=float, default=0.09,
                    help="synthetic baseline annualised vol (the 2026 tape is 6-10%%)")
    ap.add_argument("--iv-ratio", type=float, default=1.12,
                    help="synthetic IV / forward-RV ratio — the true VRP is multiplicative")
    ap.add_argument("--gex-bias", type=float, default=0.18,
                    help="synthetic call-vs-put OI tilt; >0 makes dealer gamma positive")
    ap.add_argument("--no-spike", action="store_true", help="synthetic tape without a vol spike")
    ap.add_argument("--strike-band", type=float, default=0.03,
                    help="live mode: strike grid as a fraction of spot (default +/-3%%)")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--no-cache", action="store_true", help="live mode: ignore the disk cache")
    ap.add_argument("--no-sensitivity", action="store_true")
    ap.add_argument("--json", type=Path, default=None, help="write the funnel counts to a file")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = _args(argv)
    if a.selftest:
        return selftest()

    symbols = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    base = Params.load()

    if a.synthetic:
        print(f"synthetic tape: {a.days} sessions x {len(symbols)} underlyings, seed {a.seed}, "
              f"vol {a.vol_level:.0%}, IV/RV {a.iv_ratio:.2f}, spike {not a.no_spike}")
        days = gen_synthetic(symbols, a.days, seed=a.seed, vol_level=a.vol_level,
                             iv_ratio=a.iv_ratio, gex_bias=a.gex_bias, spike=not a.no_spike)
        print("  CAVEAT: on a synthetic tape `gex_norm` is ~ --gex-bias by construction, so "
              "the GEX row\n  is circular and says nothing about the real market. The VRP, "
              "credit and sizing rows do not\n  depend on that assumption. Re-run without "
              "--synthetic before calibrating gex_min.")
    else:
        print(f"live replay: {a.days} sessions x {len(symbols)} underlyings, cache {a.cache_dir}")
        days = fetch_days(symbols, a.days, a.cache_dir, band=a.strike_band,
                          use_cache=not a.no_cache)

    if not days:
        print("No sessions to replay.")
        return 1

    res = run_funnel(days, base, label="CURRENT config.py")
    print_funnel(res, base)
    print_trades(res)

    legacy_params = replace(base, gex_min=0.0, fade_trend=True, min_credit_frac=0.33,
                            width_spy=4.0, width_iwm=2.0)
    legacy = run_funnel(days, legacy_params, label="LEGACY pre-audit params (issue #5)",
                        vrp_abs=0.03)
    print_funnel(legacy, legacy_params)

    rows: list[FunnelResult] = []
    if not a.no_sensitivity:
        rows = sensitivity(days, base)
        print_sensitivity(rows)

    print("=" * 84)
    print("VERDICT")
    print(f"  pre-audit params : {legacy.n_trades} trades over {legacy.counts['evaluated']} "
          "underlying-sessions"
          + ("   <-- the strategy NEVER fires" if legacy.n_trades == 0 else ""))
    print(f"  current params   : {res.n_trades} trades, approx P&L ${res.pnl:,.0f}"
          + ("   <-- STILL never fires" if res.n_trades == 0 else ""))
    print("=" * 84)

    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({
            "sessions": len(days),
            "current": {k: res.counts[k] for k, _ in STAGES},
            "current_pnl": round(res.pnl, 2),
            "current_trades": res.trades,
            "legacy": {k: legacy.counts[k] for k, _ in STAGES},
            "sensitivity": [
                {"variant": r.label, **{k: r.counts[k] for k, _ in STAGES},
                 "pnl": round(r.pnl, 2)} for r in rows
            ],
        }, indent=2), encoding="utf-8")
        print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
