from __future__ import annotations

from dataclasses import dataclass
import math
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Iterable, Sequence

from app.services.nse_equity_calendar import DEFAULT_NSE_EQUITY_CALENDAR, NSEEquityCalendar


@dataclass(frozen=True)
class MarketBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    def as_row(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


def normalize_bars(rows: Iterable[dict]) -> list[MarketBar]:
    """Normalize provider rows and reject malformed OHLC data early."""
    normalized: list[MarketBar] = []
    for row in rows:
        timestamp = row.get("timestamp") or row.get("datetime") or row.get("date")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if not isinstance(timestamp, datetime):
            raise ValueError("Each market bar requires a valid timestamp")
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        values = {key: float(row[key]) for key in ("open", "high", "low", "close")}
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError("OHLC prices must be finite")
        if min(values.values()) <= 0:
            raise ValueError("OHLC prices must be positive")
        if values["high"] < max(values["open"], values["close"]) or values["low"] > min(values["open"], values["close"]):
            raise ValueError("Invalid OHLC relationship")
        if values["high"] < values["low"]:
            raise ValueError("High cannot be below low")

        volume = row.get("volume")
        if volume is not None:
            volume = float(volume)
            if not math.isfinite(volume) or volume < 0:
                raise ValueError("Volume must be finite and non-negative")
        normalized.append(MarketBar(timestamp=timestamp, **values, volume=volume))

    return sorted(normalized, key=lambda item: item.timestamp)


def validate_nse_equity_dataset(
    rows: Sequence[MarketBar],
    expected_interval_minutes: int | None = None,
    calendar: NSEEquityCalendar = DEFAULT_NSE_EQUITY_CALENDAR,
) -> dict:
    """Validate intraday bars against the regular NSE equity session calendar."""
    base = validate_dataset(rows, expected_interval_minutes=None)
    if not rows:
        return {
            **base,
            "calendar_valid": False,
            "weekend_bars": 0,
            "holiday_bars": 0,
            "special_session_bars": 0,
            "outside_session_bars": 0,
            "pre_market_bars": 0,
            "post_market_bars": 0,
            "missing_sessions": 0,
            "missing_session_dates": [],
            "session_interval_gaps": 0,
            "timezone_inconsistencies": 0,
        }

    ist = ZoneInfo("Asia/Kolkata")
    regular_start = time(9, 15)
    regular_end = time(15, 30)
    local_times = [bar.timestamp.astimezone(ist) for bar in rows]
    dates = [ts.date() for ts in local_times]
    source_offsets = {bar.timestamp.utcoffset() for bar in rows}
    offsets = {ts.utcoffset() for ts in local_times}
    weekend_bars = sum(ts.weekday() >= 5 for ts in local_times)
    special_session_bars = sum(ts.date() in calendar.special_sessions for ts in local_times)
    holiday_bars = sum(
        ts.date() in calendar.holidays and ts.date() not in calendar.special_sessions
        for ts in local_times
    )
    pre_market_bars = sum(ts.time() < regular_start for ts in local_times)
    post_market_bars = sum(ts.time() > regular_end for ts in local_times)
    outside_session_bars = pre_market_bars + post_market_bars

    unique_dates = sorted(set(dates))
    missing_session_dates: list[date] = []
    calendar_valid = True
    try:
        expected_sessions = calendar.expected_sessions_between(unique_dates[0], unique_dates[-1])
        observed_regular_dates = {
            ts.date() for ts in local_times
            if ts.time() >= regular_start and ts.time() <= regular_end
            and calendar.is_trading_day(ts.date())
        }
        missing_session_dates = [day for day in expected_sessions if day not in observed_regular_dates]
    except ValueError:
        calendar_valid = False
        expected_sessions = []

    session_interval_gaps = 0
    if expected_interval_minutes and expected_interval_minutes > 0:
        expected_seconds = expected_interval_minutes * 60
        for previous, current in zip(local_times, local_times[1:]):
            if previous.date() != current.date():
                continue
            if previous.time() < regular_start or current.time() > regular_end:
                continue
            if current.time() < regular_start or previous.time() > regular_end:
                continue
            if (current - previous).total_seconds() > expected_seconds * 1.5:
                session_interval_gaps += 1

    valid = (
        base["valid"]
        and calendar_valid
        and weekend_bars == 0
        and holiday_bars == 0
        and special_session_bars == 0
        and outside_session_bars == 0
        and not missing_session_dates
        and session_interval_gaps == 0
        and len(offsets) <= 1
    )
    return {
        **base,
        "valid": valid,
        "calendar_valid": calendar_valid,
        "calendar": {
            "market": calendar.market,
            "source": calendar.source,
            "source_version": calendar.source_version,
            "session_start": regular_start.isoformat(),
            "session_end": regular_end.isoformat(),
        },
        "weekend_bars": weekend_bars,
        "holiday_bars": holiday_bars,
        "special_session_bars": special_session_bars,
        "outside_session_bars": outside_session_bars,
        "pre_market_bars": pre_market_bars,
        "post_market_bars": post_market_bars,
        "missing_sessions": len(missing_session_dates),
        "missing_session_dates": [day.isoformat() for day in missing_session_dates],
        "session_interval_gaps": session_interval_gaps,
        "timezone_inconsistencies": max(len(source_offsets) - 1, 0),
        "message": "OK" if valid else "Dataset requires session/calendar review",
    }


def validate_dataset(rows: Sequence[MarketBar], expected_interval_minutes: int | None = None) -> dict:
    """Return deterministic quality diagnostics before a dataset enters backtesting."""
    if not rows:
        return {"valid": False, "bars": 0, "duplicates": 0, "gaps": 0, "message": "No market data"}

    timestamps = [row.timestamp for row in rows]
    duplicates = len(timestamps) - len(set(timestamps))
    gaps = sum(1 for previous, current in zip(timestamps, timestamps[1:]) if current <= previous)
    interval_gaps = 0
    if expected_interval_minutes and expected_interval_minutes > 0:
        expected_seconds = expected_interval_minutes * 60
        interval_gaps = sum(1 for previous, current in zip(timestamps, timestamps[1:]) if (current - previous).total_seconds() > expected_seconds * 1.5)
    missing_volume = sum(1 for row in rows if row.volume is None)

    return {
        "valid": duplicates == 0 and gaps == 0 and interval_gaps == 0,
        "bars": len(rows),
        "start": timestamps[0].isoformat(),
        "end": timestamps[-1].isoformat(),
        "duplicates": duplicates,
        "non_increasing_timestamps": gaps,
        "interval_gaps": interval_gaps,
        "missing_volume": missing_volume,
        "message": "OK" if duplicates == 0 and gaps == 0 and interval_gaps == 0 else "Dataset requires cleaning",
    }
