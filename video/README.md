# video/ — submission presentation video (Remotion)

Programmatic presentation video for the hackathon submission. **Rendered without audio** — the
narration (`NARRATION.md`) is run through a text-to-speech and laid under the video separately.

## Run

```bash
cd video
npm install
npm run studio      # preview at localhost:3000
npm run render      # -> out/iv-desk-presentation.mp4  (1920x1080, ~3:12, no audio)
npm run gifs        # -> out/gif{1,2,3}-*.mp4, the README GIF sources (see assets/GIFS.md)
```

## What's where

| File | |
|---|---|
| `src/data.ts` | **Every number and string the video shows.** Locked live 3 Sep after the close. |
| `src/gifData.ts` | Real data for the three README GIFs — separate from `data.ts`, refreshable any time. |
| `src/Root.tsx` | The composition — chains the eight scenes via `<TransitionSeries>`, plus the three standalone GIF compositions. |
| `src/scenes/S1..S8` | Hook · Signal · Desk · Discipline (funnel) · Risk · Execution · Results · Close. |
| `src/gifs/G1..G3` | Stand-down · shadow debate · session summary — the README GIF compositions. |
| `src/theme.ts` | Palette + fonts — matches `dashboard/index.html` and `docs/internal/estado.html`. |
| `NARRATION.md` | The English script for the TTS, with per-scene timestamps. |

## Data provenance (nothing is invented)

- Funnel / 11 trades / +$484 → `backtest/RESULTS.md` (60 real Alpaca sessions, calibrated config).
- Debate transcript (Quant 3/3, Desk Head thesis + prediction) → a real run against Featherless.
- Risk gates → `agent/config.py` + `agent/risk.py`. The clamp line → `agent/debate.py`.
- S7 Results → the real competition outcome, `data/journal.jsonl` + `data/equity.csv`: 1 trade
  (QQQ iron condor), 1 win, ending equity $100,318.85, 295 documented stand-downs.

## Narration — where it stands

`NARRATION.md` carries the full 8-scene script, ~440 words / ~2:56 spoken inside the ~3:12 video.
S7 was rewritten 3 Sep with the real result; S1-S6 and S8 are unchanged from the original cut and
still accurate. Generating and muxing the new narration audio is a manual step (ElevenLabs, same
voice/settings as `video/out/*.mp3`'s filename) — not automated here, see `NARRATION.md`'s
Thursday section for the exact reference settings.
