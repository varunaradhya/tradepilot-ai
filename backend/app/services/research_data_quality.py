from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Sequence


def _parse_timestamp(value):
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def analyze_intraday_quality(rows: Sequence[dict], expected_interval_minutes: int | None = None) -> dict:
    if not rows:
        return {"valid": False, "bars": 0, "sessions": 0, "duplicates": 0, "non_chronological": 0, "invalid_ohlc": 0, "missing_volume": 0, "large_gaps": 0, "invalid_timestamps": 0, "message": "No market data"}

    timestamps = []
    invalid_timestamps = 0
    invalid_ohlc = 0
    missing_volume = 0

    for row in rows:
        ts = _parse_timestamp(row.get("timestamp") or row.get("time"))
        if ts is None:
            invalid_timestamps += 1
        timestamps.append(ts)

        try:
            o, h, l, c = map(float, (row["open"], row["high"], row["low"], row["close"]))
            if min(o, h, l, c) <= 0 or h < max(o, c) or l > min(o, c) or h < l:
                invalid_ohlc += 1
        except (KeyError, TypeError, ValueError):
            invalid_ohlc += 1

        if row.get("volume") is None:
            missing_volume += 1

    valid_ts = [ts for ts in timestamps if ts is not None]
    counts = Counter(ts.isoformat() for ts in valid_ts)
    duplicates = sum(v - 1 for v in counts.values() if v > 1)
    non_chronological = sum(1 for a, b in zip(valid_ts, valid_ts[1:]) if b < a)

    large_gaps = 0
    if expected_interval_minutes and expected_interval_minutes > 0:
        expected_seconds = expected_interval_minutes * 60
        for a, b in zip(valid_ts, valid_ts[1:]):
            if (b - a).total_seconds() > expected_seconds * 1.5:
                large_gaps += 1

    sessions = {
        str(row.get("session") or (ts.date().isoformat() if ts else "UNKNOWN"))
        for row, ts in zip(rows, timestamps)
    }
    valid = (
        duplicates == 0
        and non_chronological == 0
        and invalid_ohlc == 0
        and invalid_timestamps == 0
    )

    return {
        "valid": valid,
        "bars": len(rows),
        "sessions": len(sessions),
        "duplicates": duplicates,
        "non_chronological": non_chronological,
        "invalid_ohlc": invalid_ohlc,
        "missing_volume": missing_volume,
        "large_gaps": large_gaps,
        "invalid_timestamps": invalid_timestamps,
        "message": "OK" if valid else "Dataset requires review",
    }
