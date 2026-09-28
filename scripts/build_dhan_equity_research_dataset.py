from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
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


def _valid_ohlc(row: tuple) -> bool:
    return (
        row[2] > 0
        and row[3] > 0
        and row[4] > 0
        and row[5] > 0
        and row[4] <= row[2] <= row[3]
        and row[4] <= row[5] <= row[3]
    )


def _bar_payload(row: tuple, dt: datetime) -> dict:
    return {
        "timestamp": dt.isoformat(),
        "open": row[2],
        "high": row[3],
        "low": row[4],
        "close": row[5],
        "volume": row[6],
    }


def build_research_dataset(
    db_path: Path,
    output_dir: Path,
    dataset_id: str = "equity_nse_discovery_5m",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_dir = output_dir / "dhan_equity_clean"
    quarantine_dir = output_dir / "dhan_equity_quarantine"
    manifest_path = output_dir / "equity_nse_discovery_5m_manifest.json"
    clean_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
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
    finally:
        conn.close()

    sessions: dict[tuple[str, str], list[tuple[tuple, datetime]]] = defaultdict(list)
    for row in rows:
        dt = datetime.fromtimestamp(row[1], IST)
        sessions[(row[0], dt.date().isoformat())].append((row, dt))

    clean_by_symbol: dict[str, list[dict]] = defaultdict(list)
    quarantine_by_symbol: dict[str, list[dict]] = defaultdict(list)
    reason_counts = Counter()
    session_counts = Counter()
    complete_sessions: dict[str, int] = Counter()
    partial_sessions: dict[str, int] = Counter()

    for (symbol, session_date), session_rows in sorted(sessions.items()):
        regular_rows = [(row, dt) for row, dt in session_rows if _is_regular(dt)]

        session_bad = False
        for row, dt in session_rows:
            reasons = []
            if dt.weekday() >= 5:
                reasons.append("WEEKEND")
            elif not _is_regular(dt):
                reasons.append("OUTSIDE_REGULAR_SESSION")
            if row[6] is not None and row[6] < 0:
                reasons.append("NEGATIVE_VOLUME")
            if not _valid_ohlc(row):
                reasons.append("INVALID_OHLC")
            if reasons:
                session_bad = True
                payload = {
                    "symbol": symbol,
                    "session_date": session_date,
                    **_bar_payload(row, dt),
                    "timestamp_epoch": row[1],
                    "reasons": reasons,
                }
                quarantine_by_symbol[symbol].append(payload)
                reason_counts.update(reasons)

        if not regular_rows:
            session_counts["EXCLUDED_NO_REGULAR_BARS"] += 1
            continue

        if not _is_full_session(regular_rows):
            partial_sessions[symbol] += 1
            session_counts["EXCLUDED_PARTIAL_SESSION"] += 1
            for row, dt in regular_rows:
                if not any(
                    item["timestamp_epoch"] == row[1] and item["symbol"] == symbol
                    for item in quarantine_by_symbol[symbol]
                ):
                    quarantine_by_symbol[symbol].append(
                        {
                            "symbol": symbol,
                            "session_date": session_date,
                            **_bar_payload(row, dt),
                            "timestamp_epoch": row[1],
                            "reasons": ["PARTIAL_SESSION"],
                        }
                    )
            continue

        if session_bad:
            session_counts["EXCLUDED_INVALID_SESSION"] += 1
            continue

        complete_sessions[symbol] += 1
        for row, dt in regular_rows:
            clean_by_symbol[symbol].append(_bar_payload(row, dt))

    clean_rows = 0
    quarantine_rows = 0
    symbol_manifest: dict[str, dict] = {}

    for symbol in sorted(set(clean_by_symbol) | set(quarantine_by_symbol)):
        clean_path = clean_dir / f"{symbol}.jsonl"
        quarantine_path = quarantine_dir / f"{symbol}.jsonl"
        clean_rows += len(clean_by_symbol[symbol])
        quarantine_rows += len(quarantine_by_symbol[symbol])

        with clean_path.open("w", encoding="utf-8") as handle:
            for row in clean_by_symbol[symbol]:
                handle.write(_canonical(row) + "\n")

        quarantine_by_symbol[symbol].sort(
            key=lambda x: (x["timestamp_epoch"], x["reasons"])
        )
        with quarantine_path.open("w", encoding="utf-8") as handle:
            for row in quarantine_by_symbol[symbol]:
                handle.write(_canonical(row) + "\n")

        symbol_manifest[symbol] = {
            "clean_rows": len(clean_by_symbol[symbol]),
            "quarantine_rows": len(quarantine_by_symbol[symbol]),
            "complete_sessions": complete_sessions[symbol],
            "partial_sessions": partial_sessions[symbol],
            "clean_fingerprint": _fingerprint(clean_by_symbol[symbol]),
            "quarantine_fingerprint": _fingerprint(quarantine_by_symbol[symbol]),
        }

    manifest = {
        "schema_version": "1.1",
        "bar_schema": "MarketBar",
        "dataset_id": dataset_id,
        "source": str(db_path),
        "source_unchanged": True,
        "timezone": "Asia/Kolkata",
        "symbol_partitioned": True,
        "session_policy": {
            "regular_open": "09:15",
            "regular_close": "15:30",
            "expected_bars": 75,
            "allow_terminal_15_30": True,
            "open_tolerance_seconds": OPEN_TOLERANCE_SECONDS,
            "no_interpolation": True,
            "no_timestamp_rounding": True,
            "no_cross_symbol_mixing": True,
        },
        "input_rows": len(rows),
        "clean_rows": clean_rows,
        "quarantine_rows": quarantine_rows,
        "quarantine_reasons": dict(reason_counts),
        "session_exclusions": dict(session_counts),
        "symbols": symbol_manifest,
    }
    manifest["manifest_fingerprint"] = _fingerprint(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a non-destructive NSE equity research dataset from the local Dhan SQLite store."
    )
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset", default="equity_nse_discovery_5m")
    args = parser.parse_args()
    print(json.dumps(build_research_dataset(args.db, args.output_dir, args.dataset), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
