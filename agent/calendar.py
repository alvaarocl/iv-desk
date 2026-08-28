"""Static macro-event calendar for the competition window. VERIFY each time/date on Day 0
against a real economic calendar (e.g. tradingeconomics, forexfactory). All times US/Eastern.

High-impact only — these trigger the risk blackout (no new positions +/- 2h).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# (date, HH:MM ET, label) — CONFIRM before relying on these.
EVENTS = [
    ("2026-08-28", "08:30", "PCE price index"),
    ("2026-09-01", "10:00", "ISM Manufacturing PMI"),
    ("2026-09-03", "08:15", "ADP employment"),
    ("2026-09-03", "10:00", "ISM Services PMI"),
    ("2026-09-04", "08:30", "NFP / jobs report"),      # final session — critical
]

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
