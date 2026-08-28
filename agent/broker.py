"""Thin REST client for the Alpaca paper Trading API. No SDK — full control over mleg orders.

All endpoints proven in probes/RESULTS.md.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://paper-api.alpaca.markets/v2"
_HEADERS = {
    "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY", ""),
    "APCA-API-SECRET-KEY": os.environ.get("ALPACA_SECRET_KEY", ""),
    "Content-Type": "application/json",
}
_client = httpx.Client(base_url=_BASE, headers=_HEADERS, timeout=15.0)


def _get(path: str, **params: Any) -> Any:
    r = _client.get(path, params={k: v for k, v in params.items() if v is not None})
    r.raise_for_status()
    return r.json()


def account() -> dict:
    return _get("/account")


def clock() -> dict:
    return _get("/clock")


def positions() -> list[dict]:
    return _get("/positions")


def orders(status: str = "open", limit: int = 100, nested: bool = True) -> list[dict]:
    return _get("/orders", status=status, limit=limit, nested=str(nested).lower())


def option_contracts(
    underlying: str,
    expiration_date: str | None = None,
    expiration_date_gte: str | None = None,
    expiration_date_lte: str | None = None,
    strike_gte: float | None = None,
    strike_lte: float | None = None,
    type_: str | None = None,
    limit: int = 1000,
) -> list[dict]:
    """`/options/contracts` — the only place open_interest lives. Paginates via page_token."""
    out: list[dict] = []
    token: str | None = None
    while True:
        page = _get(
            "/options/contracts",
            underlying_symbols=underlying,
            expiration_date=expiration_date,
            expiration_date_gte=expiration_date_gte,
            expiration_date_lte=expiration_date_lte,
            strike_price_gte=strike_gte,
            strike_price_lte=strike_lte,
            type=type_,
            limit=limit,
            page_token=token,
        )
        out.extend(page.get("option_contracts", []))
        token = page.get("next_page_token")
        if not token:
            return out


def submit_mleg(legs: list[dict], qty: int, limit_price: float, tif: str = "day") -> dict:
    """legs: [{symbol, side: buy|sell, ratio_qty, position_intent}]. limit_price positive.

    Direction (debit vs credit) is inferred by Alpaca from the legs. For a net-credit structure
    the fill happens when the market credit >= limit_price. See RESULTS.md open item — verify sign.
    """
    body = {
        "order_class": "mleg",
        "qty": str(qty),
        "type": "limit",
        "time_in_force": tif,
        "limit_price": f"{limit_price:.2f}",
        "legs": legs,
    }
    r = _client.post("/orders", json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"mleg rejected {r.status_code}: {r.text}")
    return r.json()


def replace_order(order_id: str, limit_price: float) -> dict:
    r = _client.patch(f"/orders/{order_id}", json={"limit_price": f"{limit_price:.2f}"})
    r.raise_for_status()
    return r.json()


def cancel_order(order_id: str) -> None:
    _client.delete(f"/orders/{order_id}")


def cancel_all() -> None:
    _client.delete("/orders")
