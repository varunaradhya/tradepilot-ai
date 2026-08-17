from dataclasses import dataclass
from datetime import date, datetime, time
from math import isfinite
from zoneinfo import ZoneInfo


INDIA_TZ = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


@dataclass(frozen=True)
class MarketExecutionContext:
    observed_at: datetime
    reference_price: float | None = None
    lower_price_band: float | None = None
    upper_price_band: float | None = None
    holiday_dates: frozenset[date] = frozenset()


@dataclass(frozen=True)
class MarketExecutionDecision:
    allowed: bool
    reason: str


def _india_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=INDIA_TZ)
    return value.astimezone(INDIA_TZ)


def is_cash_market_open(value: datetime, holiday_dates: frozenset[date] = frozenset()) -> bool:
    local = _india_datetime(value)
    return (
        local.weekday() < 5
        and local.date() not in holiday_dates
        and MARKET_OPEN <= local.time() <= MARKET_CLOSE
    )


def validate_execution_price(
    price: float | None,
    context: MarketExecutionContext,
) -> MarketExecutionDecision:
    if price is None:
        return MarketExecutionDecision(True, "PRICE_UNVERIFIED")
    if not isfinite(price) or price <= 0:
        return MarketExecutionDecision(False, "INVALID_EXECUTION_PRICE")

    lower = context.lower_price_band
    upper = context.upper_price_band
    if lower is not None and price < lower:
        return MarketExecutionDecision(False, "BELOW_PRICE_BAND")
    if upper is not None and price > upper:
        return MarketExecutionDecision(False, "ABOVE_PRICE_BAND")

    return MarketExecutionDecision(True, "EXECUTION_PRICE_ALLOWED")


def validate_market_execution(
    price: float | None,
    context: MarketExecutionContext,
) -> MarketExecutionDecision:
    if not is_cash_market_open(context.observed_at, context.holiday_dates):
        return MarketExecutionDecision(False, "MARKET_SESSION_CLOSED")
    return validate_execution_price(price, context)
