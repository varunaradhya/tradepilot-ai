from datetime import datetime

from app.services.historical_data_service import normalize_bars, validate_dataset


def test_validate_dataset_detects_interval_gap():
    rows = [
        {"timestamp": "2026-01-01T09:15:00+00:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"timestamp": "2026-01-01T09:25:00+00:00", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
    ]
    result = validate_dataset(normalize_bars(rows), expected_interval_minutes=5)
    assert result["valid"] is False
    assert result["interval_gaps"] == 1


def test_normalize_bars_makes_naive_timestamps_utc_aware():
    bars = normalize_bars([
        {"timestamp": datetime(2026, 1, 1, 9, 15), "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10}
    ])
    assert bars[0].timestamp.tzinfo is not None


def test_validate_dataset_accepts_expected_interval():
    rows = [
        {"timestamp": "2026-01-01T09:15:00+00:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"timestamp": "2026-01-01T09:20:00+00:00", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
    ]
    result = validate_dataset(normalize_bars(rows), expected_interval_minutes=5)
    assert result["valid"] is True
    assert result["interval_gaps"] == 0
