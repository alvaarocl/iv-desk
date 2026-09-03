# IV Desk — One-Page Write-Up

> Every sentence here can be checked by opening the file named in parentheses. Nothing is described
> in the present tense unless it exists in the repo. The only blanks are the live-window numbers,
> marked `[Results: fill Thu 3 Sep after the close]`.

**IV Desk is an autonomous options desk that sells the volatility risk premium — and documents every
time it decides not to.**

## What it is

It does not predict direction. It harvests the gap between implied vol and a forecast of realized
vol on SPY, QQQ and IWM (`agent/config.py` → `UNIVERSE`), gated by dealer gamma positioning (GEX),
and expresses it only as defined-risk structures — iron condors and credit verticals at 1–3 DTE
(`agent/signal.py` → `pick_expiration`) submitted as a **single 4-leg `order_class: mleg` order**
(`agent/broker.py` → `submit_mleg`). It runs unattended on a dedicated Alpaca **paper** account
every 15 minutes during RTH from a GitHub Actions cron (`.github/workflows/desk.yml`).

## We measured before we built

Three probes against the **live** market on 28 Aug, output committed (`probes/RESULTS.md`), four
design decisions straight out of them:

- Greeks and IV come from Alpaca's snapshots → **we ship no Black-Scholes engine** (`agent/marketdata.py`).
- OPRA is a paid tier we don't have; the free `indicative` feed measured **~2 s fresh** → the whole
  design targets 1–3 DTE.
- Open interest isn't on the snapshot — it's on `/v2/options/contracts`, dated T-2 → GEX is a
  *regime* signal with a dead zone, never a precision input (`agent/signal.py` → `gex_state`).
- A 4-leg condor was accepted as one `mleg` order at options level 3 → no paired-verticals fallback
  was built.

## Architecture: the LLM never touches the money path

| Layer | Deterministic? | Verify in |
|---|---|---|
| **Signal** — Yang-Zhang + EWMA RV forecast vs ATM IV → VRP *ratio*; normalized GEX; ADX/EMA regime; skew | Yes | `agent/signal.py` |
| **Structure & sizing** — strikes at a target short delta behind liquidity gates; contracts sized so max loss ≤ risk budget | Yes | `agent/execution.py` → `select_condor`, `size` |
| **Risk Officer** — every gate, **no discretion, no LLM path into it**; `evaluate()` returns `(ok, reason)` | Yes | `agent/risk.py` |
| **Trade management** — 50% of credit take-profit, 2× credit stop, close on expiry day | Yes | `agent/execution.py` → `manage_exits` |
| **The desk (LLM)** — four seats arguing **one** thing: whether to open a trade already approved | No, and bounded | `agent/debate.py` |
| **Journal** — append-only JSONL of every signal, rejection, debate, open and exit | Yes | `agent/journal.py` |

The debate runs **only on an opening decision**, after the deterministic layers are done
(`agent/desk.py` → `_consider`). **The LLM cannot increase risk by construction, not by prompt:**
`review_open()` receives `cap_contracts`, the size the Risk Officer already approved, and the final
size is one line (`agent/debate.py`):

```python
contracts = max(0, min(int(head.contracts), cap))
```

It can trim, veto, or do nothing. Every failure mode — outage, timeout, truncated JSON, a split
ensemble — resolves to `approved=False` with the reason recorded; there is no path where garbage
means "yes" (`agent/seats.py`, design rule 2).

This mirrors, almost point for point, the architecture Alpaca publishes as good practice in
[*Building a Multi-Agent AI Trading System on Alpaca*](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)
(cited in `docs/REGLAS-HACKATHON.md`): specialised agents over one generalist prompt, a critic
validating against predefined rules, a **deterministic Python risk guard with no LLM**, and
monitoring every 15 minutes. We converged on it independently, then found the article.

## The desk: four seats, open models, all on Featherless

One provider, one transport class, no proprietary model in the loop (`agent/seats.py` →
`FeatherlessSeatClient`; `agent/debate.py` → `DeskClients.build`). Each seat is defined by what
makes its output *unusable*:

