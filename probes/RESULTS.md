# Probe results — Day 0 (28 Aug 2026, run live during market hours via REST)

Account `PA3TQHQKM5AD` (internal id `3e7babe6-a533-4c5f-a89f-2c4fe6c19791`).
API: `https://paper-api.alpaca.markets/v2` · Data: `https://data.alpaca.markets`.

## 0. CLI install
Not yet done (no Go/Homebrew on the Windows box). Grab the Windows binary from
github.com/alpacahq/cli/releases → `alpaca.exe` on PATH. **Not blocking** — all probes below run via REST
and the agent can shell the CLI or hit REST directly. Decision pending: CLI vs raw REST for the prod loop
(REST via `alpaca-py` is looking simpler and is what these probes proved out).

## 1. Account / auth ✅
- `options_trading_level: 3`, `options_approved_level: 3` — spreads + condors enabled.
- cash $100,000 · portfolio_value $100,000 · `buying_power` $400,000 (4×) · `options_buying_power` $100,000.
- status ACTIVE, nothing blocked. Created 2026-08-28T14:51Z.

## 2. Options market data ✅ (with one caveat)
- **Chain snapshot** `GET /v1beta1/options/snapshots/{underlying}?feed=indicative` returns per contract:
  `greeks{delta,gamma,theta,vega,rho}`, `impliedVolatility`, `latestQuote` (bid/ask/size), `latestTrade`,
  `minuteBar`, `dailyBar`, `prevDailyBar`. **Greeks + IV come from Alpaca — no Black-Scholes needed.**
- **`feed=opra` is blocked** ("OPRA agreement is not signed" — that's the paid tier).
  `feed=indicative` is the free tier. **Quote freshness measured ~2 s** vs wall clock — effectively real-time,
  not the 15-min delay we feared. Good enough for 0–4 DTE credit spreads.
- Full one-expiration SPY chain = **490 contracts in ~0.83 s** (one call, `limit=1000`). Cheap.
- **Open interest is NOT on the snapshot.** It's on `GET /v2/options/contracts` (and `/contracts/{symbol}`),
  field `open_interest` + `open_interest_date`. Currently dated **2026-08-26** (T-2, normal OCC lag).
  ~60/62 near-money strikes have OI; values are real (1k–58k near the money).
- Stock daily bars for the RV forecast: `feed=sip` **works** (full volume). Also `feed=iex`.
- Option **historical daily bars** `GET /v1beta1/options/bars` work → usable for backtest-lite.
- **VIX index**: not found at `/v1beta1/indices/...`. Proxy vol regime with SPY/QQQ/IWM ATM IV instead, or
  pull VIX from a free external source. Not blocking.

## 3. Multi-leg order ✅ — 4-LEG IRON CONDOR ACCEPTED
- `POST /v2/orders` with `order_class:"mleg"`, 4 legs (buy/sell put + buy/sell call), each leg
  `{symbol, side, ratio_qty, position_intent}`, top-level `type:"limit"`, `limit_price`, `qty`, `time_in_force:"day"`.
- Submitted a long condor at `limit_price:"0.01"` (non-marketable) → **`status: new`, all 4 legs `pending_new` → `new`**,
  0 fills. Cancelled (`DELETE`, 204). Account back to 0 positions / 0 open orders / $100,000 equity. Clean.
- **`limit_price` semantics still to pin down** for a net-credit condor (probe used a debit to stay safe).
  Test a real credit condor with a deliberately-high credit limit on Day 1 to confirm sign/direction.

## Universe check ✅
SPY 774.9 · QQQ 723.9 · IWM 298.4. **All three have daily expirations** every session in the window
(28, 31 Aug · 1, 2, 3, 4 Sep) plus weeklies after. All viable.

---

## Decisions locked

| Question | Answer |
|---|---|
| Structure builder | **Iron condor, single 4-leg `mleg` order.** No paired-verticals fallback needed. |
| Greeks / IV source | **Alpaca snapshot `feed=indicative`.** No Black-Scholes engine. |
| Options feed | `indicative` (OPRA is paid). ~2 s fresh. Prefer **1–3 DTE**; 0DTE only with wider stop buffers. |
| GEX inputs | OI from `/v2/options/contracts`, ±5% strike band, ~2 paginated calls/underlying, refresh 2×/day. OI is T-2 → GEX is approximate, used for regime only. |
| RV forecast input | SIP daily stock bars. |
| Prod loop transport | Lean **`alpaca-py` + REST**. Wire the CLI as a secondary path for the "uses the CLI" requirement + demo. |
| VIX | Not from Alpaca. ATM-IV proxy or external fetch. |

## Still open (Day 1)
- CLI Windows binary install + `alpaca doctor`.
- `mleg` `limit_price` sign convention for net credit.
- Indicative-feed fill model in paper: does a resting credit spread fill at mid, or only if NBBO crosses? Place one real small condor Day 1 and watch.
