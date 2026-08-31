"""Probe 4: can every desk seat actually reach Featherless with the credentials in this environment?

Why this exists as a separate probe rather than a `dry_run` of the desk: `agent.desk.run_once`
returns at the `market_closed` check before it ever reaches the debate, so a CI smoke test outside
market hours proves the checkout, the CLI and the account guard — and tells you nothing at all
about the LLM layer. On Mon 31 Aug the FEATHERLESS_API_KEY secret was wrong, all three quant seats
returned 401, `DESK_DEBATE=required` turned that into a total veto, and the desk took a zero on
session 1 of 4. This probe is clock-independent, so it can be run the night before.

Run:  uv run python probes/04_featherless_seats.py
Exit code 0 only if every configured model answers. Never prints the key.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Run as a script (`uv run python probes/04_featherless_seats.py`) like the other probes: the
# leading digit means it cannot be a `-m` module, so put the repo root on the path by hand.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from agent.seats import FeatherlessSeatClient, SeatError

load_dotenv()

BASE = os.environ.get("FEATHERLESS_BASE_URL") or "https://api.featherless.ai/v1"
KEY = os.environ.get("FEATHERLESS_API_KEY", "")
MODELS = [m.strip() for m in os.environ.get("FEATHERLESS_MODELS", "").split(",") if m.strip()]
ARGUER = os.environ.get("FEATHERLESS_ARGUER_MODEL", "").strip()


def main() -> int:
    if not KEY:
        print("FAIL: FEATHERLESS_API_KEY is empty in this environment")
        return 1
    print(f"key present (len {len(KEY)}, ends ...{KEY[-4:]}) · base {BASE}")

    # The arguer seat may be a model outside the quant ensemble; it has to work too.
    targets = list(dict.fromkeys(MODELS + ([ARGUER] if ARGUER else [])))
    if not targets:
        print("FAIL: FEATHERLESS_MODELS is empty — the quant ensemble has nothing to dispatch to")
        return 1

    failures = 0
    for model in targets:
        seat = FeatherlessSeatClient(model=model, base_url=BASE, api_key=KEY)
        try:
            out = seat.complete(system="Reply with the single word OK.", user="ping",
                                max_tokens=5, timeout=30.0)
            print(f"  200  {model}  -> {out.strip()[:20]!r}")
        except SeatError as e:
            # SeatError already carries the provider's status text; it does not carry the key.
            print(f"  FAIL {model}  -> {e}")
            failures += 1

    total = len(targets)
    print(f"\n{total - failures}/{total} seats reachable")
    if failures:
        print("The desk would stand down on every open decision while DESK_DEBATE=required.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
