from __future__ import annotations

from dataclasses import dataclass
import math
from datetime import datetime, timezone
from typing import Iterable, Sequence


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
