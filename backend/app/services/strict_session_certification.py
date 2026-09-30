"""Deterministic certification of raw NSE five-minute sessions.

This module deliberately classifies source timestamps as supplied.  It never
rounds, shifts, fills, resamples, or otherwise repairs bars.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

from app.services.dataset_provenance import fingerprint_market_bars
from app.services.historical_data_service import MarketBar, normalize_bars, validate_dataset, validate_nse_equity_dataset


IST = ZoneInfo("Asia/Kolkata")
EXPECTED_INTERVAL_SECONDS = 300
REGULAR_OPEN = time(9, 15)
REGULAR_LAST = time(15, 25)
TERMINAL_OBSERVATION = time(15, 30)
EXPECTED_BARS = 75


def _expected_timestamps(session_date: date, include_terminal: bool) -> list[datetime]:
    start = datetime.combine(session_date, REGULAR_OPEN, tzinfo=IST)
    count = EXPECTED_BARS + int(include_terminal)
    return [start + timedelta(seconds=EXPECTED_INTERVAL_SECONDS * offset) for offset in range(count)]


def certify_nse_five_minute_session(
    *,
    symbol: str,
    session_date: date,
    rows: Iterable[dict],
    corporate_action_adjusted: bool | None = None,
) -> dict:
    """Classify one raw session as ``STRICT_VALID`` or ``INVALID``.

    A strict session must be the exact 09:15--15:25 five-minute clock grid,
    with one optional 15:30 terminal observation.  Existing quality and NSE
    calendar validators are retained as independent gates.
    """
    bars: list[MarketBar] = normalize_bars(rows)
    actual = [bar.timestamp.astimezone(IST) for bar in bars]
    terminal_timestamp = datetime.combine(session_date, TERMINAL_OBSERVATION, tzinfo=IST)
    include_terminal = len(actual) == EXPECTED_BARS + 1 and actual[-1:] == [terminal_timestamp]
    expected = _expected_timestamps(session_date, include_terminal)
    deltas = [int((current - previous).total_seconds()) for previous, current in zip(actual, actual[1:])]
    exact_grid = actual == expected
    intervals_exact = all(delta == EXPECTED_INTERVAL_SECONDS for delta in deltas)
    generic_quality = validate_dataset(bars, expected_interval_minutes=5)
    nse_quality = validate_nse_equity_dataset(bars, expected_interval_minutes=5)
    content_fingerprint = fingerprint_market_bars(bars, symbol=symbol, timeframe="5m") if bars else None
    strict_valid = bool(
        len(actual) in {EXPECTED_BARS, EXPECTED_BARS + 1}
        and exact_grid
        and intervals_exact
        and generic_quality["valid"]
        and nse_quality["valid"]
    )
    return {
        "symbol": symbol.strip().upper(),
        "session_date": session_date.isoformat(),
        "classification": "STRICT_VALID" if strict_valid else "INVALID",
        "row_count": len(actual),
        "first_timestamp": actual[0].isoformat() if actual else None,
        "last_timestamp": actual[-1].isoformat() if actual else None,
        "expected_interval_seconds": EXPECTED_INTERVAL_SECONDS,
        "interval_validation": {
            "valid": intervals_exact and exact_grid,
            "exact_clock_grid": exact_grid,
            "expected_row_counts": [EXPECTED_BARS, EXPECTED_BARS + 1],
            "observed_delta_counts": dict(sorted(Counter(deltas).items())),
        },
        "nse_calendar_validation": nse_quality,
        "quality_validation": generic_quality,
        "content_fingerprint": content_fingerprint,
        "dataset_fingerprint": content_fingerprint,
        "corporate_action_adjusted": corporate_action_adjusted,
        "corporate_action_state": (
            "ADJUSTED" if corporate_action_adjusted is True
            else "UNADJUSTED" if corporate_action_adjusted is False
            else "UNKNOWN"
        ),
    }


def summarize_certifications(certifications: Sequence[dict]) -> dict:
    """Return deterministic counts suitable for a source-adjacent manifest."""
    by_symbol: dict[str, dict[str, int]] = {}
    for certification in certifications:
        summary = by_symbol.setdefault(certification["symbol"], {"STRICT_VALID": 0, "INVALID": 0})
        summary[certification["classification"]] += 1
    return {
        "sessions": len(certifications),
        "strict_valid_sessions": sum(item["classification"] == "STRICT_VALID" for item in certifications),
        "invalid_sessions": sum(item["classification"] == "INVALID" for item in certifications),
        "by_symbol": {symbol: by_symbol[symbol] for symbol in sorted(by_symbol)},
    }
