# Narration — IV Desk presentation video

The silent video is `out/iv-desk-presentation.mp4` — **1920×1080, 2:54, no audio track**.
Run this script through a TTS, then lay the voice under the video.

- English. Neutral, unhurried, a little dry. **~150 words per minute.**
- Each block is timed to a scene. **Start speaking ~0.8 s after the scene cut** (let the visual
  land first) and aim to **finish ~1 s before the next cut**.
- Total spoken ≈ **2:43** inside the 2:54 video — ~11 s of breathing room spread across the 7 gaps.
- If a block still runs long against its scene, lengthen the *scene* in `src/data.ts` → `SCENES`
  and re-render. Don't rush the read.

Word counts are per block, for pacing.

---

### 0:00 — S1 · Hook  (start ~0:01 · 40 words · ~16 s)

> Most trading agents are a wrapper around a moving average. This one doesn't predict price. It
> sells overpriced volatility on three index ETFs — and most of the time, it decides not to. Every
> refusal is on the record, with a reason.

### 0:17 — S2 · The signal  (start ~0:18 · 78 words · ~31 s)

> The signal is deterministic Python. It reads the option surface, not the price chart. Implied
> volatility over a forecast of realized volatility gives the volatility risk premium — as a ratio,
> so it holds in any volatility regime. Dealer gamma, from open interest, says whether that premium
> is safe to sell, with a dead zone near zero because the data is two days old. Three gates. Any
> one of them stands the desk down, and each writes the number that said no.

### 0:50 — S3 · The desk  (start ~0:51 · 76 words · ~30 s)

> Only then does the language-model desk get a say. Four seats, all open models, all on Featherless.
> A three-model Quant ensemble votes, and needs a strict majority of the models we dispatched — not
> of the ones that answered. Bull and Bear argue direction, and an argument that doesn't cite real
> fields from the signal is thrown away. The Desk Head sizes the trade and writes a falsifiable
> prediction: a closing range, on a date.

### 1:22 — S4 · Discipline  (start ~1:23 · 95 words · ~38 s)

> This is the part we're proudest of. Over sixty real sessions and three underlyings, the
> deterministic layer found a hundred and seventy-four opportunities. The volatility-premium gate
> cleared forty-eight. Eleven became trades. Every one of the other hundred and sixty-three is in
> the journal, with the gate that blocked it and its numbers.
>
> And the language model can never make this worse. The final size is one line — the smaller of the
> Desk Head's number and the risk officer's cap. It can trim, veto, or do nothing. There is no path
> where a broken model response means yes.

### 2:02 — S5 · Execution  (start ~2:03 · 55 words · ~22 s)

> When the desk does trade, it goes out as one four-leg iron condor through the official Alpaca CLI
> — every trading call in the loop shells out to it. It comes back through a deterministic exit
> manager: fifty percent of the credit, two times the credit, or close on expiry day. A
> fifteen-minute cron, reconciling against Alpaca every tick.

### 2:25 — S6 · Results  (start ~2:26 · 46 words · ~18 s)

> Held to expiry, the calibrated strategy made four hundred and eighty-four dollars over eleven
> backtested trades. That's not a forecast — four sessions of live P&L is a coin flip. What isn't a
> coin flip is an agent that documents every trade it didn't take.

### 2:45 — S7 · Close  (start ~2:46 · 18 words · ~7 s)

> The journal is in the repo — every signal, every refusal, every trade. Go check us against it.

---

## Total: 408 words spoken, ≈ 2:43

Copy-paste, all seven blocks in order, with a short breath between:

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
> the journal, with the gate that blocked it and its numbers. And the language model can never make
> this worse. The final size is one line — the smaller of the Desk Head's number and the risk
> officer's cap. It can trim, veto, or do nothing. There is no path where a broken model response
> means yes.
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
> The journal is in the repo — every signal, every refusal, every trade. Go check us against it.

---

## Thursday 3 Sep — the live re-render

When the P&L window closes:

1. `src/data.ts` → `RESULTS.mode = 'live'`, fill `RESULTS.live` from `data/journal.jsonl` and
   `data/equity.csv` (P&L, trades, win rate, stand-down count, `predictionsCorrect`, and
   `equityCurve` as an array of NAV points).
2. Replace the **S6 block** above with the live version, e.g.:
   > "Over the four competition sessions the desk opened *N* trades and stood down *M* times, each
   > with a logged reason. It ended the window at *X* dollars. The prediction ledger: *k* of *n*
   > theses resolved correct. Four sessions is a coin flip — the record of the non-trades is not."
3. `npm run render`, re-cut the S6 audio only.
