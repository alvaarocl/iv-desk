# CLAUDE.md — IV Desk

You are working on **IV Desk**, an entry for the **Alpaca AI Trading Agents Hackathon**
(lablab.ai × Alpaca, 28 Aug – 4 Sep 2026, $6,300 prize pool).

If someone asks "what is this project about?", give them the plain-language explanation from
[`docs/CONCEPT.md`](docs/CONCEPT.md) and point them at [`docs/GLOSSARY.md`](docs/GLOSSARY.md) for any
term they don't know. Those two files are written for a teammate who is **not** a trader — use them.

---

## One-paragraph summary

IV Desk is an autonomous options trading agent that behaves like an **insurance company for the stock
market**. It sells "insurance" (options premium) on index ETFs (SPY, QQQ, IWM) — but only when that
insurance is statistically overpriced (positive **volatility risk premium**) and market conditions
favour it (**dealer gamma** positive). It trades defined-risk structures (mostly **iron condors**,
1–3 days to expiration), manages every position with mechanical rules (take profit at 50%, stop at 2×,
close before expiry), and enforces hard risk gates (per-trade risk cap, daily circuit breaker,
drawdown throttle, macro-event blackout). On top of the deterministic engine sits an **LLM "desk"** of
named agents (Quant / Bull / Bear / Desk Head) that debate each new position and write a falsifiable
thesis, all shown on a **live public dashboard**.

Everything runs on Alpaca's **paper** environment. No real money.

---

## Repo map

| Path | What it is |
|---|---|
| `docs/CONCEPT.md` | **Start here.** Plain-language: what it does, why it wins, alternatives we considered |
| `docs/GLOSSARY.md` | Every technical term defined (options, IV, VRP, GEX, greeks, iron condor, MCP, CLI…) |
| `docs/STATUS.md` | Current build state — what works, what's left, decisions locked vs open |
| `docs/strategy-spec.md` | The precise strategy: signal maths, strike selection, every risk gate, trade management |
| `docs/game-plan.html` | The team-facing strategy + 7-day plan, designed to read at a glance |
| `docs/write-up.md` | Skeleton of the one-page submission write-up (fill on Day 6–7) |
| `PLAN.md` | Day-by-day task checklist with a cut-list |
| `probes/` | Day-0 API de-risking scripts + `RESULTS.md` (findings that locked our design decisions) |
| `agent/` | The trading engine (see below) |
| `dashboard/` | Live "trading floor" (Next.js / Vercel) — **not built yet** |
| `.github/workflows/desk.yml` | Scheduled loop, every 15 min during market hours |

### `agent/` modules

| Module | Responsibility | State |
|---|---|---|
| `broker.py` | Alpaca Trading API REST client (account, orders, `mleg`, positions, cancel) | ✅ tested live |
| `marketdata.py` | Option chain snapshots (greeks + IV), option contracts (open interest), stock bars | ✅ tested live |
| `signal.py` | Deterministic signal: RV forecast, VRP, GEX, regime, skew → `Signal` object | ✅ runs; needs calibration |
| `execution.py` | Strike selection (condor + vertical), sizing, deterministic exit manager, trade log | ✅ runs; exit manager untested on a real position |
| `risk.py` | The Risk Officer — every gate, no discretion. `evaluate()` is the single entry point | ✅ done |
| `calendar.py` | Static macro-event calendar for the blackout gate (NFP, ISM, etc.) | ✅ done; verify dates |
| `desk.py` | Main loop: exits → gates → signal per name → open decision → journal | ✅ dry-run works |
| `journal.py` | Append-only decision log (`data/journal.jsonl`) + equity curve + prediction ledger | ✅ done |
| LLM desk (Quant ensemble / Bull / Bear / Desk Head) | The debate layer on top of the signal | ❌ **not built** |

---

## How to run

```bash
uv sync                              # install deps
cp .env.example .env                 # then fill in keys (see below)
uv run python -m agent.desk          # one loop iteration (dry_run by default — logs, places nothing)
uv run ruff check agent/             # lint
uv run pytest -q                     # tests (thin so far)
```

`DESK_MODE=dry_run` (default) logs the full decision path without placing orders.
`DESK_MODE=live` places real paper orders. **Do not set `live` until the strategy is calibrated and
the exit manager has been verified on a real position.**

### Credentials (`.env`, never committed)

- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` — the hackathon paper account `PA3TQHQKM5AD` ($100k, options L3)
- `FEATHERLESS_API_KEY` — redeem coupon `ALPACA26` at featherless.ai; powers the Quant ensemble
- `ANTHROPIC_API_KEY` — the Bull / Bear / Desk Head seats

---

## Conventions & locked decisions

Settled by the Day-0 probes (`probes/RESULTS.md`) — **do not re-litigate without a reason**:

- **Structure:** iron condor as a single 4-leg `order_class:mleg` order. Confirmed working on paper.
- **Option data feed:** `feed=indicative` (OPRA is a paid add-on we don't have; indicative measured ~2s fresh).
- **Greeks + IV:** taken from Alpaca snapshots. No Black-Scholes engine.
- **Open interest:** only on `/v2/options/contracts`, dated T-2. Used for GEX (regime signal only, approximate is fine).
- **DTE:** prefer 1–3 days. 0DTE only with wider stop buffers.
- **Transport:** `httpx` + REST (`agent/broker.py`, `agent/marketdata.py`). The Alpaca CLI is wired as a
  secondary path to satisfy the "must use MCP or CLI" requirement + for the demo.
- **Universe:** SPY, QQQ, IWM. All have daily expirations through the competition window.
- **Risk posture:** consistent core book + a small (≤15% of risk budget) directional satellite sleeve.

### Open questions (need a human call)

- **Regime-adaptive vs strict discipline.** As of 28 Aug the tape is low-vol (ATM IV 6–10%), so the pure
  VRP signal produces zero trades. Leaning toward adaptive: sell condors when VRP is rich, buy cheap
  directional debit spreads when gamma is negative and the tape trends. Keeps discipline, guarantees a
  P&L track record (which is a judged axis). Final call + parameter calibration happens Monday 31 Aug
  with real open-market quotes.

---

## Working style for this repo

- Small team (2), 7 days. Branch per lane (`lane/a-signal`, `lane/b-dashboard`, `lane/c-content`), PR to `main`.
- `main` must always run clean in `dry_run` — the scheduled loop trades from it.
- `data/journal.jsonl`, `data/equity.csv`, `data/trades.jsonl` are written by the loop and committed by
  the workflow. Don't hand-edit. On a merge conflict there, take `origin/main`.
- Never commit `.env` or keys.
- The hackathon requires a **public** repo at submission — flip visibility to public on 4 Sep, not before.

## What matters for judging (so you prioritise correctly)

Five axes, roughly equal weight: P&L Performance, Technology Implementation, Creativity & Originality,
Presentation & Execution, Social Engagement. We concede the P&L axis (a lucky gambler wins it in a
6-day window) and press the other four. Reliability — actually trading all 6 days on the fresh account —
beats ~80% of entrants on its own. See `docs/game-plan.html` for the full mapping.
