from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MarketDataHealth:
    fresh: bool
    last_bar_at: datetime | None
    age_seconds: float | None
    max_age_seconds: int
    reason: str

    def as_dict(self) -> dict:
        return {
            "fresh": self.fresh,
            "last_bar_at": self.last_bar_at.isoformat() if self.last_bar_at else None,
            "age_seconds": round(self.age_seconds, 3) if self.age_seconds is not None else None,
            "max_age_seconds": self.max_age_seconds,
            "reason": self.reason,
        }


def evaluate_market_data_freshness(
    last_bar_at: datetime | None,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 120,
) -> MarketDataHealth:
    """Fail closed when the latest market bar is missing, invalid or stale."""
    if max_age_seconds < 1:
        raise ValueError("max_age_seconds must be positive")
    if last_bar_at is None:
        return MarketDataHealth(False, None, None, max_age_seconds, "NO_MARKET_DATA")
    if last_bar_at.tzinfo is None:
        return MarketDataHealth(False, None, None, max_age_seconds, "NAIVE_TIMESTAMP_REJECTED")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age = (current.astimezone(timezone.utc) - last_bar_at.astimezone(timezone.utc)).total_seconds()
    if age < 0:
        return MarketDataHealth(False, last_bar_at, age, max_age_seconds, "FUTURE_TIMESTAMP_REJECTED")
    if age > max_age_seconds:
        return MarketDataHealth(False, last_bar_at, age, max_age_seconds, "STALE_MARKET_DATA")
    return MarketDataHealth(True, last_bar_at, age, max_age_seconds, "FRESH")
