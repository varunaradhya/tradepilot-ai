from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.research_store import research_store

IST = ZoneInfo("Asia/Kolkata")
OPEN = time(9, 15)
CLOSE = time(15, 30)
EXPECTED = 75


def validate(rows: list[dict]) -> dict:
    sessions: dict[str, list[dict]] = {}
    for row in rows:
        ts = row["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)
        local = ts.astimezone(IST)
        sessions.setdefault(local.date().isoformat(), []).append(row)

    complete = partial = outside = duplicates = 0
    issues = Counter()

    for session, items in sessions.items():
        times = []
        for row in items:
            ts = row["timestamp"]
            local = (ts.replace(tzinfo=IST) if ts.tzinfo is None else ts).astimezone(IST)
            times.append(local)
            if local.weekday() >= 5 or not (OPEN <= local.time() <= CLOSE):
                outside += 1
                issues["OUTSIDE_REGULAR_SESSION"] += 1

        keys = [x.isoformat() for x in times]
        duplicates += len(keys) - len(set(keys))
        if len(items) == EXPECTED and min(times).time() == OPEN and max(times).time() >= time(15, 25):
            complete += 1
        else:
            partial += 1
            issues["PARTIAL_SESSION"] += 1

    return {
        "status": "OK" if rows and duplicates == 0 and outside == 0 else "DATA_QUALITY_FAILED",
        "dataset_rows": len(rows),
        "session_count": len(sessions),
        "complete_sessions": complete,
        "partial_sessions": partial,
        "outside_regular_session_rows": outside,
        "duplicate_timestamps": duplicates,
        "issues": dict(issues),
        "timezone": "Asia/Kolkata",
        "regular_session": {"open": "09:15", "close": "15:30", "expected_bars": 75},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate stored NIFTY benchmark research data before V2-B use.")
    parser.add_argument("--benchmark", default="NIFTY")
    parser.add_argument("--interval", default="5", choices=["1", "5", "15", "25", "60"])
    args = parser.parse_args()
    dataset = f"benchmark/{args.benchmark.strip().upper()}_intraday_{args.interval}m"
    rows = [bar.as_row() for bar in research_store.load(dataset)]
    result = {"dataset": dataset, **validate(rows)}
    print(json.dumps(result, indent=2, default=str, sort_keys=True))
    if result["status"] != "OK":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
