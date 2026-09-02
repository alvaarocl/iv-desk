# Narration — IV Desk presentation video

The silent video is `out/iv-desk-presentation.mp4` — **1920×1080, 60 fps, ~3:06, no audio track**.
Run this script through a TTS, then lay the voice under the video.

- English. Neutral, unhurried, a little dry. **~150 words per minute.**
- **Start speaking ~0.7 s after each scene cut** (let the visual land) and aim to **finish ~1 s
  before the next cut**.
- Total spoken ≈ **2:55** inside the ~3:06 video.
- If a block runs long against its scene, lengthen that scene in `src/data.ts` → `SCENES` and
  re-render — don't rush the read. Your audio is the master; move the scenes to fit it.

Timestamps are where each scene *starts*.

---

### 0:00 — S1 · Hook  (42 words · ~17 s)

> Most trading agents are a wrapper around a moving average. This one doesn't predict price. It
> sells overpriced volatility on three index ETFs — and most of the time, it decides not to. Every
> refusal is on the record, with a reason.

### 0:21 — S2 · The signal  (80 words · ~32 s)

> The signal is deterministic Python. It reads the option surface, not the price chart. Implied
> volatility over a forecast of realized volatility gives the volatility risk premium — as a ratio,
> so it holds in any volatility regime. Dealer gamma, from open interest, says whether that premium
> is safe to sell, with a dead zone near zero because the data is two days old. Three gates. Any
> one of them stands the desk down, and each writes the number that said no.

### 0:54 — S3 · The desk  (78 words · ~31 s)

> Only then does the language-model desk get a say. Four seats, all open models, all on Featherless.
> A three-model Quant ensemble votes, and needs a strict majority of the models we dispatched — not
> of the ones that answered. Bull and Bear argue direction, and an argument that doesn't cite real
> fields from the signal is thrown away. The Desk Head sizes the trade and writes a falsifiable
> prediction: a closing range, on a date.

### 1:27 — S4 · Discipline, the funnel  (63 words · ~24 s)

> This is the part we're proudest of. Over sixty real sessions and three underlyings, the
> deterministic layer found a hundred and seventy-four opportunities. The volatility-premium gate
> cleared forty-eight. Eleven became trades. Every one of the other hundred and sixty-three is in
> the journal, with the gate that blocked it and its numbers.

### 1:50 — S5 · Discipline, the risk officer  (58 words · ~23 s)

> And the language model can never make this worse. The final size is one line — the smaller of the
> Desk Head's number and the risk officer's cap. It can trim, veto, or do nothing. The risk officer
> is pure code with no path in for a language model, and there is none where a broken model
> response means yes.

### 2:14 — S6 · Execution  (55 words · ~22 s)

> When the desk does trade, it goes out as one four-leg iron condor through the official Alpaca CLI
> — every trading call in the loop shells out to it. It comes back through a deterministic exit
> manager: fifty percent of the credit, two times the credit, or close on expiry day. A
> fifteen-minute cron, reconciling against Alpaca every tick.

### 2:38 — S7 · Results  (46 words · ~18 s)

> Held to expiry, the calibrated strategy made four hundred and eighty-four dollars over eleven
> backtested trades. That's not a forecast — four sessions of live P&L is a coin flip. What isn't a
> coin flip is an agent that documents every trade it didn't take.

### 3:01 — S8 · Close  (16 words · ~6 s)

> The journal is in the repo. Go check us against it.

---

## Total: ~438 words, ≈ 2:55 spoken

Full copy-paste, all eight blocks in order, short breath between:

