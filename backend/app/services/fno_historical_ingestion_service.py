from __future__ import annotations

"""Normalize provider historical F&O data without inventing executable quotes.

Dhan's expired rolling-options endpoint supplies minute OHLC/OI/IV/volume/spot,
but not historical best bid/ask. Normalized snapshots therefore remain
non-execution-grade until a provider with historical executable quotes is
attached. Close/LTP is never copied into bid/ask.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class HistoricalOptionBar:
    timestamp: int
    strike: float
    option_type: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    iv: float | None
    volume: int | None
    oi: int | None
    spot: float | None
    source: str = "dhan_expired_options"
    execution_grade: bool = False


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _array_value(values: Any, index: int) -> Any:
    if not isinstance(values, list) or index >= len(values):
        return None
    return values[index]


def normalize_dhan_rolling_option_response(
    response: dict[str, Any],
    *,
    strike_hint: float,
    option_type: str,
) -> list[HistoricalOptionBar]:
    """Normalize one Dhan rolling-option response into immutable option bars."""
    side = str(option_type).strip().upper()
    if side not in {"CE", "PE", "CALL", "PUT"}:
        raise ValueError("option_type must be CE/PE/CALL/PUT")
    side = "CE" if side in {"CE", "CALL"} else "PE"

    data = response.get("data") or {}
    payload = data.get("ce" if side == "CE" else "pe")
    if not isinstance(payload, dict):
        return []

    timestamps = payload.get("timestamp") or []
    rows: list[HistoricalOptionBar] = []
    seen_timestamps: set[int] = set()
    for index, raw_timestamp in enumerate(timestamps):
        timestamp = _int(raw_timestamp)
        if timestamp is None:
            continue
        if timestamp in seen_timestamps:
            raise ValueError(f"duplicate historical option timestamp: {timestamp}")
        seen_timestamps.add(timestamp)
        strike = _float(_array_value(payload.get("strike"), index))
        rows.append(
            HistoricalOptionBar(
                timestamp=timestamp,
                strike=strike if strike is not None else float(strike_hint),
                option_type=side,
                open=_float(_array_value(payload.get("open"), index)),
                high=_float(_array_value(payload.get("high"), index)),
                low=_float(_array_value(payload.get("low"), index)),
                close=_float(_array_value(payload.get("close"), index)),
                iv=_float(_array_value(payload.get("iv"), index)),
                volume=_int(_array_value(payload.get("volume"), index)),
                oi=_int(_array_value(payload.get("oi"), index)),
                spot=_float(_array_value(payload.get("spot"), index)),
            )
        )
    return rows


def build_option_chain_snapshots(
    rows: Iterable[HistoricalOptionBar],
) -> list[dict[str, Any]]:
    """Merge normalized bars into timestamped option-chain snapshots."""
    grouped: dict[int, dict[str, dict[str, dict[str, Any]]]] = defaultdict(dict)
    for row in rows:
        strike_key = str(int(row.strike)) if row.strike.is_integer() else str(row.strike)
        grouped[row.timestamp].setdefault(strike_key, {})[row.option_type.lower()] = {
            "last_price": row.close,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "volume": row.volume,
            "oi": row.oi,
            "implied_volatility": row.iv,
            "spot": row.spot,
            "execution_grade": row.execution_grade,
        }

    return [
        {"timestamp": timestamp, "oc": chain, "execution_grade": False}
        for timestamp, chain in sorted(grouped.items())
    ]


def merge_historical_option_sources(
    sources: Sequence[Iterable[HistoricalOptionBar]],
) -> list[HistoricalOptionBar]:
    """Merge sources deterministically and reject duplicate observations."""
    merged: dict[tuple[int, float, str], HistoricalOptionBar] = {}
    for source in sources:
        for row in source:
            key = (row.timestamp, row.strike, row.option_type)
            if key in merged:
                raise ValueError(f"duplicate historical option observation: {key}")
            merged[key] = row
    return sorted(merged.values(), key=lambda row: (row.timestamp, row.strike, row.option_type))
