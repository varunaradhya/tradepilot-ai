from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class CandleQuality:
    valid: bool
    duplicate: bool = False
    stale: bool = False
    missing_intervals: int = 0
    out_of_order: bool = False
    outside_session: int = 0
    reason: str | None = None


def validate_intraday_candles(rows, expected_minutes: int = 5, stale_after_minutes: int = 15) -> CandleQuality:
    if not rows:
        return CandleQuality(False, reason="NO_DATA")

    timestamps = [row["timestamp"] if isinstance(row, dict) else row.timestamp for row in rows]
    out_of_order = timestamps != sorted(timestamps)
    if out_of_order:
        return CandleQuality(False, out_of_order=True, reason="OUT_OF_ORDER")

    duplicate = len(set(timestamps)) != len(timestamps)
    if duplicate:
        return CandleQuality(False, duplicate=True, reason="DUPLICATE_CANDLE")

    missing = 0
    for previous, current in zip(timestamps, timestamps[1:]):
        delta = (current - previous).total_seconds() / 60
        if delta > expected_minutes:
            missing += max(0, round(delta / expected_minutes) - 1)

    outside_session = sum(
        1 for value in timestamps
        if isinstance(value, datetime) and not is_indian_cash_market_time(value.time())
    )

    stale = False
    if isinstance(timestamps[-1], datetime):
        now = datetime.now(timestamps[-1].tzinfo) if timestamps[-1].tzinfo else datetime.now()
        age = (now - timestamps[-1]).total_seconds() / 60
        stale = age > stale_after_minutes

    # Structural quality takes precedence over wall-clock freshness when both
    # are present. This makes the diagnostic actionable: a replayed historical
    # dataset with gaps should report its gaps rather than being labelled stale.
    reason = None
    if missing:
        reason = "MISSING_INTERVALS"
    elif stale:
        reason = "STALE_DATA"
    elif outside_session:
        reason = "OUTSIDE_MARKET_SESSION"

    return CandleQuality(
        valid=not stale and not out_of_order and not duplicate and not missing,
        stale=stale,
        missing_intervals=missing,
        outside_session=outside_session,
        reason=reason,
    )


def is_indian_cash_market_time(value: time) -> bool:
    return time(9, 15) <= value <= time(15, 30)
