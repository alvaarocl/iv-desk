# IV Desk — One-Page Write-Up

> Submission deliverable. Fill the bracketed parts on Day 6–7. Keep to ~1 page.

## What it is

IV Desk is an autonomous options trading desk that harvests the **volatility risk premium** on index ETFs (SPY, QQQ, IWM), gated by **dealer gamma positioning**. It runs unattended on Alpaca's paper environment for the full competition via a scheduled Alpaca CLI loop.

## AI logic

- **Signal (deterministic):** a realized-volatility forecast (Yang-Zhang + EWMA) is compared to at-the-money implied vol from Alpaca option snapshots to measure VRP. Aggregate dealer gamma exposure (GEX) is computed from chain open interest to classify the tape as mean-reverting or trending. Skew and a regime classifier (EMA/ADX/VIX/GEX) select the structure.
- **Desk (LLM, only on open decisions):** a Quant seat — an ensemble of [N] open-source models served by Featherless that must reach consensus — proposes the structure and strikes. Bull and Bear seats argue the directional lean. A deterministic Risk Officer returns a hard size cap and vetoes. A Desk Head seat commits the final trade with a written, falsifiable thesis that is later graded.
- **Management (deterministic):** take profit at 50% of max credit, stop at 2× credit, close before expiration.

## Risk gates

Per-trade max loss ≤ [X]% NAV · portfolio max loss ≤ 10% NAV · ≤ 6 concurrent positions · net |delta| bounded · −3% daily loss circuit breaker · drawdown throttle at 8% / hard stop at 12% · macro event blackout (incl. NFP on the final session) · no 0DTE opens after 14:00 ET · assignment avoidance by 15:45 ET on expiry. The Risk Officer is pure code with no discretion; the LLM seats cannot override it.

## Alpaca infrastructure

- **CLI** (`alpacahq/cli`) — production trading loop on a 15-minute cron during market hours: order placement (`order_class: mleg`), positions, account, market clock.
- **MCP server** — an "ask the desk" interface for live exploration of the desk's current state and reasoning.
- **Options market data** — snapshot endpoint (greeks, IV) and per-contract open interest (cached) build the vol surface and GEX.
- Fresh dedicated paper account, $100,000 starting balance. Account ID: **PA39HSCQE8S3**.

## Results (fill Day 7)

- Trading window: 28 Aug – 4 Sep 2026, [N] sessions.
- Trades: [N] closed · win rate [X]% · avg win $[X] · avg loss $[X] · profit factor [X].
- Ending equity: $[X] · return [X]% · max drawdown [X]% · [N] circuit-breaker triggers.
- Prediction ledger: [X]/[N] theses resolved correct.

## Links

Repo: [URL] · Live dashboard: [URL] · Demo video: [URL]
