"""Execution — wraps the Alpaca CLI for orders, alpaca-py for data. Deterministic exit manager.

Owner: lane A. Depends on Day-0 probe 3 (does paper mleg take 4 legs?).
The trading loop shells out to the `alpaca` CLI so the production path is exactly what we demo.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


def cli(*args: str) -> dict:
    """Run `alpaca ...` and parse JSON stdout. Raises on non-zero exit."""
    proc = subprocess.run(["alpaca", *args], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def account() -> dict:
    return cli("account", "get")


def positions() -> list[dict]:
    return cli("position", "list").get("positions", [])  # adjust key to CLI output


def clock() -> dict:
    return cli("clock", "get")


@dataclass
class Leg:
    symbol: str
    side: str      # buy | sell
    ratio_qty: int = 1


def submit_mleg(legs: list[Leg], qty: int, limit_price: float, four_leg_ok: bool) -> list[dict]:
    """Submit an iron condor as one 4-leg order, or two verticals if probe 3 said 4-leg is rejected.

    TODO(lane A): build the exact `alpaca order create` invocation for mleg from probe-3 findings.
    """
    raise NotImplementedError


def fetch_market_data(underlying: str) -> dict:
    """Spot, daily OHLC history, option chain snapshot (greeks+IV), cached OI, VIX.

    TODO(lane A): implement with alpaca-py OptionHistoricalDataClient + StockHistoricalDataClient.
    GEX inputs (OI sweep) are cached in data/gex_cache.json and refreshed 2-3x/day, not every loop.
    """
    raise NotImplementedError


def manage_exits(open_positions: list[dict], params) -> list[dict]:
    """Deterministic, NO LLM. For each position:
      - close at take_profit_frac of max credit
      - close at stop_multiple x credit received, or if a short strike is breached
      - close by 15:45 ET on expiration day
    Returns the close orders to send.
    """
    raise NotImplementedError