- **Quant** — up to 3 open models vote independently on the same ballot. Consensus needs a strict
  majority **of the models dispatched**, not of those that answered, *and* agreement on the
  structure the deterministic layer picked (`agent/seats.py` → `consensus`).
- **Bull / Bear** — must anchor claims to numeric `Signal` fields and name them; fewer than two
  *real* field names and the argument is discarded (`agent/seats.py` → `argue`).
- **Desk Head** — final size (≤ cap) plus a **falsifiable prediction**: a closing range on the
  expiration date. Inverted, non-numeric or implausible ranges are rejected, so the trade doesn't
  happen (`agent/seats.py` → `_validate_prediction`).

The whole debate carries a 90 s wall-clock budget with per-seat deadlines, because the tick is 15
minutes. `DESK_DEBATE=off` is the kill switch; the default is `required` — no working LLM layer
means no new positions.

## Risk gates (`agent/risk.py`, thresholds in `agent/config.py`)

Per-trade max loss ≤ 0.5% NAV · portfolio open risk ≤ 10% NAV · ≤ 8 concurrent positions · net delta
band ±0.30 of NAV · −3% daily-loss breaker · drawdown throttle to half size at 8%, hard halt at 12%
· **asymmetric** macro-event blackout (2 h before a release, 45 min after) over a hand-verified
calendar of the window's prints (`agent/calendar.py`) · no new 0DTE after 14:00 ET.

That asymmetry shows how the desk reasons about its own gates: the risk is opening premium into an
*unresolved* print, and it lives entirely before the release — afterwards IV crushes, which is the
best entry of the day for a premium seller. The argument is written next to the constant.

Two guards sit outside `evaluate()` so they hold even if it never runs: an **account guard** that
refuses live mode against the wrong account and refuses to touch the competition account before the
window opens, and **early-assignment detection** — any unexpected equity position forces exits-only
(`agent/desk.py` → `_guard_account`, `_assignment_alert`).

## A falsifiable record, including the non-trades

Every tick appends to `data/journal.jsonl` (`agent/desk.py` → `run_once`, `_consider`):

- `portfolio` — NAV, day P&L, open risk, positions, net delta, size multiplier, breaker state.
- `signal`, **per underlying** — the full deterministic read *plus a `stand_down` field naming the
  gate that blocked it*: `vrp`, `gex`, `trend` or `data` (`agent/signal.py`). A quiet desk is not a
  silent one: the record says which gate said no, and with what numbers.
- `rejected` — the Risk Officer's reason string whenever a proposed trade fails a gate.
- `debate` — the **complete transcript**: every ballot, both arguments, the Desk Head's decision,
  the cap, the final size, the elapsed clock (`agent/debate.py` → `DebateOutcome.to_record`) —
  written whether it approved or stood down.
- `opened` / `exit` — strikes, contracts, credit, max loss, thesis; then the exit reason
  (`take_profit` / `stop` / `expiry_close`) and realised P&L, plus `data/equity.csv`.

A desk that stands down before an ISM print with a documented reason is a better demonstration of
autonomy than one that got three condors right. The journal lets a judge check that instead of
believing it.

## Standing down, not rationalizing: two real vetoes from this week

The calibration behind these gates is measured, not assumed: a 60-session replay against real
Alpaca chain data (`backtest/RESULTS.md`) put 174 underlying-sessions through the same funnel the
live desk runs — the VRP gate alone kills 121 of them (174 → 48), dealer gamma kills most of what's
left (48 → 16), the trend and structure/credit gates narrow it further, and the whole funnel
converges on **11 trades opened, +$484 held-to-expiry**. That is the evidence the risk gates do
something, not a claim about them.

Two live examples from the actual competition window, not the backtest:

