# Strategy Spec

## Universe

`SPY`, `QQQ`, `IWM` — deepest options liquidity, tightest spreads, daily expirations, index-like (no single-name earnings gap risk).

## Instruments

Defined-risk short-premium structures. **Prefer 1–3 DTE** (indicative feed is ~2s fresh but not
full OPRA; 0DTE only with wider stop buffers). Iron condors go as a **single 4-leg `mleg` order** —
confirmed working on this paper account (see `probes/RESULTS.md`).

| Regime (from signal) | Structure |
|---|---|
| Range-bound, dealer gamma long *with magnitude*, rich VRP | **Iron condor** (4-leg `mleg`) |
| Chop with long gamma, rich VRP | **Iron condor** — no directional lean to express |
| Trending (ADX > 22), rich VRP | **Stand down** — see *Trending tape* below |
| Dealer gamma short, or inside the GEX dead zone | **Stand down** |
| VRP not rich | **No trade** |

There is no directional debit-spread sleeve. It was documented but never implemented
(`sell_premium` was hard-coded `False` on that branch, so the loop skipped it and the strike
selector had no case for it), and `satellite_frac` was never read. Removed in issue #14 rather
than left as a promise the code does not keep. `CONCEPT.md` and `README.md` still describe it —
they need the same edit.

All expirations chosen to **resolve on or before Fri 4 Sep** so P&L is realized, not open marks.

## Signal (`agent/signal.py`)

Runs once per loop; heavy parts (GEX) cached 2–4h.

### 1. Realized-vol forecast
Yang-Zhang estimator over 20 trading days, blended with EWMA (λ=0.94). Annualized. This is `RV_hat`.

### 2. Volatility risk premium — **relative**, not absolute (issue #6)

`ATM_IV` is the near-expiry at-the-money implied vol from the Alpaca option snapshot.

- **Gate:** sell premium only if `ATM_IV / RV_hat >= vrp_ratio_min` (start `vrp_ratio_min = 1.15`).
- `VRP = ATM_IV - RV_hat` is still computed and written to the journal, but it **does not decide
  anything**. It is there for the write-up and for post-hoc analysis.

Why the change. The old gate was `VRP >= 0.03` — three *absolute* vol points, a number calibrated
for a VIX-20 world. With ATM IV at 6–10%, as it was the week of the competition, it demanded that
implied vol sit ~40% above realized, so it never fired. A ratio is scale-free: 1.15 means the same
thing at 6% IV and at 25% IV, which is the property we need when the whole window is four sessions
in an unknown regime.

