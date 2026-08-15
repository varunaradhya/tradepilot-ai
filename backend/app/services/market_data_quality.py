from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class CandleQuality:
    valid: bool
    duplicate: bool = False
    stale: bool = False
    missing_intervals: int = 0
    reason: str | None = None


def validate_intraday_candles(rows, expected_minutes: int = 5, stale_after_minutes: int = 15) -> CandleQuality:
    if not rows:
        return CandleQuality(False, reason="NO_DATA")

    timestamps = [row["timestamp"] if isinstance(row, dict) else row.timestamp for row in rows]
    if timestamps != sorted(timestamps):
        return CandleQuality(False, reason="OUT_OF_ORDER")

    duplicate = len(set(timestamps)) != len(timestamps)
    if duplicate:
        return CandleQuality(False, duplicate=True, reason="DUPLICATE_CANDLE")

    missing = 0
    for previous, current in zip(timestamps, timestamps[1:]):
        delta = (current - previous).total_seconds() / 60
        if delta > expected_minutes:
            missing += max(0, round(delta / expected_minutes) - 1)

    stale = False
    if isinstance(timestamps[-1], datetime):
        age = (datetime.now(timestamps[-1].tzinfo) - timestamps[-1]).total_seconds() / 60
        stale = age > stale_after_minutes

    return CandleQuality(
        valid=not stale,
        stale=stale,
        missing_intervals=missing,
        reason="STALE_DATA" if stale else ("MISSING_INTERVALS" if missing else None),
    )


def is_indian_cash_market_time(value: time) -> bool:
    return time(9, 15) <= value <= time(15, 30)
