"""Decision journal — append-only JSONL, the audit trail the dashboard and write-up read from.

Also the prediction ledger: each committed trade carries a falsifiable thesis that gets
graded when the position closes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

JOURNAL = Path(__file__).resolve().parent.parent / "data" / "journal.jsonl"
EQUITY = Path(__file__).resolve().parent.parent / "data" / "equity.csv"


def append(record: dict) -> None:
    JOURNAL.parent.mkdir(exist_ok=True)
    record.setdefault("logged_at", datetime.now(UTC).isoformat())
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def record_equity(nav: float, day_pnl: float) -> None:
    EQUITY.parent.mkdir(exist_ok=True)
    new = not EQUITY.exists()
    with EQUITY.open("a", encoding="utf-8") as f:
        if new:
            f.write("ts,nav,day_pnl\n")
        f.write(f"{datetime.now(UTC).isoformat()},{nav:.2f},{day_pnl:.2f}\n")


def grade_prediction(trade_id: str, resolved_outcome: dict) -> None:
    """Append a grading record linking back to the original thesis by trade_id."""
    append({"event": "prediction_graded", "trade_id": trade_id, **resolved_outcome})
