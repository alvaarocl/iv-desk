"""The macro-event blackout is asymmetric (issue #33).

Wide before the print (opening premium into an unresolved number is the risk the gate exists
for), narrow after it (the IV crush is the best entry of the day, not a thing to sit out).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agent.calendar import BLACKOUT_AFTER, BLACKOUT_BEFORE, in_event_blackout

ET = ZoneInfo("America/New_York")
ISM = datetime(2026, 9, 1, 10, 0, tzinfo=ET)  # ISM Manufacturing, a scored session


def test_wide_before_the_print():
    assert in_event_blackout(ISM - timedelta(minutes=90))
    assert in_event_blackout(ISM - timedelta(minutes=1))


def test_narrow_after_the_print():
    assert in_event_blackout(ISM + timedelta(minutes=30)), "aún dentro de la ventana corta"
    assert not in_event_blackout(ISM + timedelta(minutes=50)), "pasada la ventana, se puede operar"


def test_the_open_reopens_before_noon():
    """The regression this fixes: +/-2h blocked 09:30-12:00 ET on two of four scored sessions."""
    assert in_event_blackout(datetime(2026, 9, 1, 9, 30, tzinfo=ET)), "la apertura sigue bloqueada"
    assert not in_event_blackout(datetime(2026, 9, 1, 11, 0, tzinfo=ET)), "a las 11:00 ya se opera"


def test_asymmetry_is_the_point():
    assert BLACKOUT_BEFORE > BLACKOUT_AFTER


def test_a_clean_session_is_never_blacked_out():
    for hour in range(10, 16):
        assert not in_event_blackout(datetime(2026, 9, 2, hour, 0, tzinfo=ET))
