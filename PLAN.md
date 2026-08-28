# 7-Day Plan

Hackathon: 28 Aug – 4 Sep 2026. Submissions close **4 Sep 17:00 CEST**.
Market days in window: **Fri 28, Mon 31 Aug · Tue 1, Wed 2, Thu 3, Fri 4 Sep** (6 sessions).
NFP (jobs report) drops **Fri 4 Sep 08:30 ET** — final session. Event-blackout gate must hold.

Team of 2–3, full-time. Lanes: **(A) agent/signal · (B) dashboard · (C) content/write-up.**

---

## Day 0 — Fri 28 Aug (kickoff 17:00 CEST)

- [ ] Watch kickoff, join lablab Discord, read Hackathon Guidelines + Rule Book.
- [ ] **Claim Featherless $25 credits** (first-come-first-served — do this first).
- [ ] Create a **new, dedicated** Alpaca paper account. Set starting balance **$100,000**. Confirm **options Level 3**. Generate API keys.
- [ ] `cp .env.example .env`, fill keys.
- [ ] Install Alpaca CLI, `alpaca doctor`.
- [ ] **Run probes** (`probes/`), record results in `probes/RESULTS.md`:
  - `01_cli_smoke.sh` — CLI auth, account, clock, an option chain query.
  - `02_options_data.py` — snapshot returns greeks + IV; per-contract OI works; measure latency / rate limits for a full-chain OI sweep.
  - `03_multileg_order.py` — does paper `mleg` accept a 4-leg iron condor? If not, fall back to 2× verticals.
- [ ] Repo public on GitHub. CI secrets set.
- [ ] Social post #1 (X + LinkedIn, tag @lablabai @AlpacaHQ): what we're building + why VRP/GEX, not RSI.

## Day 1 — Sat 29 Aug (market closed)

- [ ] A: `agent/signal.py` — regime classifier, VRP (IV vs Yang-Zhang/EWMA RV forecast), GEX from cached OI, skew. Outputs `{sell_premium, structure, bias, conviction, regime}`.
- [ ] A: `agent/surface.py` — Black-Scholes fallback greeks if snapshot greeks are thin.
- [ ] A: backtest-lite — replay ~3 months daily bars, approximate spread P&L, sanity-check the logic isn't pathological. Not a real backtest, a guardrail.
- [ ] A: Featherless ensemble client — 3 open models price a structure, majority vote.
- [ ] B: Next.js skeleton on Vercel, deploy hello-world, wire to read `data/`.
- [ ] C: architecture diagram; social post #2.

## Day 2 — Sun 30 Aug (market closed)

- [ ] A: `agent/execution.py` — CLI wrapper, `mleg` builder, limit-at-mid with reprice ladder, exit manager (50% profit / 2× stop / close-before-expiry).
- [ ] A: `agent/risk.py` — every gate (see strategy spec). Deterministic, unit-tested.
- [ ] A: `agent/desk.py` — main loop; debate only on open decisions; `agent/journal.py` decision log.
- [ ] A: `.github/workflows/desk.yml` — cron every 15 min during RTH, dry-run mode.
- [ ] **End-to-end dry run** — agent decides + logs, places nothing.
- [ ] B: debate feed + open-book components reading real journal output.
- [ ] C: social post #3 — the risk gates.

## Day 3 — Mon 31 Aug (LIVE, session 1)

- [ ] Flip to live paper orders. **Conservative sizing:** 0.5% NAV risk/trade, max 3 concurrent.
- [ ] Watch every cron invocation. Fix bugs immediately. Keep a running incident log.
- [ ] Verify exits fire correctly on a real position.
- [ ] B: equity curve live. C: social post #4 — "we're live" + first fills screenshot.

## Day 4 — Tue 1 Sep (session 2)

- [ ] Scale to target sizing (1–2% NAV/trade, max 5–6) **only if Day 3 was clean**.
- [ ] Nightly reflection job writes first post-mortem + param adjustment.
- [ ] B: prediction ledger view done. C: social post #5 — first real P&L update.

## Day 5 — Wed 2 Sep (session 3)

- [ ] Desk runs. Monitor.
- [ ] B: dashboard feature-complete, polished, deployed at final URL.
- [ ] C: record screen clips of the desk debating + executing. Draft demo-video script.
- [ ] C: social — mid-week results + one lesson learned.

## Day 6 — Thu 3 Sep (session 4)

- [ ] Desk runs. Monitor.
- [ ] C: write `docs/write-up.md` (one page: AI logic · risk gates · Alpaca infra).
- [ ] C: record + edit demo video. Build slide deck. Cover image.
- [ ] C: social — near-final results.

## Day 7 — Fri 4 Sep (session 5, LAST — submit today)

- [ ] Pre-open: confirm NFP blackout gate active (no opens 08:15–09:00 ET).
- [ ] Desk closes / lets expire everything → **flat book by 16:00 ET**.
- [ ] Lock final P&L. Screenshot account + activities.
- [ ] Finalize submission:
  - [ ] Title, short + long description, tags
  - [ ] Cover image, demo video, slide deck
  - [ ] Public GitHub repo URL
  - [ ] Dashboard URL (demo platform)
  - [ ] **Alpaca paper trading account ID** ← required for judging
  - [ ] Up to 5 social post links
  - [ ] One-page write-up
- [ ] **Submit before 17:00 CEST.**
- [ ] Social post — final results + repo.

---

## Cut-list (drop in this order if time runs short)

1. Nightly reflection / self-tuning loop
2. Featherless ensemble → single open model
3. Bull/Bear debate → Desk Head reads signal directly
4. Skew leg of the signal
5. Dashboard polish → static screenshots in the video

**Never cut:** reliable 6-day execution · risk gates · flat book on Day 7 · the write-up · account ID in submission.
