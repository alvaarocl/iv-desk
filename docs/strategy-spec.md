# Strategy Spec

## Universe

`SPY`, `QQQ`, `IWM` — deepest options liquidity, tightest spreads, daily expirations, index-like (no single-name earnings gap risk).

## Instruments

Defined-risk short-premium structures, 0–4 DTE:

| Regime (from signal) | Structure |
|---|---|
| Range-bound, positive GEX, rich VRP | **Iron condor** (or 2× vertical credit spreads if `mleg` 4-leg unsupported) |
| Mild directional lean, rich VRP | **Put credit spread** (bullish) / **Call credit spread** (bearish) |
| Trending, negative GEX | **Stand down**, or satellite **debit spread** in trend direction |
| VRP not rich | **No trade** |

All expirations chosen to **resolve on or before Fri 4 Sep** so P&L is realized, not open marks.

## Signal (`agent/signal.py`)

Runs once per loop; heavy parts (GEX) cached 2–4h.

### 1. Realized-vol forecast
Yang-Zhang estimator over 20 trading days, blended with EWMA (λ=0.94). Annualized. This is `RV_hat`.

### 2. Volatility risk premium
`VRP = ATM_IV - RV_hat` where `ATM_IV` is the near-expiry at-the-money implied vol from the Alpaca option snapshot.
- Sell premium only if `VRP >= vrp_min` (start `vrp_min = 0.03`, i.e. 3 vol points).
- Scale conviction with `VRP` magnitude.

### 3. Dealer gamma exposure (GEX)
For strikes within ±5% of spot, using open interest `OI_k` and per-contract gamma `γ_k`:
`GEX = Σ_k [ γ_k · OI_k · 100 · S² · 0.01 · sign_k ]`  (calls +, puts −; standard SpotGamma-style convention)
- `GEX > 0` (dealers long gamma) → mean-reverting → condor OK.
- `GEX < 0` → trending → no premium selling; directional only.
- Cache per underlying; refresh at open, midday, and 2h before close.

### 4. Skew
`skew = IV(25Δ put) - IV(25Δ call)`. High put skew → favor put credit spreads further OTM / richer call side of condor.

### 5. Regime classifier
Combine: price vs 20/50 EMA, ADX(14), VIX level + 5-day change, GEX sign. Output ∈ {`trending_up`, `trending_down`, `range`, `chop`}.

### Output
```json
{
  "underlying": "SPY",
  "sell_premium": true,
  "structure": "iron_condor",
  "bias": "neutral",
  "conviction": 0.62,
  "regime": "range",
  "vrp": 0.041,
  "gex_sign": 1,
  "notes": "IV 14.2 vs RV_hat 10.1; dealers long gamma; put skew mild"
}
```

## Strike / structure selection

- Short strikes at **~15–20Δ** (≈ 80–85% POP per side).
- Width: SPY/QQQ $3–5, IWM $2–3.
- **Credit ≥ 33% of width** (max R:R ≈ 2:1) or skip.
- Liquidity gate: contract `OI > 500`, quoted spread `< 10%` of mid, both legs.

## Risk gates (`agent/risk.py`) — deterministic, no discretion

| Gate | Rule |
|---|---|
| Per-trade risk | Max loss ≤ **1–2% of NAV** (0.5% during Day 3 ramp) |
| Portfolio risk | Σ(max loss of open positions) ≤ **10% of NAV** |
| Concurrent positions | ≤ **6** (≤ 3 during ramp) |
| Portfolio delta | Net |Δ| ≤ **0.30 × (NAV / 100k)** normalized units |
| Daily circuit breaker | Day P&L (realized + unrealized) ≤ **−3% NAV** → close all, no new trades until next session |
| Drawdown gate | DD from peak > 8% → halve sizing; > 12% → no new positions |
| Event blackout | No new positions within 2h of scheduled high-impact macro (NFP 4 Sep, ISM, JOLTS, Fed speakers). Static calendar in `agent/calendar.py` |
| Time-of-day | No new 0DTE opens after **14:00 ET** (gamma risk); manage only |
| Satellite sleeve | Directional debit spreads capped at **15% of total risk budget** |
| Assignment | Close any ITM short leg by **15:45 ET** on expiration day |

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

`vrp_min`, short-strike delta, width, profit-take %, stop multiple, per-trade risk %, GEX threshold. Reflection may move each by ≤ 20% per night, logged with rationale.
