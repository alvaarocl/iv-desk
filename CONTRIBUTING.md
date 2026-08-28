# Team workflow

Small team, 7 days. Keep it light but don't break `main` — the cron loop runs from `main`.

## Branches

- `main` — always deployable. The GitHub Actions loop trades from here.
- Work on `lane/a-signal`, `lane/b-dashboard`, `lane/c-content` (or short-lived `feat/*`).
- PR into `main`, quick review from the other person, squash-merge.

## Before pushing to main

```
uv run ruff check .
uv run pytest -q
uv run python -m agent.desk    # must run clean in dry_run mode
```

## Secrets — never commit

`.env` is gitignored. Real keys live in:
- local `.env` for each person
- GitHub repo **Settings → Secrets and variables → Actions**:
  `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ANTHROPIC_API_KEY`, `FEATHERLESS_API_KEY`
  and repo **Variables**: `FEATHERLESS_MODELS`, `DESK_MODE`

## Data files

`data/journal.jsonl` and `data/equity.csv` are committed by the bot on every loop.
Don't hand-edit them. If you hit a merge conflict there, take `origin/main`'s version.

## Repo visibility

**Private until submission.** Flip to public on **4 Sep** before submitting
(the rules require a public MIT repo). `gh repo edit --visibility public`.
