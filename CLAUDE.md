# CLAUDE.md — IV Desk

You are working on **IV Desk**, an entry for the **Alpaca AI Trading Agents Hackathon**
(lablab.ai × Alpaca, 28 Aug – 4 Sep 2026, **$5,000 prize pool** — 1st $2,500 / 2nd $1,500 /
3rd $1,000; some sources quote $6,000 counting two separate $500 social prizes. Verified 29 Aug
against the public event listing — see [`docs/REGLAS-HACKATHON.md`](docs/REGLAS-HACKATHON.md).
Do **not** print any other figure in the write-up or in a social post).

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
thesis — logged to a falsifiable public journal (`data/journal.jsonl`), and shown on a live dashboard
(the LLM desk is built and wired into the loop; the dashboard is a single static page on GitHub
Pages — optional, the rules say no UI is required).

Everything runs on Alpaca's **paper** environment. No real money.

---

## Repo map

| Path | What it is |
|---|---|
| `docs/CONCEPT.md` | **Start here.** Plain-language: what it does, why it wins, alternatives we considered |
| `docs/DOSSIER.md` | The full build explained twice (layperson + technical) + how to field the hard questions. Read before presenting |
| `docs/GLOSSARY.md` | Every technical term defined (options, IV, VRP, GEX, greeks, iron condor, MCP, CLI…) |
| `docs/STATUS.md` | Current build state — what works, what's left, decisions locked vs open |
| `docs/AUDITORIA.md` | **Technical audit** — every known defect with file:line, by severity. Update it in the same PR that fixes the code |
| `docs/REGLAS-HACKATHON.md` | Verified contest rules + judging criteria. Check before claiming anything in the write-up |
| `docs/CALENDARIO.md` | **Every deadline in one place**, in CEST *and* ET. Check before reasoning about any time |
| `docs/RUNBOOK.md` | **Live-session runbook** — startup checklist, what to watch each loop, kill switch, incident tree |
| `docs/VIABILIDAD.md` | Viability judgement, positioning, and the priority order for the remaining work |
| `docs/API-ALPACA.md` | Alpaca API/CLI/feed conventions — **mleg limit_price is signed**. Read before touching order code |
| `docs/strategy-spec.md` | The precise strategy: signal maths, strike selection, every risk gate, trade management |
| `docs/game-plan.html` | The team-facing strategy + 7-day plan, designed to read at a glance |
| `docs/write-up.md` | The one-page submission write-up. **Written from the code, never from the plan** — anything not built by Thursday does not appear in it |
| `PLAN.md` | Day-by-day task checklist with a cut-list |
| `probes/` | Day-0 API de-risking scripts + `RESULTS.md` (findings that locked our design decisions) |
| `agent/` | The trading engine (see below) |
| `dashboard/` | Single static `index.html` on GitHub Pages, reads `data/` live — https://alvaarocl.github.io/iv-desk/ |
| `.github/workflows/desk.yml` | Scheduled loop, every 15 min during market hours |

### `agent/` modules

| Module | Responsibility | State |
|---|---|---|
| `broker.py` | Trading API client (account, orders, `mleg`, positions, cancel) | ✅ shells out to the Alpaca CLI (`_cli()` → `alpaca api METHOD /path`); `limit_price` signed, zero rejected |
| `marketdata.py` | Option chain snapshots (greeks + IV), option contracts (open interest), stock bars | ✅ tested live |
| `signal.py` | Deterministic signal: RV forecast, VRP **ratio**, normalized GEX, regime, skew, `stand_down` reason → `Signal` | ✅ runs; **thresholds provisional** pending the backtest |
| `execution.py` | Strike selection (condor + vertical), sizing, deterministic exit manager, trade log | ✅ runs; exit manager untested on a real position |
| `risk.py` | The Risk Officer — every gate, no discretion. `evaluate()` is the single entry point | ✅ done |
| `calendar.py` | Static macro-event calendar for the blackout gate (NFP, ISM, etc.) | ✅ done; verify dates |
| `desk.py` | Main loop: exits → gates → signal per name → open decision → journal | ✅ dry-run works |
| `journal.py` | Append-only decision log (`data/journal.jsonl`) + equity curve + prediction ledger | ✅ done |
| `seats.py` / `debate.py` | LLM desk: Quant ensemble / Bull / Bear / Desk Head, only on open decisions | ✅ built + **wired into `desk.py:248`**; 100% Featherless; can only trim or veto `n`, never widen |

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

### Credentials

- **Local `.env`** (never committed) — `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` for the **testing**
  account `PA3TQHQKM5AD`. All local runs use this.
- **GitHub Actions secrets** — the same names but for the **competition** account `PA39HSCQE8S3`.
  Set these Sunday; the live cron uses them from Mon 09:30 ET.
