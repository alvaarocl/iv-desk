"""Macro-event blackout — verified dates for the competition window (issue #17)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from agent import calendar as cal

ET = ZoneInfo("America/New_York")


def _et(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=ET)


def test_monday_open_is_clear():
    # PCE (26 Aug) is out of the list; nothing blacks out the 31 Aug 09:30 open.
    assert cal.in_event_blackout(_et(2026, 8, 31, 9, 30)) is False


def test_ism_manufacturing_blacks_out_tuesday_late_morning():
    assert cal.in_event_blackout(_et(2026, 9, 1, 10, 30)) is True
    assert cal.in_event_blackout(_et(2026, 9, 1, 13, 0)) is False   # cleared by ~12:00


def test_adp_is_wednesday_not_thursday():
    assert cal.in_event_blackout(_et(2026, 9, 2, 8, 15)) is True
    # Wednesday afternoon is clean once ADP clears
    assert cal.in_event_blackout(_et(2026, 9, 2, 12, 0)) is False


def test_thursday_morning_blacks_out_for_claims_and_ism_services():
    assert cal.in_event_blackout(_et(2026, 9, 3, 8, 30)) is True
    assert cal.in_event_blackout(_et(2026, 9, 3, 10, 0)) is True


def test_next_event_ordering():
    nxt = cal.next_event(_et(2026, 8, 31, 12, 0))
    assert nxt is not None and nxt[1] == "ISM Manufacturing PMI"
