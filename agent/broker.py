"""Trading API client routed through the **Alpaca CLI** (`alpacahq/cli`).

The hackathon rules require the Trading API *plus* the MCP server or the CLI, so every trading-API
call in this module shells out to `alpaca api ...`. Market-data reads stay on REST in
`marketdata.py` (explicitly allowed).

Conventions that cost us time to discover (see `docs/API-ALPACA.md`):

- `mleg` `limit_price` is **signed**: positive = debit (what we pay), negative = credit (what we
  want to collect). `submit_mleg` takes the signed value and refuses an unsigned guess.
- Orders are **asynchronous**. A 200 confirms receipt, not execution — always poll `get_order`
  before treating a position as open.
- The CLI flag is `--body` (not `--data`), and `alpaca api` paths must not be mangled by MSYS path
  conversion. `subprocess` passes argv directly, so that only affects manual Git Bash testing
  (export `MSYS_NO_PATHCONV=1` there).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any
from urllib.parse import urlencode

from dotenv import load_dotenv

load_dotenv()

CLI_BIN = os.environ.get("ALPACA_CLI_BIN", "alpaca")
CLI_TIMEOUT = int(os.environ.get("ALPACA_CLI_TIMEOUT", "45"))


class BrokerError(RuntimeError):
    """Any non-success response from the Trading API, or a CLI transport failure."""


def _cli(method: str, path: str, body: dict | None = None, query: dict | None = None) -> Any:
    """Run `alpaca api METHOD path` and return the decoded JSON body."""
    cmd = [CLI_BIN, "api", method, path, "--quiet"]
    if query:
        clean = {k: v for k, v in query.items() if v is not None}
        if clean:
            cmd += ["--query", urlencode(clean)]
    if body is not None:
        cmd += ["--body", json.dumps(body)]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT, check=False
        )
    except FileNotFoundError as exc:
        raise BrokerError(
            f"Alpaca CLI not found (looked for {CLI_BIN!r}). Install it or set ALPACA_CLI_BIN. "
            "Order placement must go through the CLI — see docs/API-ALPACA.md."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise BrokerError(f"alpaca CLI timed out after {CLI_TIMEOUT}s on {method} {path}") from exc

    out = (proc.stdout or "").strip()
    try:
        payload = json.loads(out) if out else None
    except json.JSONDecodeError:
        raise BrokerError(
            f"alpaca CLI returned non-JSON on {method} {path} (rc={proc.returncode}): "
            f"{out[:300] or (proc.stderr or '')[:300]}"
        ) from None

    # The CLI surfaces API errors as a JSON object carrying `error`/`status`, with a non-zero rc.
    if isinstance(payload, dict) and payload.get("error"):
        raise BrokerError(
            f"{method} {path} -> {payload.get('status', proc.returncode)}: {payload['error']}"
        )
    if proc.returncode != 0:
        raise BrokerError(
            f"alpaca CLI exited {proc.returncode} on {method} {path}: "
            f"{(proc.stderr or out)[:300]}"
        )
    return payload


# ---------- account / market ----------

def account() -> dict:
    return _cli("GET", "/v2/account")


def clock() -> dict:
    return _cli("GET", "/v2/clock")


def assert_account(expected_account_number: str, *, allow_when_blank: bool = True) -> dict:
    """Refuse to continue unless the credentials point at `expected_account_number`.

    The competition account (PAPER UC3M) and the testing account have separate key pairs, and
    trading the wrong one is unrecoverable: orders on the testing account do not score, and any
    manual order on the competition account pollutes a history that must be 100% agent-driven.
    """
    if not expected_account_number:
        if allow_when_blank:
            return account()
        raise BrokerError("No expected account number configured; refusing to trade.")
    acct = account()
    actual = acct.get("account_number")
    if actual != expected_account_number:
        raise BrokerError(
            f"ACCOUNT MISMATCH — credentials point at {actual!r} but this run expects "
            f"{expected_account_number!r}. Refusing to place any order."
        )
    return acct


# ---------- positions / orders ----------

def positions() -> list[dict]:
    return _cli("GET", "/v2/positions") or []


def orders(status: str = "open", limit: int = 100, nested: bool = True) -> list[dict]:
    return _cli(
        "GET", "/v2/orders",
        query={"status": status, "limit": limit, "nested": str(nested).lower()},
    ) or []


def get_order(order_id: str | None = None, client_order_id: str | None = None) -> dict | None:
    """Fetch one order by broker id or by our deterministic `client_order_id`.

    Returns None when the order does not exist — that is the normal answer for a
    `client_order_id` we have never submitted, so it must not raise.
    """
    try:
        if client_order_id:
            return _cli(
                "GET", "/v2/orders:by_client_order_id",
                query={"client_order_id": client_order_id},
            )
        if order_id:
            return _cli("GET", f"/v2/orders/{order_id}")
    except BrokerError as exc:
        if "404" in str(exc) or "not found" in str(exc).lower():
            return None
        raise
    return None


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
    """`/v2/options/contracts` — the only place `open_interest` lives. Paginates via page_token."""
    out: list[dict] = []
    token: str | None = None
    while True:
        page = _cli(
            "GET", "/v2/options/contracts",
            query={
                "underlying_symbols": underlying,
                "expiration_date": expiration_date,
                "expiration_date_gte": expiration_date_gte,
                "expiration_date_lte": expiration_date_lte,
                "strike_price_gte": strike_gte,
                "strike_price_lte": strike_lte,
                "type": type_,
                "limit": limit,
                "page_token": token,
            },
        ) or {}
        out.extend(page.get("option_contracts", []))
        token = page.get("next_page_token")
        if not token:
            return out


# ---------- order placement ----------

def submit_mleg(
    legs: list[dict],
    qty: int,
    limit_price: float,
    *,
    client_order_id: str | None = None,
    tif: str = "day",
) -> dict:
    """Submit a multi-leg order. `legs`: [{symbol, side, ratio_qty, position_intent}].

    `limit_price` is **signed and passed through verbatim**: negative to open a credit structure,
    positive to pay a debit. Passing the wrong sign turns a credit condor into "I'll pay up to X",
    which is instantly marketable — so we never take the absolute value here.
    """
    if limit_price == 0:
        raise ValueError("limit_price must be non-zero; sign carries credit/debit direction")
    body: dict[str, Any] = {
        "order_class": "mleg",
        "qty": str(qty),
        "type": "limit",
        "time_in_force": tif,
        "limit_price": f"{limit_price:.2f}",
        "legs": legs,
    }
    if client_order_id:
        body["client_order_id"] = client_order_id
    return _cli("POST", "/v2/orders", body=body)


def replace_order(order_id: str, limit_price: float) -> dict:
    return _cli("PATCH", f"/v2/orders/{order_id}", body={"limit_price": f"{limit_price:.2f}"})


def cancel_order(order_id: str) -> None:
    _cli("DELETE", f"/v2/orders/{order_id}")


def cancel_all() -> None:
    _cli("DELETE", "/v2/orders")
