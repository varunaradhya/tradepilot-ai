from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
REGULAR_OPEN = time(9, 15)
REGULAR_CLOSE = time(15, 30)
EXPECTED_LAST_BAR = time(15, 25)
EXPECTED_BARS = 75
OPEN_TOLERANCE_SECONDS = 5


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _is_regular(dt: datetime) -> bool:
    return dt.weekday() < 5 and REGULAR_OPEN <= dt.time() <= REGULAR_CLOSE


def _is_full_session(rows: list[tuple]) -> bool:
    if not rows:
        return False
    times = [row[1] for row in rows]
    first, last = min(times), max(times)
    first_s = first.hour * 3600 + first.minute * 60 + first.second
    open_s = REGULAR_OPEN.hour * 3600 + REGULAR_OPEN.minute * 60
    last_s = last.hour * 3600 + last.minute * 60 + last.second
    expected_last_s = EXPECTED_LAST_BAR.hour * 3600 + EXPECTED_LAST_BAR.minute * 60
    return (
        open_s <= first_s <= open_s + OPEN_TOLERANCE_SECONDS
        and last_s >= expected_last_s
        and len(rows) in {EXPECTED_BARS, EXPECTED_BARS + 1}
    )


def build_research_dataset(
    db_path: Path,
    output_dir: Path,
    dataset_id: str = "equity_nse_discovery_5m",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = output_dir / "equity_nse_discovery_5m_clean.jsonl"
    quarantine_path = output_dir / "equity_nse_discovery_5m_quarantine.jsonl"
    manifest_path = output_dir / "equity_nse_discovery_5m_manifest.json"

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

    rows = cur.fetchall()
    conn.close()

    sessions: dict[tuple[str, str], list[tuple]] = {}
    for row in rows:
        symbol, ts = row[0], row[1]
        dt = datetime.fromtimestamp(ts, IST)
        sessions.setdefault((symbol, dt.date().isoformat()), []).append((row, dt))

    clean = []
    quarantine = []
    reason_counts = Counter()
    session_counts = Counter()

    for (symbol, session_date), session_rows in sorted(sessions.items()):
        regular_rows = [(row, dt) for row, dt in session_rows if _is_regular(dt)]

        # Entire non-weekday / non-regular sessions are excluded, but retained
        # in the quarantine ledger. No source row is modified or synthesized.
        for row, dt in session_rows:
            reasons = []
            if dt.weekday() >= 5:
                reasons.append("WEEKEND")
            elif not _is_regular(dt):
                reasons.append("OUTSIDE_REGULAR_SESSION")
            if row[6] is not None and row[6] < 0:
                reasons.append("NEGATIVE_VOLUME")
            if not (row[2] > 0 and row[3] > 0 and row[4] > 0 and row[5] > 0 and row[4] <= row[2] <= row[3] and row[4] <= row[5] <= row[3]):
                reasons.append("INVALID_OHLC")

            if reasons:
                quarantine.append({
                    "symbol": symbol,
                    "session_date": session_date,
                    "timestamp": datetime.fromtimestamp(row[1], IST).isoformat(),
                    "timestamp_epoch": row[1],
                    "open": row[2], "high": row[3], "low": row[4], "close": row[5],
                    "volume": row[6],
                    "reasons": reasons,
                })
                for reason in reasons:
                    reason_counts[reason] += 1

        if not regular_rows:
            session_counts["EXCLUDED_NO_REGULAR_BARS"] += 1
            continue

        # A normal research session must contain the expected opening and
        # terminal coverage. Partial sessions are not filled or interpolated.
        if not _is_full_session(regular_rows):
            session_counts["EXCLUDED_PARTIAL_SESSION"] += 1
            for row, dt in regular_rows:
                if not any(q["timestamp_epoch"] == row[1] and q["symbol"] == symbol for q in quarantine):
                    quarantine.append({
                        "symbol": symbol,
                        "session_date": session_date,
                        "timestamp": dt.isoformat(),
                        "timestamp_epoch": row[1],
                        "open": row[2], "high": row[3], "low": row[4], "close": row[5],
                        "volume": row[6],
                        "reasons": ["PARTIAL_SESSION"],
                    })
            continue

        for row, dt in regular_rows:
            if row[6] is not None and row[6] < 0:
                continue
            if not (row[2] > 0 and row[3] > 0 and row[4] > 0 and row[5] > 0 and row[4] <= row[2] <= row[3] and row[4] <= row[5] <= row[3]):
                continue
            clean.append({
                "symbol": symbol,
                "session_date": session_date,
                "timestamp": dt.isoformat(),
                "timestamp_epoch": row[1],
                "open": row[2], "high": row[3], "low": row[4], "close": row[5],
                "volume": row[6],
            })

    clean.sort(key=lambda x: (x["symbol"], x["timestamp_epoch"]))
    quarantine.sort(key=lambda x: (x["symbol"], x["timestamp_epoch"], x["reasons"]))

    with clean_path.open("w", encoding="utf-8") as handle:
        for row in clean:
            handle.write(_canonical(row) + "\n")
    with quarantine_path.open("w", encoding="utf-8") as handle:
        for row in quarantine:
            handle.write(_canonical(row) + "\n")

    manifest = {
        "schema_version": "1.0",
        "dataset_id": dataset_id,
        "source": str(db_path),
        "source_unchanged": True,
        "timezone": "Asia/Kolkata",
        "session_policy": {
            "regular_open": "09:15",
            "regular_close": "15:30",
            "expected_bars": 75,
            "allow_terminal_15_30": True,
            "open_tolerance_seconds": OPEN_TOLERANCE_SECONDS,
            "no_interpolation": True,
            "no_timestamp_rounding": True,
        },
        "input_rows": len(rows),
        "clean_rows": len(clean),
        "quarantine_rows": len(quarantine),
        "quarantine_reasons": dict(reason_counts),
        "session_exclusions": dict(session_counts),
        "clean_fingerprint": _fingerprint(clean),
        "quarantine_fingerprint": _fingerprint(quarantine),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a non-destructive NSE equity research dataset from the local Dhan SQLite store.")
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset", default="equity_nse_discovery_5m")
    args = parser.parse_args()
    print(json.dumps(build_research_dataset(args.db, args.output_dir, args.dataset), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
