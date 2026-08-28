"""Main loop — invoked by cron (GitHub Actions) every 15 min during RTH.

Flow per invocation:
  1. exits first     — manage_exits() on the open book (deterministic)
  2. gates           — daily breaker / drawdown / blackout: if any trip, exits-only
  3. signal          — build_signal() per underlying (deterministic)
  4. open decision   — ONLY if a signal says sell_premium and slots are free:
                         run the debate (LLM), Risk Officer caps size, Desk Head commits
  5. journal         — append every decision + prediction to data/journal.jsonl

The loop is stateless: it reconstructs its view from the Alpaca account each run. Idempotent.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from . import execution as ex
from .config import UNIVERSE, DESK_MODE, Params
from .journal import append
from .signal import build_signal

ET = ZoneInfo("America/New_York")


def run_once() -> None:
    params = Params.load()
    now_et = datetime.now(ET)

    clk = ex.clock()
    if not clk.get("is_open"):
        append({"ts": now_et.isoformat(), "event": "market_closed", "skip": True})
        return

    book = ex.positions()

    # 1. exits always run
    for order in ex.manage_exits(book, params):
        append({"ts": now_et.isoformat(), "event": "exit", "order": order})

    # 2. portfolio-level gates → exits-only mode
    #    TODO(lane A): compute PortfolioState from account(); check daily breaker / dd_halt / blackout

    # 3 + 4. per-underlying signal → maybe open
    for u in UNIVERSE:
        md = ex.fetch_market_data(u)
        sig = build_signal(u, md, params)
        append({"ts": now_et.isoformat(), "event": "signal", **sig.__dict__})
        if not sig.sell_premium:
            continue
        # TODO(lane A): debate(sig, md) → proposal; risk.evaluate(...) → cap; commit if ok
        # respect DESK_MODE == "dry_run" (log only, place nothing)

    _ = DESK_MODE


if __name__ == "__main__":
    run_once()
