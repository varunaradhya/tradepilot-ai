from datetime import datetime, timezone

from app.services.market_data_quality import validate_intraday_candles


def _bar(day: int, hour: int, minute: int):
    return {
        "timestamp": datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc),
        "open": 100,
        "high": 101,
        "low": 99,
        "close": 100,
        "volume": 1000,
    }


def test_session_boundary_does_not_create_missing_candles():
    rows = [_bar(14, 9, 30), _bar(15, 3, 45)]
    result = validate_intraday_candles(rows, expected_minutes=5, stale_after_minutes=99999)
    assert result.missing_intervals == 0
