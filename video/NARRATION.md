# Narration — IV Desk presentation video

**For the TTS.** English. The silent video is `out/iv-desk-presentation.mp4` (1920×1080, ~2:52).
Generate the voice track, then lay it under the video in any editor.

- Voice: neutral, unhurried, a little dry. Roughly **150 words per minute**.
- Leave **~0.6 s of silence** between segments (they line up with scene cuts).
- Total spoken ≈ 2:35, which fits the 2:52 video with breathing room.
- If a segment runs long against its scene, trim the *scene* duration in
  `video/src/data.ts` → `SCENES` and re-render — don't rush the read.

Segment timings below are where each scene *starts*. Start speaking ~1 s after the cut.

---

## 0:00 — S1 · Hook  (~40 words)

> Most trading agents are a multi-agent wrapper around a moving average. This one doesn't predict
> price at all. It sells overpriced volatility on three index ETFs — and most of the time, it
> decides not to. Every refusal is on the record, with a reason.

## 0:17 — S2 · The signal  (~90 words)

> The signal is deterministic Python, and it reads the option surface, not the price chart.
> Implied volatility, divided by a forecast of realized volatility, gives the volatility risk
> premium — a ratio, so it means the same thing in a six-percent tape and a twenty-percent one.
> Dealer gamma, computed from open interest, decides whether that premium is safe to sell — with a
> dead zone around zero, because the data is two days old. Three gates. Any one of them stands the
> desk down, and each writes the number that said no.

## 0:50 — S3 · The desk  (~80 words)

> Only then does the language-model desk get a say. Four seats, all open models, all on Featherless.
> A three-model Quant ensemble votes, and needs a strict majority of the models we dispatched — not
> of the ones that answered. Bull and Bear argue direction, and an argument that doesn't cite real
> fields from the signal is thrown away. The Desk Head sizes the trade and writes a falsifiable
> prediction: a closing range, on a date.

## 1:22 — S4 · Discipline  (~105 words)

> This is the part we're proudest of. Across sixty real sessions and three underlyings, the
> deterministic layer found a hundred and seventy-four opportunities. The volatility-premium gate
> cleared forty-eight of them. Eleven became trades. Every one of the other hundred and sixty-three
> is in the journal, with the exact gate that blocked it and the numbers behind it.
>
> And the language model can never make this worse. The final size is one line — the minimum of
> what the Desk Head asked for and the cap the risk officer already set. It can trim, veto, or do
> nothing. There is no path where a broken model response means yes.

## 2:02 — S5 · Execution  (~58 words)

> When the desk does trade, it goes out as a single four-leg iron condor through the official
> Alpaca CLI — every trading call in the loop shells out to it. It comes back through a
> deterministic exit manager: fifty percent of the credit, two times the credit, or close on
> expiry day. It runs itself on a fifteen-minute cron, reconciling against Alpaca on every tick.

## 2:25 — S6 · Results  (~46 words)

> Held to expiry, the calibrated strategy made four hundred and eighty-four dollars over eleven
> backtested trades. That's not a forecast — four sessions of live P&L is a coin flip. What isn't a
> coin flip is an agent that documents every trade it didn't take.

## 2:45 — S7 · Close  (~12 words)

> The journal is in the repo. Go check us against it.

---

## Thursday 3 Sep — the live re-render

When the P&L window closes:

1. In `video/src/data.ts`, set `RESULTS.mode = 'live'` and fill the `RESULTS.live` block from
   `data/journal.jsonl` / `data/equity.csv` (P&L, trades, win rate, stand-down count, predictions
   correct, and the equity curve as an array of NAV points).
2. Replace the S6 narration above with the live version, e.g.:
   > "Over the four competition sessions the desk opened *N* trades and stood down *M* times, each
   > with a logged reason. It ended the window at *X* dollars. The prediction ledger: *k* of *n*
   > theses resolved correct. Four sessions is a coin flip — the record of the non-trades is not."
3. `cd video && npm run render`. Re-cut the audio for S6 only.
