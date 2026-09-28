from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
REGULAR_OPEN = time(9, 15)
REGULAR_CLOSE = time(15, 30)


def audit(db_path: Path, dataset_id: str) -> dict:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT symbol, timestamp, open, high, low, close, volume
        FROM equity_bars
        WHERE dataset_id = ?
        ORDER BY symbol, timestamp
        """,
        (dataset_id,),
    )

    total = 0
    negative_volume = []
    invalid_ohlc = []
    outside_regular_session = []
    weekend_rows = []
    by_symbol = Counter()
    sessions = defaultdict(list)
    previous = {}

    for symbol, ts, o, h, l, c, volume in cur.fetchall():
        total += 1
        by_symbol[symbol] += 1
        dt = datetime.fromtimestamp(ts, IST)
        session_date = dt.date()
        sessions[(symbol, session_date)].append(dt)

        if volume is not None and volume < 0:
            negative_volume.append(
                {"symbol": symbol, "timestamp": dt.isoformat(), "volume": volume}
            )

        if not (o > 0 and h > 0 and l > 0 and c > 0 and l <= o <= h and l <= c <= h):
            invalid_ohlc.append(
                {"symbol": symbol, "timestamp": dt.isoformat()}
            )

        if dt.weekday() >= 5:
            weekend_rows.append({"symbol": symbol, "timestamp": dt.isoformat()})
        elif not (REGULAR_OPEN <= dt.time() <= REGULAR_CLOSE):
            outside_regular_session.append(
                {"symbol": symbol, "timestamp": dt.isoformat()}
            )

        previous_key = (symbol, session_date)
        if previous_key in previous:
            delta = (dt - previous[previous_key]).total_seconds()
            if delta <= 0:
                pass
        previous[previous_key] = dt

    incomplete_sessions = []
    for (symbol, day), values in sorted(sessions.items()):
        regular = [
            x for x in values
            if x.weekday() < 5 and REGULAR_OPEN <= x.time() <= REGULAR_CLOSE
        ]
        if not regular:
            continue
        first = min(regular)
        last = max(regular)
        if first.time() > REGULAR_OPEN or last.time() < REGULAR_CLOSE:
            incomplete_sessions.append(
                {
                    "symbol": symbol,
                    "date": day.isoformat(),
                    "bars": len(regular),
                    "first": first.isoformat(),
                    "last": last.isoformat(),
                }
            )

    conn.close()

    return {
        "schema_version": "1.0",
        "dataset_id": dataset_id,
        "database": str(db_path),
        "timezone": "Asia/Kolkata",
        "regular_session": {"open": "09:15", "close": "15:30"},
        "total_bars": total,
        "symbols": dict(sorted(by_symbol.items())),
        "negative_volume_count": len(negative_volume),
        "negative_volume_rows": negative_volume,
        "invalid_ohlc_count": len(invalid_ohlc),
        "invalid_ohlc_rows": invalid_ohlc[:100],
        "weekend_row_count": len(weekend_rows),
        "outside_regular_session_count": len(outside_regular_session),
        "outside_regular_session_examples": outside_regular_session[:100],
        "incomplete_session_count": len(incomplete_sessions),
        "incomplete_session_examples": incomplete_sessions[:100],
        "source_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--dataset", default="equity_nse_discovery_5m")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit(args.db, args.dataset)
    payload = json.dumps(report, indent=2, sort_keys=True, default=str)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")

    print(payload)


if __name__ == "__main__":
    main()
