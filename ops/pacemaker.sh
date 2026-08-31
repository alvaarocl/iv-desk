#!/usr/bin/env bash
# Pacemaker — external tick source for the desk loop.
#
# WHY THIS EXISTS. On Mon 31 Aug the scheduled workflow fired 1 run out of ~27
# (`gh api runs?created=2026-08-31` -> total_count: 1). GitHub's cron is best-effort on every
# tier and is documented as such; a 4% delivery rate is not something the loop can be hardened
# against from the inside. So the cron stays as a backstop and this drives the same, already
# tested workflow from outside.
#
# WHAT IT DELIBERATELY DOES NOT DO. It does not pass `-f mode`. Since the `inherit` fix, a bare
# dispatch falls through to the DESK_MODE repo variable, which keeps the variable as the single
# source of truth and means `gh variable set DESK_MODE exits_only` — the documented kill switch —
# reaches pacemaker-driven runs on the next tick. Hard-coding `-f mode=live` here would re-arm
# live every 15 minutes and silently defeat that.
#
# It also offsets from the cron's :00/:15/:30/:45 to :07/:22/:37/:52. `_client_order_id`
# (execution.py) has minute granularity, so two runs landing in the same wall minute would collide
# and the second would be recorded as a duplicate stub that overwrites the real entry_order_id.
#
# Usage:  bash ops/pacemaker.sh            # runs until Ctrl-C
#         bash ops/pacemaker.sh --once     # single dispatch, for testing
set -uo pipefail

REPO="${GH_REPO:-alvaarocl/iv-desk}"
OFFSET_MIN=7          # minutes past each quarter hour
INTERVAL=900          # 15 min

dispatch() {
  local mode
  mode=$(gh api "repos/$REPO/actions/variables/DESK_MODE" -q .value 2>/dev/null || echo "?")
  if gh workflow run desk.yml -R "$REPO" 2>/dev/null; then
    echo "$(date -Is)  dispatched  (DESK_MODE=$mode)"
  else
    echo "$(date -Is)  !!! DISPATCH FAILED — check: gh auth status" >&2
  fi
}

trap 'echo; echo "$(date -Is)  pacemaker stopped."; exit 0' INT TERM

if [ "${1:-}" = "--once" ]; then dispatch; exit 0; fi

echo "Pacemaker -> $REPO, every ${INTERVAL}s at :$(printf %02d $OFFSET_MIN) past the quarter."
echo "Kill switch stays: gh variable set DESK_MODE --body exits_only   (takes effect next tick)"
echo "Ctrl-C to stop."

# Align to the next :07/:22/:37/:52 so we never share a wall minute with the cron.
now_m=$(date +%-M); now_s=$(date +%-S)
next=$(( (((now_m / 15) + 1) * 15 + OFFSET_MIN) % 60 ))
wait_s=$(( ((next - now_m + 60) % 60) * 60 - now_s ))
[ "$wait_s" -gt 0 ] && { echo "aligning: sleeping ${wait_s}s until :$(printf %02d $next)"; sleep "$wait_s"; }

while true; do
  dispatch
  sleep "$INTERVAL"
done
