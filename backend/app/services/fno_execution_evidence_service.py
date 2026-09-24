from __future__ import annotations

"""Execution-grade historical option evidence boundary.

This module accepts externally sourced historical executable quotes. It never
derives bid/ask from OHLC/LTP and never repairs malformed observations.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable


@dataclass(frozen=True)
class ExecutionQuote:
    timestamp: int
    strike: float
    option_type: str
    bid: float
    ask: float
    spot: float | None = None
    expiry: str | None = None
    security_id: str | None = None
    source: str = "external_historical_quotes"


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def normalize_execution_quotes(
    rows: Iterable[dict[str, Any]],
    *,
    expected_timestamps: set[int] | None = None,
) -> list[ExecutionQuote]:
    """Validate and normalize historical executable bid/ask observations.

    A row is accepted only when timestamp, strike, option type, bid and ask are
    present and economically valid. Expected timestamps, when supplied, make
    alignment an explicit contract. No OHLC/LTP field is used as a fallback.
    """
    normalized: list[ExecutionQuote] = []
    seen: set[tuple[int, float, str]] = set()

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("historical execution quote must be an object")

        try:
            timestamp = int(row["timestamp"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("historical execution quote requires integer timestamp")

        strike = _number(row.get("strike"))
        bid = _number(row.get("bid"))
        ask = _number(row.get("ask"))
        option_type = str(row.get("option_type") or "").strip().upper()

        if strike is None or strike <= 0:
            raise ValueError("historical execution quote requires positive strike")
        if option_type not in {"CE", "PE"}:
            raise ValueError("option_type must be CE or PE")
        if bid is None or ask is None or bid <= 0 or ask <= 0:
            raise ValueError("historical execution quote requires positive bid and ask")
        if bid > ask:
            raise ValueError("historical execution quote has inverted bid/ask")
        if expected_timestamps is not None and timestamp not in expected_timestamps:
            raise ValueError(f"historical execution quote is not timestamp-aligned: {timestamp}")

        key = (timestamp, strike, option_type)
        if key in seen:
            raise ValueError(f"duplicate historical execution quote: {key}")
        seen.add(key)

        normalized.append(
            ExecutionQuote(
                timestamp=timestamp,
                strike=strike,
                option_type=option_type,
                bid=bid,
                ask=ask,
                spot=_number(row.get("spot")),
                expiry=str(row["expiry"]) if row.get("expiry") is not None else None,
                security_id=str(row["security_id"]) if row.get("security_id") is not None else None,
                source=str(row.get("source") or "external_historical_quotes"),
            )
        )

    return sorted(normalized, key=lambda item: (item.timestamp, item.strike, item.option_type))


def build_execution_grade_snapshots(
    quotes: Iterable[ExecutionQuote],
) -> list[dict[str, Any]]:
    """Build replay snapshots from already validated executable quotes."""
    grouped: dict[int, dict[str, dict[str, dict[str, Any]]]] = {}

    for quote in quotes:
        strike_key = str(int(quote.strike)) if quote.strike.is_integer() else str(quote.strike)
        chain = grouped.setdefault(quote.timestamp, {})
        pair = chain.setdefault(strike_key, {})
        pair[quote.option_type.lower()] = {
            "top_bid_price": quote.bid,
            "top_ask_price": quote.ask,
            "bid": quote.bid,
            "ask": quote.ask,
            "spot": quote.spot,
            "expiry": quote.expiry,
            "security_id": quote.security_id,
            "source": quote.source,
            "execution_grade": True,
        }

    return [
        {"timestamp": timestamp, "oc": chain, "execution_grade": True}
        for timestamp, chain in sorted(grouped.items())
    ]
