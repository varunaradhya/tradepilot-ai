from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class MarketSchedulerConfig:
    market_open: time = time(9, 15)
    market_close: time = time(15, 30)
    timezone_name: str = "Asia/Kolkata"


def scheduler_status(now: datetime | None = None, config: MarketSchedulerConfig = MarketSchedulerConfig()) -> dict:
    """Return deterministic NSE-session status for a worker/scheduler.

    This service does not start threads, call brokers, or place orders. A deployed
    worker can use this status to decide when to invoke the existing market-data
    and paper-session services.
    """
    tz = ZoneInfo(config.timezone_name)
    current = (now or datetime.now(tz)).astimezone(tz)
    weekday = current.weekday() < 5
    local_time = current.time().replace(tzinfo=None)
    in_session = weekday and config.market_open <= local_time <= config.market_close
    return {
        "timezone": config.timezone_name,
        "timestamp": current.isoformat(),
        "market": "NSE_EQ",
        "weekday": weekday,
        "market_open": config.market_open.isoformat(),
        "market_close": config.market_close.isoformat(),
        "session_active": in_session,
        "mode": "SIMULATION_ONLY",
        "broker_orders_enabled": False,
    }
