# video/ — submission presentation video (Remotion)

Programmatic presentation video for the hackathon submission. **Rendered without audio** — the
narration (`NARRATION.md`) is run through a text-to-speech and laid under the video separately.

## Run

```bash
cd video
npm install
npm run studio      # preview at localhost:3000
npm run render      # -> out/iv-desk-presentation.mp4  (1920x1080, ~2:52, no audio)
```

## What's where

| File | |
|---|---|
| `src/data.ts` | **Every number and string the video shows.** The only file to edit on Thu 3 Sep. |
| `src/Root.tsx` | The composition — chains the seven scenes via `<Series>`. |
| `src/scenes/S1..S7` | Hook · Signal · Desk · Discipline · Execution · Results · Close. |
| `src/theme.ts` | Palette + fonts — matches `dashboard/index.html` and `docs/internal/estado.html`. |
| `NARRATION.md` | The English script for the TTS, with per-scene timestamps. |

## Data provenance (nothing is invented)

- Funnel / 11 trades / +$484 → `backtest/RESULTS.md` (60 real Alpaca sessions, calibrated config).
- Debate transcript (Quant 3/3, Desk Head thesis + prediction) → a real run against Featherless.
- Risk gates → `agent/config.py` + `agent/risk.py`. The clamp line → `agent/debate.py`.

## Thursday re-render (live results)

`src/data.ts` → set `RESULTS.mode = 'live'`, fill `RESULTS.live` from `data/journal.jsonl` and
`data/equity.csv`, swap the S6 narration (see `NARRATION.md`), `npm run render`.
