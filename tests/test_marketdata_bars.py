"""daily_bars must return the NEWEST bars, not the oldest (issue #26).

The old version asked for a ~2x-wide window with limit=lookback+5. Alpaca returns bars
ascending from `start`, so `limit` truncated the newest ones and the RV forecast was
computed on a series ending weeks earlier — silently, with a plausible-looking number.
"""

from agent import marketdata as md


def _fake_api(total_sessions: int, page_size: int = 3):
    """Ascending bars split across pages, exactly like the real endpoint."""
    all_bars = [{"t": f"2026-01-{i + 1:02d}", "c": 100.0 + i} for i in range(total_sessions)]
    calls: list[dict] = []

    def _get(path, **params):
        calls.append(params)
        start = int(params.get("page_token") or 0)
        chunk = all_bars[start:start + page_size]
        nxt = start + page_size
        return {"bars": chunk, "next_page_token": str(nxt) if nxt < len(all_bars) else None}

    return _get, all_bars, calls


def test_returns_the_most_recent_bars(monkeypatch):
    fake, all_bars, _ = _fake_api(total_sessions=78)
    monkeypatch.setattr(md, "_get", fake)

    bars = md.daily_bars("SPY", 55)

    assert len(bars) == 55
    assert bars[-1] == all_bars[-1], "la última barra debe ser la MÁS RECIENTE"
    assert bars[0] == all_bars[-55], "la ventana debe ser la cola, no la cabeza"


def test_paginates_instead_of_truncating(monkeypatch):
    """The regression: one call with a small limit returned the oldest page."""
    fake, _, calls = _fake_api(total_sessions=78)
    monkeypatch.setattr(md, "_get", fake)

    md.daily_bars("SPY", 55)

    assert len(calls) > 1, "debe paginar"
    assert all(c["limit"] > 55 for c in calls), "limit no debe recortar la ventana"


def test_short_history_returns_what_exists(monkeypatch):
    fake, all_bars, _ = _fake_api(total_sessions=12)
    monkeypatch.setattr(md, "_get", fake)

    bars = md.daily_bars("SPY", 55)

    assert bars == all_bars