> Most trading agents are a wrapper around a moving average. This one doesn't predict price. It
> sells overpriced volatility on three index ETFs — and most of the time, it decides not to. Every
> refusal is on the record, with a reason.
>
> The signal is deterministic Python. It reads the option surface, not the price chart. Implied
> volatility over a forecast of realized volatility gives the volatility risk premium — as a ratio,
> so it holds in any volatility regime. Dealer gamma, from open interest, says whether that premium
> is safe to sell, with a dead zone near zero because the data is two days old. Three gates. Any
> one of them stands the desk down, and each writes the number that said no.
>
> Only then does the language-model desk get a say. Four seats, all open models, all on Featherless.
> A three-model Quant ensemble votes, and needs a strict majority of the models we dispatched — not
> of the ones that answered. Bull and Bear argue direction, and an argument that doesn't cite real
> fields from the signal is thrown away. The Desk Head sizes the trade and writes a falsifiable
> prediction: a closing range, on a date.
>
> This is the part we're proudest of. Over sixty real sessions and three underlyings, the
> deterministic layer found a hundred and seventy-four opportunities. The volatility-premium gate
> cleared forty-eight. Eleven became trades. Every one of the other hundred and sixty-three is in
> the journal, with the gate that blocked it and its numbers.
>
> And the language model can never make this worse. The final size is one line — the smaller of the
> Desk Head's number and the risk officer's cap. It can trim, veto, or do nothing. The risk officer
> is pure code with no path in for a language model, and there is none where a broken model
> response means yes.
>
> When the desk does trade, it goes out as one four-leg iron condor through the official Alpaca CLI
> — every trading call in the loop shells out to it. It comes back through a deterministic exit
> manager: fifty percent of the credit, two times the credit, or close on expiry day. A
> fifteen-minute cron, reconciling against Alpaca every tick.
>
> Held to expiry, the calibrated strategy made four hundred and eighty-four dollars over eleven
> backtested trades. That's not a forecast — four sessions of live P&L is a coin flip. What isn't a
> coin flip is an agent that documents every trade it didn't take.
>
> The journal is in the repo. Go check us against it.

---

## Thursday 3 Sep — the live re-render

1. `src/data.ts` → `RESULTS.mode = 'live'`, fill `RESULTS.live` from `data/journal.jsonl` and
   `data/equity.csv`. **Also write `RESULTS.live.verdict`** — one sentence, now rendered on
   screen in S7 (it wasn't before; the live branch used to show only numbers). Two drafts are
   in the comment right above `RESULTS` in `data.ts` — pick the one matching the real outcome
   (0 trades vs ≥1) and adjust the specifics, don't paste it verbatim.
2. Replace the **S7 block** above with the live version, e.g.:
   > "Over the four competition sessions the desk opened *N* trades and stood down *M* times, each
   > with a logged reason. It ended the window at *X* dollars. The prediction ledger: *k* of *n*
   > theses resolved correct. Four sessions is a coin flip — the record of the non-trades is not."
   If it lands on zero trades: say that plainly and say why, in one sentence — "dealer gamma
   stayed negative on all three names almost the entire window" is the honest reason as of
   2 Sep, not a excuse invented after the fact. Check `data/journal.jsonl` for the real gex_norm
   pattern across all four sessions before writing this — don't assume it stayed the same as
   Wed.
3. `npm run render`, re-cut the S7 audio only.

### Also real, already in the repo: the shadow debate

If GEX never clears, the debate never runs against a real opening (`debate.review_open` fires
only when `sell_premium` is true — see `agent/desk.py:219`). Since 1 Sep the desk runs it anyway
in **observation-only mode** whenever VRP is rich but GEX vetoes (`agent/desk.py:_maybe_shadow_debate`,
merged #50) — a real transcript against real Featherless models and real market data, `shadow:
true` in the journal, structurally incapable of opening a position. First one fired 2 Sep on
SPY: 2/3 quant confirm, Bull and Bear genuinely disagree, Desk Head overrules the quant majority
and vetoes. It's the source for `assets/gif-debate.gif` (see `assets/GIFS.md`) and worth a line
in the S7 verdict if the competition window ends at zero trades — it is direct evidence the desk
was never idle, whatever the equity curve says.
