# Runbook — live sessions

> Covers the **cron contingency** and the **kill switch** (issue #23). The full per-session
> operating checklist — startup verification, what to watch each invocation, incident decision
> tree — is issue #24 (lane/entrega) and gets appended here.

All times below in **ET**. Session = 09:30–16:00 ET (15:30–22:00 CEST). P&L window: Mon 31 Aug
09:30 ET → equity snapshot EOD Thu 3 Sep.

---

## The loop tolerates a missed run — by design

GitHub Actions `schedule:` is best-effort and can be delayed 5–30 min or skipped entirely under
load. The loop is built so a single skipped invocation is not fatal:

- **On every start it reconciles against Alpaca** (`ex.reconcile`): pending entries are resolved
  to filled/cancelled from the broker, pending exits are checked, and unexpected equity positions
  (early assignment) flip the desk to exits-only. The local `data/trades.jsonl` is a journal, not
  the source of truth.
- **The expiry close fires on any run at/after 15:30 ET** on expiration day, not a single
  15:45 run. A skipped 15:45 tick no longer means a position rides into expiration.
- `client_order_id` is deterministic per trade intent, so a re-run or manual dispatch cannot
  double-submit.

## If a run is skipped

| When | Risk | Action |
|---|---|---|
| **Near the open (09:30–10:00)** | A planned entry is delayed. Low urgency — entries are not time-critical. | Nothing. The next tick opens it if the signal still holds. |
| **Mid-session** | A take-profit or stop that should have triggered is late. | Check the last `portfolio` / `exit` event timestamp in `data/journal.jsonl`. If the last run is >30 min old and market is open, trigger a manual run (below). |
| **15:30–16:00 ET on an expiration day** | A position could expire unmanaged → pin risk, assignment, ~$77k notional in shares. | **Trigger a manual run immediately.** If Actions is unresponsive, run the loop locally in `exits_only` (below) or close the position by hand in the Alpaca dashboard. |

## Manual run

GitHub → **Actions** → *IV Desk loop* → **Run workflow** → pick `mode`:

- `dry_run` — safe, places nothing.
- `live` — full loop, opens and manages.
- `exits_only` — **kill switch**: reconciles and manages the open book on the live account, opens
  nothing.

## Kill switch — stop opening new positions

Fastest (no code, ~30 s): GitHub → **Settings** → **Secrets and variables** → **Actions** →
**Variables** → set `DESK_MODE` = `exits_only`. Takes effect on the next scheduled tick (≤15 min).
To act now, also trigger a manual `exits_only` run.

To stop **everything** including exits: disable the workflow (Actions → *IV Desk loop* → ⋯ →
**Disable workflow**) and manage positions by hand.

## Local run against the live account (last resort)

Only if GitHub Actions is down during a critical window.

```bash
# in the repo root, with the COMPETITION account keys exported (never store them in .env):
export ALPACA_API_KEY=...  ALPACA_SECRET_KEY=...  ALPACA_ACCOUNT_ID=PA39HSCQE8S3
export ALPACA_CLI_BIN="$HOME/.local/bin/alpaca"   # or wherever the CLI lives
export MSYS_NO_PATHCONV=1                          # Git Bash only
DESK_MODE=exits_only uv run python -m agent.desk
```

The account guard refuses to run `live`/`exits_only` unless the credentials resolve to
`PA39HSCQE8S3`, and refuses to touch `PA39HSCQE8S3` at all before Mon 31 Aug 09:30 ET.

---

## Account rules (never break these)

| Account | ID | Use | Keys live in |
|---|---|---|---|
| Paper Trading (testing) | `PA3TQHQKM5AD` | all dev, dry-run, fill tests | local `.env` only |
| PAPER UC3M (competition) | `PA39HSCQE8S3` | agent orders in the P&L window only — judged equity | GitHub Actions secrets only |

- No manual order on `PA39HSCQE8S3`, ever. Its history must be 100% agent-driven.
- Competition keys never go in the local `.env`.
- `ALPACA_ACCOUNT_ID` is **always** the competition account id (`PA39HSCQE8S3`), everywhere —
  it is what the guard checks and what goes in the submission.