- `FEATHERLESS_API_KEY` — redeem coupon `ALPACA26` at featherless.ai; powers the Quant ensemble
- `FEATHERLESS_ARGUER_MODEL` — the Bull / Bear / Desk Head seats. Optional: defaults to the
  first id in `FEATHERLESS_MODELS`. **The whole desk runs on Featherless** (issue #31) — there is
  no second provider and no out-of-pocket spend.
- Each Alpaca paper account has its **own** key pair — generate the UC3M keys from the dashboard
  after switching to that account.

---

## Conventions & locked decisions

Settled by the Day-0 probes (`probes/RESULTS.md`) — **do not re-litigate without a reason**:

- **Structure:** iron condor as a single 4-leg `order_class:mleg` order. Confirmed working on paper.
- **Option data feed:** `feed=indicative` (OPRA is a paid add-on we don't have; indicative measured ~2s fresh).
- **Greeks + IV:** taken from Alpaca snapshots. No Black-Scholes engine.
- **Open interest:** only on `/v2/options/contracts`, dated T-2. Used for GEX (regime signal only, approximate is fine).
- **DTE:** prefer 1–3 days. 0DTE only with wider stop buffers.
- **Transport:** order placement goes through the **Alpaca CLI** (`alpacahq/cli`, pinned `v0.0.14`) —
  the rules require MCP or CLI, and the CLI is built for cron agents. `agent/broker.py` shells out via
  `_cli()`; `httpx` REST (`agent/marketdata.py`) is used for market-data reads only. *(migration done
  29 Aug, issue #4 closed.)*
- **Universe:** SPY, QQQ, IWM. All have daily expirations through the competition window.
- **Risk posture:** a single consistent core book. The directional satellite sleeve was removed on
  29 Aug (issue #14) — it was never implemented and `satellite_frac` was never read.
- **Competition trades use expirations ≤ 3 Sep** — the equity snapshot is EOD Thursday 3 Sep
  (confirmed in Discord 29 Aug; Fri-4-Sep expirations are excluded from the measurement).
- **Accounts:** testing = "Paper Trading" `PA3TQHQKM5AD` (has cancelled probe orders — all dev/testing
  runs here). Competition = "PAPER UC3M" `PA39HSCQE8S3` — untouched, first order Mon 31 Aug 09:30 ET,
  its keys live only in GitHub Actions secrets.

### Judging criteria — there are FOUR, not five

**P&L Performance · Technology Implementation · Creativity & Originality · Presentation & Execution.**

**Social Engagement is a separate prize, not an axis of the rubric.** So P&L is worth **~25%, not
~20%** — which is why "we concede the P&L axis" is not a free move. See
[`docs/REGLAS-HACKATHON.md`](docs/REGLAS-HACKATHON.md) and [`docs/VIABILIDAD.md`](docs/VIABILIDAD.md).

### Official Alpaca rules that shape the work (received 29 Aug)

- **P&L scoring window (✅ confirmed in Discord, 29 Aug): Mon 31 Aug 09:30 ET → Fri 4 Sep 09:30 ET,
  total-equity snapshot at the close of Thu 3 Sep.** Four sessions count (31 Aug, 1–3 Sep).
  Positions expiring Fri 4 Sep are **excluded** — competition trades use expirations ≤ 3 Sep.
  Literal quote in `docs/REGLAS-HACKATHON.md`. (#19)
- Judged on **total account equity** (not cash) + creativity, autonomy, robustness of the workflow.
- **A user interface is NOT required** — "primarily evaluating the autonomous agent workflow and its
  trading performance". The dashboard is optional; build it only if the agent + write-up are done.
- Agent must start trading from the fresh competition account at Mon 31 Aug 09:30 ET; nothing earlier counts.
- Pre-event scaffolding is allowed **but must be disclosed in the README**.
- Free tier's latest option quotes are real-time (only historical bars/trades carry the 15-min delay).

### Open questions (need a human call)

- ~~**Regime-adaptive vs strict discipline.**~~ **Decided 29 Aug (issue #12): stand down in a trending
  tape** rather than fade it, behind `params.fade_trend` (set `True` to restore the old behaviour).
  Fading a trend with short premium is how short-vol books die, and it was gated only by a noisy
  GEX sign.
- **Still open: parameter calibration.** `vrp_ratio_min`, `gex_min` and the
  `(width, short_delta, min_credit_frac)` trio are **provisional** until the backtest (issue #5)
  runs against real chain data. They currently encode a judgement, not a measurement.

---

## Working style for this repo

- Small team (2), 7 days. Branch per lane — `lane/ejecucion` (Álvaro: `broker.py`, `execution.py`,
  workflow, tests), `lane/senal` (Ángel: `signal.py`, `config.py`, backtest), `lane/entrega` (docs,
  LLM layer) — PR to `main`. **Lanes own disjoint files on purpose**: don't edit another lane's files.
  Full cycle in [`CONTRIBUTING.md`](CONTRIBUTING.md).
- `main` must always run clean in `dry_run` — the scheduled loop trades from it.
- `data/journal.jsonl`, `data/equity.csv`, `data/trades.jsonl` are written by the loop and committed by
  the workflow. Don't hand-edit. On a merge conflict there, take `origin/main`.
- Never commit `.env` or keys.
- The hackathon requires a **public** repo at submission — flip visibility to public on 4 Sep, not before.
- During the live sessions (Mon–Thu, 15:30–22:00 CEST) [`docs/RUNBOOK.md`](docs/RUNBOOK.md) rules: no
  code deploys mid-session unless the desk is losing money to a bug.

## What matters for judging (so you prioritise correctly)

Four axes (above), of which P&L is ~25%: total account equity at the Thu 3 Sep snapshot, plus the
creativity, autonomy and robustness of the autonomous agent workflow. Winners are **not** picked on P&L alone, and **no UI is required**. So the
priority order is: (1) a fresh account trading live and reliably from Mon 09:30 ET, (2) a workflow
that is genuinely autonomous and robust (the LLM desk + risk gates + CLI execution), (3) the write-up
and demo video, (4) social posts, (5) the dashboard only if everything else is done. See
`docs/game-plan.html` and `docs/CONCEPT.md` for the reasoning.
