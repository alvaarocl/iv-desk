# Plan

Revised 29 Aug after Alpaca's official guidelines (see `docs/STATUS.md` → "Official rules").

## Hard dates

| What | When |
|---|---|
| **P&L scoring window** | **Mon 31 Aug 09:30 ET → equity snapshot EOD Thu 3 Sep** |
| Trading days that count | **Mon 31 Aug · Tue 1 · Wed 2 · Thu 3 Sep** — 4 sessions |
| Fri 4 Sep | Does **not** count for P&L. NFP that morning is irrelevant to scoring. |
| lablab submission deadline | **Fri 4 Sep 17:00 CEST** |
| Agent must start trading | From the **fresh competition account**, Mon 31 Aug 09:30 ET. Nothing before counts. |

Judged on **total account equity** at the Thursday snapshot (not cash) + creativity, autonomy and
robustness of the agent workflow. **UI is explicitly not required.**

## Consequences

- **Competition trades use expirations ≤ 3 Sep.** Positions should resolve or be cleanly
  marked-to-market by EOD Thursday. Options expiring Sep 3 settle into that snapshot.
- **Dashboard is optional** — build only if lanes A + C are done. It's still good social fuel.
- **A brand-new paper account**, created this weekend, **not touched until Monday 09:30 ET**.
  `PA3TQHQKM5AD` becomes the testing account.
- **Execution goes through the Alpaca CLI**, not raw REST — it's what the rules bless for cron agents.
- Pre-event scaffolding **must be disclosed** in the README.

Team of 2. Lanes: **(A) agent · (B) dashboard (optional) · (C) content/write-up.**

---

## Sat 29 Aug — today (market closed)

- [ ] Create a **new** Alpaca paper account, $100,000, options Level 3. Record its account ID.
      **Do not place any order on it.** Put its keys aside for Monday.
- [ ] Redeem Featherless coupon `ALPACA26` → `FEATHERLESS_API_KEY`.
- [ ] **A:** switch `execution.py` order placement to shell out to the `alpaca` CLI. Keep `marketdata.py`
      REST for reads (or move to `alpaca data option` too). Install the CLI Windows binary, `alpaca doctor`.
- [ ] **A:** build the LLM desk — Quant ensemble (Featherless, 3 models, consensus) + Bull / Bear /
      Desk Head (Anthropic). Wire into `desk.py` as the open-position decision step. Debate only on opens.
- [ ] **A:** decide adaptive vs strict (recommend adaptive), set provisional params.
- [ ] **A:** portfolio net-delta aggregation (replace the `0.0` stub).
- [ ] **C:** README disclosure paragraph (pre-event scaffolding). Draft `docs/write-up.md`.
- [ ] Social post #1: what we're building, why VRP/gamma not RSI.

## Sun 30 Aug — (market closed)

- [ ] **A:** end-to-end dry run against the testing account, all day. Fix everything.
- [ ] **A:** backtest-lite — replay ~3 months of daily bars, approximate condor P&L, confirm the logic
      isn't pathological. Goes in the repo as a guardrail exhibit (rules explicitly allow this).
- [ ] **A:** verify the exit manager on a real position in the **testing** account (open a 1-lot condor,
      watch it take profit / stop / expiry-close correctly).
- [ ] **A:** GitHub Actions secrets = **competition** account keys. Workflow still `dry_run`.
- [ ] **A:** calibrate `vrp_min`, `short_delta`, `min_credit_frac` against Friday's closing chain.
- [ ] **B:** (if ahead) dashboard skeleton on Vercel reading `data/`.
- [ ] **C:** finish write-up draft, slide outline. Social post #2 (architecture).

## Mon 31 Aug → 09:30 ET — GO LIVE (P&L day 1)

- [ ] 09:00 ET: flip workflow `DESK_MODE=live`, competition account. Confirm fresh $100k, zero history.
- [ ] Conservative sizing: 0.5% NAV risk/trade, max 3 positions. Expirations Sep 1–3.
- [ ] Watch **every** 15-min invocation. Keep an incident log. Fix fast.
- [ ] **C:** social post #3 — "we're live", first fills.

## Tue 1 Sep — P&L day 2

- [ ] Scale to target sizing (1–2% NAV, max 5–6) only if Monday was clean.
- [ ] First nightly reflection (optional).
- [ ] **C:** social post #4 — first real P&L update. **B:** dashboard if on track.

## Wed 2 Sep — P&L day 3

- [ ] Desk runs. Prefer expirations Sep 3 (never later than Sep 3 for competition trades).
- [ ] **C:** start recording demo clips of the desk debating + executing. Write-up near final.

## Thu 3 Sep — P&L day 4 (FINAL — equity snapshot EOD)

- [ ] Morning: no new positions that can't resolve or be safely marked by EOD.
- [ ] Through the day: let Sep-3 positions expire; close anything that would carry ugly risk into the snapshot.
- [ ] ~15:45 ET: desk closes remaining open risk. Aim for a clean, well-marked book at EOD.
- [ ] **After close:** screenshot equity, positions, activity log. Lock the P&L number.
- [ ] **C:** finish demo video, deck, cover image.

## Fri 4 Sep — submit (no competition trading)

- [ ] Finalize submission: title, descriptions, tags, cover, video, deck, **public GitHub repo**,
      **competition account ID**, up to 5 social links, one-page write-up.
- [ ] Flip repo to public. Confirm MIT license + pre-event disclosure present.
- [ ] **Submit before 17:00 CEST.**
- [ ] Final social post — results + repo.

---

## Cut-list (drop in this order if time runs short)

1. Dashboard (explicitly not required)
2. Nightly reflection / self-tuning
3. Featherless ensemble → single open model
4. Bull/Bear debate → Desk Head reads the signal directly
5. Skew leg of the signal

**Never cut:** live and trading Monday 09:30 ET · risk gates · CLI execution path · clean book at
Thursday EOD · the write-up · competition account ID in the submission · pre-event disclosure.
