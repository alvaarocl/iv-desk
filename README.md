# IV Desk

An autonomous options **trading desk** for the [Alpaca AI Trading Agents Hackathon](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon) (28 Aug – 4 Sep 2026).

It does not trade price. It trades the **volatility risk premium**, gated by **dealer gamma positioning**, and it does so as a small desk of named agents whose every decision is a public, falsifiable transcript.

---

## New here? Read these first

| Doc | For |
|---|---|
| [`docs/CONCEPT.md`](docs/CONCEPT.md) | **Plain-language** explanation — what it does, why it wins, alternatives we considered. Start here if you're not a trader. |
| [`docs/GLOSSARY.md`](docs/GLOSSARY.md) | Every technical term defined (options, IV, VRP, GEX, greeks, iron condor, MCP, CLI…). |
| [`docs/STATUS.md`](docs/STATUS.md) | What works now, what's left, decisions locked vs open. |
| [`docs/strategy-spec.md`](docs/strategy-spec.md) | The precise strategy — signal maths, strike selection, every risk gate. |
| [`docs/game-plan.html`](docs/game-plan.html) | The strategy + 7-day plan as a designed one-pager (open in a browser). |
| [`PLAN.md`](PLAN.md) | Day-by-day task checklist. |
| [`CLAUDE.md`](CLAUDE.md) | Orientation for a fresh Claude Code session in this repo. |

The rest of this README is the technical thesis.

---

## Thesis

Short-dated index options are structurally overpriced: implied volatility tends to exceed subsequently realized volatility (the *volatility risk premium*, VRP). Harvesting that premium is positive expectancy **only when you are disciplined about (a) when the premium is actually rich, (b) what the dealer-hedging regime is doing to price dynamics, and (c) mechanical trade management.** Humans are not disciplined about those. An agent can be.

- **VRP** — sell premium only when IV (from Alpaca option snapshots) exceeds a realized-vol forecast (Yang-Zhang / EWMA) by a threshold.
- **Dealer gamma (GEX)** — aggregate gamma exposure from chain open interest. Positive GEX ⇒ mean-reverting tape ⇒ iron condors. Negative GEX ⇒ trending tape ⇒ stand down or trade a directional debit spread.
- **Skew** — put/call IV asymmetry picks the structure and the strikes.
- **Management is deterministic** — take profit at 50% of max credit, stop at 2× credit received, close before expiration to avoid pin risk. No LLM in this loop.

Risk posture: **consistent core + small satellite.** Core book aims for modest positive P&L with defined risk and hard drawdown gates. A 10–15% satellite sleeve takes one higher-conviction directional spread when the signal is strong.

---

## The desk

| Seat | Role | Implementation |
|---|---|---|
| **Quant** | Prices the vol surface, proposes structures | Deterministic surface math + Featherless open-model ensemble (3 models vote, consensus required) |
| **Bull / Bear** | Argue the directional lean for the underlying | LLM, structured debate |
| **Risk Officer** | Hard veto on every risk gate | Deterministic (`risk.py`) — no discretion |
| **Desk Head** | Final sizing + allocation across SPY / QQQ / IWM | LLM, bounded by Risk Officer output |

Full debate runs **only on open-position decisions** (a handful per day). Monitoring and exits are pure Python.

---

## Alpaca stack usage

- **CLI** (`alpacahq/cli`) — the 6-day production trading loop (cron). Order placement, positions, account, clock/calendar.
- **MCP server** — the "ask the desk" chat interface and live judge exploration.
- **Options market data** — snapshot endpoint for greeks + IV; per-contract endpoint for open interest (cached).
- **`order_class: mleg`** — multi-leg condors / verticals with bracket exits.
- **Paper only.** Fresh dedicated account, $100,000 starting balance.

---

## Repo layout

```
agent/        the desk: signal, risk, execution, debate, loop, journal
probes/       Day-0 de-risking scripts (run once API keys exist)
dashboard/    Next.js live "trading floor" (equity curve, debate feed, prediction ledger)
docs/         strategy spec + the one-page write-up for submission
data/         journal.jsonl, equity.csv, gex cache (git-tracked audit trail)
.github/      scheduled workflow that runs the loop
```

See `PLAN.md` for the day-by-day plan and `docs/strategy-spec.md` for signal + risk-gate detail.

---

## Pre-event work disclosure

Per the hackathon rules, work done before the official P&L window (Mon 31 Aug 09:30 ET) is disclosed here:

- This repository was created on **28 Aug 2026** (kickoff day). Initial commits are the project
  scaffold, documentation, Day-0 API de-risking probes, and the deterministic trading engine
  (`agent/`), all developed 28–30 Aug.
- All prototyping and testing before the P&L window ran on a **separate testing paper account**
  (`PA3TQHQKM5AD`). The official competition account (`PA39HSCQE8S3`) is a fresh $100,000 paper
  account that places its first order on **Mon 31 Aug 09:30 ET** and is used for nothing before then.
- No pre-existing private libraries are depended on. Third-party dependencies are listed in
  `pyproject.toml`.
- The agent, its options workflow (Alpaca Trading API via the CLI), and the LLM desk layer were all
  built during the event.
