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
    # --- signal gates -------------------------------------------------------------------
    # PROVISIONAL. Every number in this block is a defensible first guess, not a calibrated
    # value: the definitive set comes out of the backtest in issue #5. Change them there,
    # with evidence, not here.
    vrp_ratio_min: float = 1.15      # sell premium only if ATM_IV / RV_hat >= this (relative,
                                     # so it survives a 6% IV tape as well as a 20% one; #6)
    gex_min: float = 0.10            # |net/gross gamma notional| floor. Below it -> dead zone
                                     # -> regime "chop" -> no trade, instead of flip-flopping
                                     # on a T-2 open-interest reading (#10)
    fade_trend: bool = False         # False -> stand down in a trending tape (decision on #12).
                                     # True restores the old "sell into the move" behaviour;
                                     # one flag, so the reversal is a one-line change.

    # --- structure geometry -------------------------------------------------------------
    # PROVISIONAL, same caveat: pending the #5 backtest.
    # For a condor, credit/width ~ 2 x the mean |delta| between the short and long strike
    # (desk.py charges the max loss of one side only), so the ratio *rises* as the width
    # narrows. 4-point wings on SPY put the long leg near 5 delta and collect ~0.20 of width;
    # 2-point wings keep the long leg near 10 delta and land nearer 0.25-0.30. That is why
    # 0.33 x 4.0 was unreachable (#7): it was never a vol problem, it was geometry.
    # If cr_frac still falls short in the backtest, the next lever is short_delta (0.18 -> 0.22),
    # not the width.
    short_delta: float = 0.18        # target short-strike delta
    width_spy: float = 2.0           # SPY and QQQ; both quote $1 strikes near the money
    width_iwm: float = 1.0
    min_credit_frac: float = 0.20    # credit / width floor
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
    no_new_0dte_after_et: str = "14:00"
    # `satellite_frac` removed (#14): the directional debit-spread sleeve was never
    # implemented — signal.py set sell_premium=False on that branch, so desk.py skipped it
    # and _pick() had no case for it. Deleted rather than left as documentation of a
    # behaviour the code does not have.

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
    """dry_run | live | exits_only — read fresh each loop so workflow_dispatch can flip it.

    `exits_only` is the kill switch: reconcile and manage the open book against the live account,
    but open nothing new. Anything unrecognised falls back to the safe `dry_run`.
    """
    m = os.environ.get("DESK_MODE", "dry_run").strip().lower()
    return m if m in ("dry_run", "live", "exits_only") else "dry_run"