**Known limitation, accepted deliberately.** `RV_hat` is a 20-session annualized number and
`ATM_IV` is 1–3 DTE, so the two are not the same horizon and the ratio carries a systematic bias.
We do not rescale, because the bias is roughly multiplicative and stable and is therefore absorbed
by calibrating `vrp_ratio_min` on the backtest (issue #5) — as opposed to a term-structure model we
have no way to validate in this window.

`yang_zhang_rv` also had an off-by-one: the range terms (`log_ho/log_lo/log_co`, length N) were
sliced against the gap terms (length N−1), so they were one day apart. Fixed, and the middle term
is now the open-to-close variance the Yang-Zhang estimator actually calls for, rather than
close-to-close, which double-counted the overnight gap and inflated `RV_hat`.

### 3. Dealer gamma exposure (GEX) — normalized, with a dead zone (issue #10)

For strikes within ±5% of spot (`gex_band`), using open interest `OI_k` and per-contract gamma `γ_k`:

`GEX = Σ_k [ γ_k · OI_k · 100 · S² · 0.01 · sign_k ]`  (calls +, puts −; SpotGamma-style convention)

`GEX` alone is not comparable across anything, so the gate reads a normalized version:

`GEX_norm = GEX / Σ_k | γ_k · OI_k · 100 · S² · 0.01 |`  → the **net/gross gamma imbalance**, in [−1, 1].

**Why this normalization.** The raw dollar figure scales three ways at once: with `S²`, with the
open-interest level, and with the vol regime (gamma itself moves with IV and DTE). A fixed dollar
threshold therefore means something different for SPY than for IWM, and something different in a
quiet September than in a busy March. Dividing by the *gross* gamma notional of the same strikes
cancels all three and leaves a pure imbalance ratio: +1 = all dealer gamma in the band is long,
−1 = all short, 0 = calls and puts cancel. That is exactly what the regime gate is asking about
("are dealers net long gamma here, and by enough to matter?"), it is one threshold for the whole
universe, and it degrades gracefully when the open interest is stale — Alpaca only publishes OI at
**T-2**. *Alternative considered and rejected:* dividing by `S²` alone, which still scales with OI
and so would need a different threshold per underlying.

**Dead zone.** `gex_state = +1` if `GEX_norm >= gex_min`, `−1` if `GEX_norm <= −gex_min`, else `0`.

- `gex_state = +1` → dealers long gamma → suppressed realized vol → condor OK.
- `gex_state = −1` → dealers short gamma → trending tape → **stand down** (no directional sleeve).
- `gex_state = 0` → **dead zone** → `regime = "chop"`, no trade.

The dead zone is the point of the change. On a T-2 datapoint, `+0.01` and `−0.01` are the same
reading with different noise; a bare sign test made the desk alternate between "sell condors" and
"stand down" every 15 minutes. `gex_min` starts at **0.10** — provisional, to be set from the
distribution of `GEX_norm` that the backtest (#5) produces.

- Cache per underlying; refresh at open, midday, and 2h before close. *(Still to do — the loop
  currently recomputes it every 15 min.)*

### 4. Skew
`skew = IV(25Δ put) - IV(25Δ call)`. High put skew → favor put credit spreads further OTM / richer call side of condor.

### 5. Regime classifier
Combine: price vs 20/50 EMA, ADX(14), and `gex_state`. Output ∈ {`trending_up`, `trending_down`,
`range`, `chop`}. A `gex_state` of 0 short-circuits to `chop` before anything else is evaluated.

`ADX(14)` is now Wilder's ADX — the DX series smoothed with a 14-period RMA. The previous
implementation collapsed ±DI to scalars and returned a single **DX**, which is a far noisier and
systematically larger number, so the `> 22` threshold in this document did not mean what it said
(issue #12).

### 5b. Trending tape — decision on "fade the trend" (issue #12)

**The desk does not sell premium into a trend.** When `regime` is `trending_up` or `trending_down`,
`structure = "none"` and `sell_premium = False`.

The code used to do the opposite, deliberately: `trending_up` mapped to a `bearish` bias, which
mapped to a **call credit spread** — i.e. it sold calls above the market precisely when the tape was
running up. Two reasons that had to go:

1. Selling premium against the direction of the move is the classic way to lose money in short
   options, and the only filter on it was a noisy GEX *sign* (see #10). The `bias` branches were
   moreover reachable **only** when `regime != "range"` — that is, only in a trend. So the riskiest
   configuration was also the only one those branches ever ran in.
2. Four sessions is not enough samples to survive one directional break. The VRP edge pays a little,
   often; a faded trend loses a lot, rarely. Over four days the variance dominates, and the whole
   positioning of this project is *a desk that knows when not to trade*.

It is behind `fade_trend: bool = False` in `Params`. Setting it to `True` restores the old
behaviour exactly (inverted bias → credit spread on the side the market is running into), so if the
backtest ever justifies the fade, the reversal is one flag and no code change. `bias` itself now
reports the **honest** read of the tape (`trending_up` → `bullish`) unless `fade_trend` is on.

### Output
```json
{
  "underlying": "SPY",
  "sell_premium": true,
  "structure": "iron_condor",
  "bias": "neutral",
  "regime": "range",
  "vrp": 0.041,
  "vrp_ratio": 1.41,
  "atm_iv": 0.142,
  "rv_hat": 0.101,
  "gex": 4.1e9,
  "gex_sign": 1,
  "gex_norm": 0.23,
  "gex_state": 1,
  "skew": 0.012,
  "stand_down": "",
  "notes": "IV 14.2% vs RV_hat 10.1% (ratio 1.41 vs 1.15); GEX_norm +0.230 (|min| 0.10, state +1); regime range; skew +1.2%; iron_condor"
}
```

`stand_down` is `""` when the desk is trading and otherwise names the gate that blocked it:
`vrp` | `gex` | `trend` | `data`. It exists so `data/journal.jsonl` records the desk **deciding**
not to trade, with a reason, rather than simply being silent — a silent log proves nothing.

`conviction` was removed (issue #14): it was computed on every loop and read by nothing. Reinstate
it only together with the sizing multiplier it was supposed to feed.

## Strike / structure selection

- Short strikes at **~18Δ** (`short_delta = 0.18`, ≈ 82% POP per side).
- Width: **SPY/QQQ $2, IWM $1** (`width_spy = 2.0`, `width_iwm = 1.0`).
- **Credit ≥ 20% of width** (`min_credit_frac = 0.20`) or skip.
- Liquidity gate: contract `OI > 500`, quoted spread `< 10%` of mid, both legs.

**Why the widths came down (issue #7).** The old `0.33 × 4.0` asked for $1.33 of credit on a
4-point, 18Δ condor. That was never a volatility problem, it was geometry: for a vertical,
credit/width ≈ the mean |delta| between the short and the long strike, and for a condor the loop
charges the max loss of **one** side only, so `credit/width ≈ 2 × mean|Δ|`. Four-point wings on SPY
put the long leg near 5Δ and collect roughly 0.20 of width; two-point wings keep it near 10Δ and
land nearer 0.25–0.30. The ratio therefore *rises* as the width narrows — which is why the fix is
narrower wings, not a lower vol assumption. SPY and QQQ quote $1 strikes near the money, so $2 wings
are two strikes wide and always constructible.

**These numbers are provisional.** `short_delta`, the widths and `min_credit_frac` move together —
they change max loss per contract, hence the sizing, hence the R:R — so the definitive set comes
from the backtest in issue #5, not from tuning one of them in isolation. If `cr_frac` still falls
short there, the next lever is `short_delta` (0.18 → 0.22), not the width. Note the trade-off being
made: at 0.20 of width the max R:R is ~4:1 rather than the ~2:1 this document used to claim, and
whether the take-profit-at-50% / stop-at-2× management makes that pay is exactly the question the
backtest has to answer.

## Risk gates (`agent/risk.py`) — deterministic, no discretion

| Gate | Rule |
|---|---|
| Per-trade risk | Max loss ≤ **1–2% of NAV** (0.5% during Day 3 ramp) |
| Portfolio risk | Σ(max loss of open positions) ≤ **10% of NAV** |
| Concurrent positions | ≤ **6** (≤ 3 during ramp) |
| Portfolio delta | Net |Δ| ≤ **0.30 × (NAV / 100k)** normalized units |
| Daily circuit breaker | Day P&L (realized + unrealized) ≤ **−3% NAV** → close all, no new trades until next session |
| Drawdown gate | DD from peak > 8% → halve sizing; > 12% → no new positions |
| Event blackout | **Asymmetric**: no new positions from **2h before** to **45min after** scheduled high-impact macro. Static calendar in `agent/calendar.py`. See §Blackout below |
| Time-of-day | No new 0DTE opens after **14:00 ET** (gamma risk); manage only |
| Assignment | Close the structure by **15:45 ET** on expiration day. Early assignment is **detected, not prevented** — see §Assignment below |

### Blackout — asymmetric on purpose (issue #33)

**2h before an event, 45 min after.** Not symmetric, and the asymmetry is the whole point.

The risk this gate exists for lives **before** the release: implied vol is bid, the move is
unknown, and selling a condor into an unresolved print is the wrong side of that trade. So the
pre-window stays wide.

**After** the print the opposite is true. The number is out, uncertainty collapses, and the IV
crush is exactly what a premium seller wants. Sitting on our hands there means skipping the best
entry of the day.

The concrete cost of getting this wrong: a symmetric ±2h blocked **09:30–12:00 ET on 1 and 3 Sep**
(ISM at 10:00) — the open of **two of the four scored sessions** — under a posture that explicitly
chose frequency over size (issue #16). Asymmetry cuts that to 09:30–10:45 and recovers 75 minutes
per session without taking on the risk the gate was built to avoid.

Covered by `tests/test_calendar_blackout.py`. **The event dates themselves are still unverified**
(issue #17).

### Assignment — accepted, not mitigated (issue #25)

SPY/QQQ/IWM options are American-style, so a short ITM leg can be assigned at any time, not just
at expiration. We **accept** this risk for the competition window rather than engineer around it:

- The classic trigger is the dividend, and **SPY's ex-dividend date falls outside the window**
  (~18 Sep).
- Our structures are 1–3 DTE and defined-risk, so the exposure window is short.

What we do instead is **detect it and stop**: `execution.has_unexpected_equity()` spots any equity
position that a defined-risk options book should never hold, and `desk.run_once` puts the desk into
exits-only before computing any risk figure. If we are assigned, every NAV and delta number the
desk would otherwise compute is wrong — so the correct response is to stop, not to adapt.

## Trade management (`agent/execution.py`) — no LLM

- **Take profit:** close at **50%** of max credit.
- **Stop:** close at **2× credit received** in debit, or if short strike breached intraday.
- **Time stop:** close at 15:45 ET on expiration day regardless.
- Entry orders: limit at mid, reprice toward NBBO every 30s, max 3 steps, then cancel and retry next loop.

## Debate (`agent/desk.py`) — LLM, only on open decisions

1. Quant ensemble (Featherless, 3 models) proposes structure + strikes from signal output; majority vote or abstain.
2. Bull and Bear each argue the underlying's direction for the trade horizon; must cite the signal fields.
3. Risk Officer (deterministic) returns allowed size + any hard vetoes.
4. Desk Head picks final structure, size (≤ Risk Officer cap), and which underlying, writes the trade thesis + a falsifiable prediction ("SPY closes in [a,b] on [date] because ...").
5. Everything appended to `data/journal.jsonl`; prediction graded on close.

## Parameters (tunable by nightly reflection)

`vrp_ratio_min`, `gex_min`, `short_delta`, `width_spy` / `width_iwm`, `min_credit_frac`,
`take_profit_frac`, `stop_multiple`, `risk_per_trade`. Reflection may move each by ≤ 20% per night,
logged with rationale.

`fade_trend` is **not** in that set: it is a risk-posture decision (§5b), not a knob, and it only
changes by a human editing `config.py`.

Current defaults in `agent/config.py` are first guesses chosen to be *reachable*, not calibrated
values. The backtest in issue #5 owns the final numbers.
