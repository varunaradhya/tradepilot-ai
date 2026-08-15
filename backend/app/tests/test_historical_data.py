from datetime import datetime, timedelta, timezone

import pytest

from app.services.historical_data_service import normalize_bars, validate_dataset


def test_normalize_bars_sorts_and_preserves_ohlcv():
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = [
        {"timestamp": (start + timedelta(days=1)).isoformat(), "open": 101, "high": 105, "low": 100, "close": 104, "volume": 2000},
        {"timestamp": start.isoformat(), "open": 100, "high": 103, "low": 99, "close": 101, "volume": 1500},
    ]
    bars = normalize_bars(rows)
    assert bars[0].close == 101
    assert bars[1].close == 104
    assert validate_dataset(bars)["valid"] is True


def test_normalize_bars_rejects_invalid_ohlc():
    with pytest.raises(ValueError, match="Invalid OHLC"):
        normalize_bars([{"timestamp": "2026-01-01T00:00:00+00:00", "open": 100, "high": 90, "low": 80, "close": 85}])


def test_validate_dataset_flags_duplicate_timestamps():
    row = {"timestamp": "2026-01-01T00:00:00+00:00", "open": 100, "high": 105, "low": 95, "close": 102}
    bars = normalize_bars([row, row])
    result = validate_dataset(bars)
    assert result["valid"] is False
    assert result["duplicates"] == 1
