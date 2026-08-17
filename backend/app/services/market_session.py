from datetime import date, datetime, time
from zoneinfo import ZoneInfo

INDIA_TZ = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def to_india_time(value: datetime) -> datetime:
    """Normalize aware/naive timestamps to Asia/Kolkata for session decisions."""
    if value.tzinfo is None:
        return value.replace(tzinfo=INDIA_TZ)
    return value.astimezone(INDIA_TZ)


def is_weekday(value: date) -> bool:
    return value.weekday() < 5


def is_cash_session_open(value: datetime) -> bool:
    local = to_india_time(value)
    return is_weekday(local.date()) and MARKET_OPEN <= local.time() <= MARKET_CLOSE


def session_date(value: datetime) -> date:
    return to_india_time(value).date()
