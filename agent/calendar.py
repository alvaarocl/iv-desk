"""Static macro-event calendar for the competition window. All times US/Eastern.

High-impact only — these trigger the risk blackout (no new positions +/- BLACKOUT).

Verified 29 Aug 2026 against BEA / ISM / ADP / BLS release schedules (issue #17):
- PCE (July data) was released **Wed 26 Aug 08:30 ET** — before the P&L window (starts Mon 31 Aug),
  so it is not in the list. The next PCE is 30 Sep, after the window.
- ISM Manufacturing PMI publishes on the first business day of the month → **Tue 1 Sep 10:00 ET**.
- ADP National Employment Report → **Wed 2 Sep 08:15 ET** (the old entry had it on the 3rd).
- ISM Services PMI, third business day → **Thu 3 Sep 10:00 ET**.
- Weekly initial jobless claims every Thursday → **Thu 3 Sep 08:30 ET**.
- NFP / Employment Situation → **Fri 4 Sep 08:30 ET**. Outside the P&L window (Fri does not score)
  and competition trades expire <= 3 Sep, but kept as a backstop.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# (date, HH:MM ET, label)
EVENTS = [
    ("2026-09-01", "10:00", "ISM Manufacturing PMI"),
    ("2026-09-02", "08:15", "ADP employment"),
    ("2026-09-03", "08:30", "Initial jobless claims"),
    ("2026-09-03", "10:00", "ISM Services PMI"),
    ("2026-09-04", "08:30", "NFP / Employment Situation"),   # outside the P&L window; backstop
]

# +/- window around each event in which no new position may open. 2h is deliberately
# conservative: with the 10:00 ISM prints this blacks out new opens until ~12:00 ET on 1 and
# 3 Sep. Narrow it here if the backtest shows the lost morning costs too much (issue #16).
BLACKOUT = timedelta(hours=2)


def in_event_blackout(now_et: datetime) -> bool:
    now = now_et if now_et.tzinfo else now_et.replace(tzinfo=ET)
    for d, hm, _ in EVENTS:
        h, m = map(int, hm.split(":"))
        t = datetime.fromisoformat(d).replace(hour=h, minute=m, tzinfo=ET)
        if abs(now - t) <= BLACKOUT:
            return True
    return False


def next_event(now_et: datetime) -> tuple[datetime, str] | None:
    now = now_et if now_et.tzinfo else now_et.replace(tzinfo=ET)
    upcoming = []
    for d, hm, label in EVENTS:
        h, m = map(int, hm.split(":"))
        t = datetime.fromisoformat(d).replace(hour=h, minute=m, tzinfo=ET)
        if t >= now:
            upcoming.append((t, label))
    return min(upcoming) if upcoming else None
