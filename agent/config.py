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
    # CALIBRATED 30 Aug against 60 real sessions x SPY/QQQ/IWM (backtest/RESULTS.md, issues
    # #6 #7 #10 #29 #30). The real tape's VRP is thin: IV/RV_hat median 0.90, p90 1.27. The
    # pre-audit config fired 0 trades in 174 underlying-sessions; vrp 1.15 + gex 0.10 fired
    # only 3. The sensitivity grid showed vrp 1.05 and a near-zero gex floor recover trades
    # with positive expectancy, so:
    vrp_ratio_min: float = 1.05      # sell premium only if ATM_IV / RV_hat >= this. 1.15 was
                                     # starving it (3 trades/174, -$35). The grid has a real
                                     # inflection here: 1.05 -> 11 trades/+$484, 1.00 -> 13/+$117
                                     # (the 1.00-1.05 trades are net losers). Still well above
                                     # the 0.90 median IV/RV of the real tape (#6).
    gex_min: float = 0.03            # dead-zone floor on |net/gross gamma notional|. 0.10 cost
                                     # 6 of 11 VRP survivors for no P&L gain; 0.0 is just the
                                     # bare sign (#10's complaint). 0.03 keeps the near-zero
                                     # flip-flop filter without the expensive threshold.
    fade_trend: bool = False         # False -> stand down in a trending tape (decision on #12).
                                     # True restores the old "sell into the move" behaviour;
                                     # one flag, so the reversal is a one-line change.

    # --- structure geometry -------------------------------------------------------------
    # For a condor, credit/width ~ 2 x the mean |delta| between the short and long strike
    # (desk.py charges the max loss of one side only), so the ratio *rises* as the width
    # narrows. That is why 0.33 x 4.0 was unreachable (#7): geometry, not vol. On the real
    # tape credit/width ran median 0.223 / max 0.280 at width 2/1 — so 0.20 is the honest
    # floor and anything above ~0.28 would gate out every real structure.
    short_delta: float = 0.18        # target short-strike delta. 0.25 barely moved P&L in the
                                     # grid and widens per-trade risk — kept conservative.
    width_spy: float = 2.0           # SPY and QQQ; both quote $1 strikes near the money
    width_iwm: float = 1.0
    min_credit_frac: float = 0.20    # credit / width floor (see above: real max was 0.28)
    take_profit_frac: float = 0.50   # close at 50% of max credit
    stop_multiple: float = 2.0       # close at 2x credit received
    # --- sizing: frequency over size (decision on #16, option c) --------------------------
    # 4 sessions is a variance lottery; we do not try to win the P&L axis. But a flat
    # $100k with zero trades scores 0 on P&L *and* leaves the other three axes (75%) with
    # nothing to show. So: keep the per-trade risk small and FLAT (no Mon->Tue ramp), and
    # be less selective — more small defined-risk trades => more debate transcripts, a
    # textured equity curve, downside still capped by max_portfolio_risk.
    risk_per_trade: float = 0.005    # fraction of NAV, held flat all week
    max_portfolio_risk: float = 0.10 # hard ceiling on Sum(max_loss) of open positions
    max_positions: int = 8           # was 6; let good days accumulate small positions
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