- **A signal-rich, mesa-vetoed candidate (2 Sep, `data/journal.jsonl`).** SPY cleared VRP
  (ratio 1.61, well above the 1.05 floor) and, on the deterministic layer alone, would have gone
  to the Quant ensemble — but GEX read −0.106 (dealers short gamma), so `signal.py` stood it down
  before the mesa was even due to see it. The debate ran anyway, in an **observation-only shadow
  mode** added mid-week specifically so a GEX veto doesn't also mean a silent LLM layer
  (`agent/desk.py` → `_maybe_shadow_debate`): 2 of 3 Quant models confirmed the structure, Bull and
  Bear argued genuinely opposite cases (similarity score 0.082 — not two copies of the same
  answer), and the **Desk Head overruled its own Quant majority**: *"The GEX signal must be strong
  enough to overcome the high ATM IV and choppy regime for this trade to win."* Full transcript in
  the journal, `shadow: true`.
- **A signal-clear, structurally-blocked candidate (3 Sep).** On the last scored session SPY
  cleared *every* signal gate — VRP ratio 1.74, GEX +0.58 (dealers long gamma, the regime the
  strategy is built to sell into) — sized to 7 contracts by the Risk Officer, and was still
  rejected before it reached the desk: credit/width came back at 0.10 against the 0.20 floor
  (`agent/config.py` → `min_credit_frac`). A 0-DTE condor simply doesn't carry as much credit per
  unit of width as the 1–3 DTE structures that floor was calibrated on, and the gate caught it.

Neither of those is the strategy failing to fire. It is three independent, code-enforced opinions
— the deterministic gate, the LLM mesa, and the credit floor — agreeing that a rich-looking signal
still wasn't a trade worth the risk, each for a different, logged reason.

## Alpaca stack usage

- **Trading API through the official CLI.** Every trading call in the production loop shells out to
  `alpaca api METHOD /path` — account, clock, positions, orders, cancels, `/v2/options/contracts`,
  and the `mleg` submission (`agent/broker.py` → `_cli`). The binary is pinned and version-verified
  in CI (`.github/workflows/desk.yml`).
- **`order_class: mleg`** — `limit_price` is **signed** (negative = credit), passed through verbatim;
  `submit_mleg` refuses a zero price rather than guess. Orders are async, so the loop polls before
  treating a position as open (`agent/execution.py` → `_await_fill`).
- **Options market data over REST** (allowed for reads): chain snapshots with greeks and IV
  (`feed=indicative`), per-contract open interest, SIP daily bars (`agent/marketdata.py`).
- **Idempotent and self-healing.** `client_order_id` is deterministic per trade intent, so a re-run
  cannot duplicate an order; every tick reconciles against Alpaca as the source of truth
  (`agent/execution.py` → `_client_order_id`, `reconcile`).
- **Paper only.** Competition account **PA39HSCQE8S3**, $100,000, first order Mon 31 Aug 09:30 ET,
  used for nothing before that. Development ran on a separate paper account (`PA3TQHQKM5AD`),
  disclosed in the README.

## Engineering

177 tests, no network and no API keys required: the four-seat debate runs end-to-end against
injected transport doubles (`tests/test_debate.py`), strike selection and the exit manager against
synthetic chains (`tests/test_execution.py`), the gates and account guard directly
(`tests/test_risk_and_guard.py`), and — added mid-week when Alpaca's feed turned out not to publish
greeks for same-day options — a Black-Scholes implied-vol solver with 23 tests of its own
(`tests/test_blackscholes.py`), including the numerical case (near-zero vega) that made an early
version of it silently wrong. Every tunable is one dataclass with the reasoning for each number
written beside it (`agent/config.py`).

## Results — [Results: fill Thu 3 Sep after the close]

Window: Mon 31 Aug 09:30 ET → equity snapshot at Thu 3 Sep close. Four sessions.

- Trades closed [N] · win rate [X]% · ending equity $[X] · return [X]% · max drawdown [X]%.
- Documented stand-downs: [N], by gate (`vrp` / `gex` / `trend` / risk / desk veto).
- Predictions made [N] · resolved correct [N] · circuit-breaker triggers [N].
- Incidents resolved live: [N] — logged in `docs/RUNBOOK.md`.

**Repo:** [URL] · **Demo video:** [URL] · **Account:** PA39HSCQE8S3
