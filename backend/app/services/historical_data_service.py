from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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

        values = {key: float(row[key]) for key in ("open", "high", "low", "close")}
        if min(values.values()) <= 0:
            raise ValueError("OHLC prices must be positive")
        if values["high"] < max(values["open"], values["close"]) or values["low"] > min(values["open"], values["close"]):
            raise ValueError("Invalid OHLC relationship")
        if values["high"] < values["low"]:
            raise ValueError("High cannot be below low")

        volume = row.get("volume")
        normalized.append(MarketBar(timestamp=timestamp, **values, volume=None if volume is None else float(volume)))

    return sorted(normalized, key=lambda item: item.timestamp)


def validate_dataset(rows: Sequence[MarketBar]) -> dict:
    """Return deterministic quality diagnostics before a dataset enters backtesting."""
    if not rows:
        return {"valid": False, "bars": 0, "duplicates": 0, "gaps": 0, "message": "No market data"}

    timestamps = [row.timestamp for row in rows]
    duplicates = len(timestamps) - len(set(timestamps))
    gaps = sum(1 for previous, current in zip(timestamps, timestamps[1:]) if current <= previous)
    missing_volume = sum(1 for row in rows if row.volume is None)

    return {
        "valid": duplicates == 0 and gaps == 0,
        "bars": len(rows),
        "start": timestamps[0].isoformat(),
        "end": timestamps[-1].isoformat(),
        "duplicates": duplicates,
        "non_increasing_timestamps": gaps,
        "missing_volume": missing_volume,
        "message": "OK" if duplicates == 0 and gaps == 0 else "Dataset requires cleaning",
    }
