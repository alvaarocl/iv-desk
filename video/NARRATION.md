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

### 2:38 — S7 · Results  (48 words · ~19 s)

> Over four sessions, the desk opened one trade: a QQQ iron condor, cleared by every gate and a
> live debate. It closed inside every strike. Two hundred ninety-five other times, it looked and
> said no — logged, with a reason. Ending equity: one hundred thousand, three hundred nineteen
> dollars.

### 3:01 — S8 · Close  (16 words · ~6 s)

> The journal is in the repo. Go check us against it.

---

## Total: ~440 words, ≈ 2:56 spoken

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
> Over four sessions, the desk opened one trade: a QQQ iron condor, cleared by every gate and a
> live debate. It closed inside every strike. Two hundred ninety-five other times, it looked and
> said no — logged, with a reason. Ending equity: one hundred thousand, three hundred nineteen
> dollars.
>
> The journal is in the repo. Go check us against it.

---

## Thursday 3 Sep — done (kept for the record, not a to-do anymore)

`RESULTS.mode = 'live'` and `RESULTS.live` are filled in `src/data.ts`. The actual outcome:
**1 trade, 1 win.** QQQ iron condor, 8 contracts, cleared every gate and a real (non-shadow)
debate, closed inside the strikes. Ending equity $100,318.85 (+$318.85). 295 documented
stand-downs across the week. The S7 block above already carries this — nothing left to swap in.

Next step is yours: generate the new S7 audio in ElevenLabs (same voice/settings as the existing
track — see the filename in `video/out/`: Arabella, PVC, `sp100`, `s63`, `sb49`, `v3`), splice or
regenerate, remux with `video/out/iv-desk-presentation.mp4` (re-rendered silent, S1-S6/S8 audio
unchanged from the original track), export to `video/out/IVDESK-UC3M.mp4`.

### Also real, already in the repo: the shadow debate

If GEX never clears, the debate never runs against a real opening (`debate.review_open` fires
only when `sell_premium` is true — see `agent/desk.py:219`). Since 1 Sep the desk runs it anyway
in **observation-only mode** whenever VRP is rich but GEX vetoes (`agent/desk.py:_maybe_shadow_debate`,
merged #50) — a real transcript against real Featherless models and real market data, `shadow:
true` in the journal, structurally incapable of opening a position. First one fired 2 Sep on
SPY: 2/3 quant confirm, Bull and Bear genuinely disagree, Desk Head overrules the quant majority
and vetoes. It's the source for `assets/gif-debate.gif` (see `assets/GIFS.md`). The window ended
with a real trade, so S7 didn't need this as its fallback story — but it's still evidence the desk
runs the mesa on more than the one signal that happened to clear every gate, and it's fair game
for S3 or a GIF callout if there's room.
