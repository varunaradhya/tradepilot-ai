from dataclasses import dataclass
from datetime import datetime, time
from math import isfinite


@dataclass(frozen=True)
class CandleQuality:
    valid: bool
    duplicate: bool = False
    stale: bool = False
    missing_intervals: int = 0
    out_of_order: bool = False
    outside_session: int = 0
    invalid_ohlc: int = 0
    non_trading_day: int = 0
    reason: str | None = None


def _ohlc_valid(row) -> bool:
    try:
        values = [float(row[key]) for key in ("open", "high", "low", "close")]
    except (KeyError, TypeError, ValueError):
        return False
    if not all(isfinite(value) and value > 0 for value in values):
        return False
    open_price, high, low, close = values
    return low <= open_price <= high and low <= close <= high and low <= high


def validate_intraday_candles(rows, expected_minutes: int = 5, stale_after_minutes: int = 15) -> CandleQuality:
    if not rows:
        return CandleQuality(False, reason="NO_DATA")
    if expected_minutes <= 0 or stale_after_minutes < 0:
        raise ValueError("expected_minutes must be positive and stale_after_minutes non-negative")

    timestamps = [row["timestamp"] if isinstance(row, dict) else row.timestamp for row in rows]
    out_of_order = timestamps != sorted(timestamps)
    if out_of_order:
        return CandleQuality(False, out_of_order=True, reason="OUT_OF_ORDER")

    duplicate = len(set(timestamps)) != len(timestamps)
    if duplicate:
        return CandleQuality(False, duplicate=True, reason="DUPLICATE_CANDLE")

    invalid_ohlc = sum(1 for row in rows if isinstance(row, dict) and not _ohlc_valid(row))
    missing = 0
    for previous, current in zip(timestamps, timestamps[1:]):
        delta = (current - previous).total_seconds() / 60
        if delta > expected_minutes:
            missing += max(0, round(delta / expected_minutes) - 1)

    outside_session = 0
    non_trading_day = 0
    for value in timestamps:
        if isinstance(value, datetime):
            if value.weekday() >= 5:
                non_trading_day += 1
            elif not is_indian_cash_market_time(value.time()):
                outside_session += 1

    stale = False
    if isinstance(timestamps[-1], datetime):
        now = datetime.now(timestamps[-1].tzinfo) if timestamps[-1].tzinfo else datetime.now()
        age = (now - timestamps[-1]).total_seconds() / 60
        stale = age > stale_after_minutes

    if invalid_ohlc:
        reason = "INVALID_OHLC"
    elif missing:
        reason = "MISSING_INTERVALS"
    elif stale:
        reason = "STALE_DATA"
    elif non_trading_day:
        reason = "NON_TRADING_DAY"
    elif outside_session:
        reason = "OUTSIDE_MARKET_SESSION"
    else:
        reason = None

    return CandleQuality(
        valid=not stale and not missing and not invalid_ohlc and not non_trading_day,
        stale=stale,
        missing_intervals=missing,
        outside_session=outside_session,
        invalid_ohlc=invalid_ohlc,
        non_trading_day=non_trading_day,
        reason=reason,
    )


def is_indian_cash_market_time(value: time) -> bool:
    return time(9, 15) <= value <= time(15, 30)
