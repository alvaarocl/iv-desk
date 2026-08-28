"""Alpaca market data — option chain snapshots (greeks + IV) and stock bars for the RV forecast."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://data.alpaca.markets"
_HEADERS = {
    "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY", ""),
    "APCA-API-SECRET-KEY": os.environ.get("ALPACA_SECRET_KEY", ""),
}
_client = httpx.Client(base_url=_BASE, headers=_HEADERS, timeout=20.0)
OPTION_FEED = "indicative"  # OPRA is a paid add-on; indicative measured ~2s fresh


def _get(path: str, **params: Any) -> Any:
    r = _client.get(path, params={k: v for k, v in params.items() if v is not None})
    r.raise_for_status()
    return r.json()


def stock_price(symbol: str) -> float:
    return _get(f"/v2/stocks/{symbol}/trades/latest")["trade"]["p"]


def daily_bars(symbol: str, lookback_days: int = 40) -> list[dict]:
    start = (date.today() - timedelta(days=lookback_days * 2)).isoformat()
    return _get(
        f"/v2/stocks/{symbol}/bars", timeframe="1Day", start=start, limit=lookback_days + 5, feed="sip"
    ).get("bars", [])


def option_chain_snapshot(
    underlying: str,
    expiration_date: str | None = None,
    strike_gte: float | None = None,
    strike_lte: float | None = None,
) -> dict[str, dict]:
    """{occ_symbol: {greeks, impliedVolatility, latestQuote, latestTrade, dailyBar, ...}}."""
    out: dict[str, dict] = {}
    token: str | None = None
    while True:
        page = _get(
            f"/v1beta1/options/snapshots/{underlying}",
            feed=OPTION_FEED,
            limit=1000,
            expiration_date=expiration_date,
            strike_price_gte=strike_gte,
            strike_price_lte=strike_lte,
            page_token=token,
        )
        snaps = page.get("snapshots", {})
        out.update(snaps)
        token = page.get("next_page_token")
        if not token or not snaps:
            return out


def option_daily_bars(symbols: list[str], start: str, limit: int = 100) -> dict[str, list[dict]]:
    return _get(
        "/v1beta1/options/bars", symbols=",".join(symbols), timeframe="1Day", start=start, limit=limit
    ).get("bars", {})


def parse_occ(symbol: str) -> tuple[str, date, str, float]:
    """SPY260904C00785000 -> ('SPY', date(2026,9,4), 'C', 785.0)."""
    i = 0
    while symbol[i].isalpha():
        i += 1
    root, body = symbol[:i], symbol[i:]
    yy, mm, dd = int(body[0:2]), int(body[2:4]), int(body[4:6])
    cp = body[6]
    strike = int(body[7:]) / 1000
    return root, date(2000 + yy, mm, dd), cp, strike
