from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from app.brokers.dhan import DhanAPIError, DhanClient
from app.services.historical_data_service import MarketBar, normalize_bars, validate_dataset


@dataclass(frozen=True)
class HistoricalRequest:
    security_id: str
    exchange_segment: str = "NSE_EQ"
    instrument: str = "EQUITY"
    interval: str | None = None
    oi: bool = False


def _parse_epoch_seconds(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _response_to_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Dhan's columnar chart response into normalized row dictionaries."""
    if not isinstance(payload, dict):
        raise DhanAPIError("Dhan historical-data response was not an object.")

    opens = payload.get("open") or []
    highs = payload.get("high") or []
    lows = payload.get("low") or []
    closes = payload.get("close") or []
    volumes = payload.get("volume") or []
    timestamps = payload.get("timestamp") or payload.get("time") or []

    lengths = [len(values) for values in (opens, highs, lows, closes, timestamps)]
    if not timestamps or len(set(lengths)) != 1:
        raise DhanAPIError("Dhan historical-data response contains inconsistent candle arrays.")

    rows: list[dict[str, Any]] = []
    for index in range(len(timestamps)):
        rows.append(
            {
                "timestamp": _parse_epoch_seconds(timestamps[index]),
                "open": opens[index],
                "high": highs[index],
                "low": lows[index],
                "close": closes[index],
                "volume": volumes[index] if volumes else None,
            }
        )
    return rows


def _request_ranges(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    if start >= end:
        return []
    ranges: list[tuple[date, date]] = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=max_days), end)
        ranges.append((cursor, chunk_end))
        cursor = chunk_end
    return ranges


def fetch_daily_history(
    client: DhanClient,
    request: HistoricalRequest,
    start: date,
    end: date,
) -> tuple[list[MarketBar], dict]:
    """Fetch daily history. Daily Dhan requests are not artificially chunked."""
    if request.interval is not None:
        raise ValueError("fetch_daily_history does not accept an interval")
    payload = client.historical_daily(
        security_id=request.security_id,
        exchange_segment=request.exchange_segment,
        instrument=request.instrument,
        from_date=start.isoformat(),
        to_date=end.isoformat(),
        oi=request.oi,
    )
    bars = normalize_bars(_response_to_rows(payload))
    return bars, validate_dataset(bars)


def fetch_intraday_history(
    client: DhanClient,
    request: HistoricalRequest,
    start: date,
    end: date,
) -> tuple[list[MarketBar], dict]:
    """Fetch intraday history in Dhan's maximum 90-day request windows."""
    if request.interval not in {"1", "5", "15", "25", "60"}:
        raise ValueError("Dhan intraday interval must be 1, 5, 15, 25, or 60 minutes")

    rows: list[dict[str, Any]] = []
    for chunk_start, chunk_end in _request_ranges(start, end, 90):
        payload = client.historical_intraday(
            security_id=request.security_id,
            exchange_segment=request.exchange_segment,
            instrument=request.instrument,
            interval=request.interval,
            from_date=chunk_start.isoformat(),
            to_date=chunk_end.isoformat(),
            oi=request.oi,
        )
        rows.extend(_response_to_rows(payload))

    bars = normalize_bars(rows)
    diagnostics = validate_dataset(bars)
    return bars, diagnostics
