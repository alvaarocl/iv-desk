"""Central config. Everything tunable lives here; nightly reflection rewrites `params.json`."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PARAMS_FILE = DATA / "params.json"

UNIVERSE = ["SPY", "QQQ", "IWM"]


@dataclass
class Params:
    vrp_min: float = 0.03            # min IV - RV_hat (vol points) to sell premium
    short_delta: float = 0.18        # target short-strike delta
    width_spy: float = 4.0
    width_iwm: float = 2.0
    min_credit_frac: float = 0.33    # credit / width floor
    take_profit_frac: float = 0.50   # close at 50% of max credit
    stop_multiple: float = 2.0       # close at 2x credit received
    risk_per_trade: float = 0.005    # fraction of NAV; ramps to 0.01-0.02
    max_portfolio_risk: float = 0.10
    max_positions: int = 6
    max_net_delta: float = 0.30      # normalized to NAV/100k
    daily_loss_breaker: float = 0.03
    dd_throttle: float = 0.08
    dd_halt: float = 0.12
    gex_band: float = 0.05           # +/- fraction of spot for GEX strike window
    satellite_frac: float = 0.15     # max share of risk budget for directional debit spreads
    no_new_0dte_after_et: str = "14:00"

    @classmethod
    def load(cls) -> Params:
        if PARAMS_FILE.exists():
            return cls(**{**asdict(cls()), **json.loads(PARAMS_FILE.read_text())})
        return cls()

    def save(self) -> None:
        DATA.mkdir(exist_ok=True)
        PARAMS_FILE.write_text(json.dumps(asdict(self), indent=2))


ALPACA_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET = os.environ.get("ALPACA_SECRET_KEY", "")
FEATHERLESS_MODELS = [m for m in os.environ.get("FEATHERLESS_MODELS", "").split(",") if m]


def desk_mode() -> str:
    """dry_run | live — read fresh each loop so workflow_dispatch can flip it."""
    return os.environ.get("DESK_MODE", "dry_run").strip().lower()
