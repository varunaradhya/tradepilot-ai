from datetime import datetime

from app.services.historical_data_service import normalize_bars, validate_dataset, validate_nse_equity_dataset


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


def test_validate_nse_equity_dataset_rejects_outside_regular_session():
    rows = [
        {"timestamp": "2026-01-05T09:10:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"timestamp": "2026-01-05T09:15:00+05:30", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
    ]
    result = validate_nse_equity_dataset(normalize_bars(rows), expected_interval_minutes=5)
    assert result["valid"] is False
    assert result["pre_market_bars"] == 1
    assert result["outside_session_bars"] == 1


def test_validate_nse_equity_dataset_rejects_weekend_and_holiday_bars():
    weekend = validate_nse_equity_dataset(normalize_bars([
        {"timestamp": "2026-01-03T09:15:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
    ]))
    holiday = validate_nse_equity_dataset(normalize_bars([
        {"timestamp": "2026-01-26T09:15:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
    ]))
    assert weekend["weekend_bars"] == 1
    assert weekend["valid"] is False
    assert holiday["holiday_bars"] == 1
    assert holiday["valid"] is False


def test_validate_nse_equity_dataset_detects_missing_trading_session():
    rows = [
        {"timestamp": "2026-01-02T09:15:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"timestamp": "2026-01-06T09:15:00+05:30", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
    ]
    result = validate_nse_equity_dataset(normalize_bars(rows))
    assert result["valid"] is False
    assert result["missing_session_dates"] == ["2026-01-05"]


def test_validate_nse_equity_dataset_detects_mixed_source_timezones():
    rows = [
        {"timestamp": "2026-01-05T09:15:00+05:30", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10},
        {"timestamp": "2026-01-05T03:50:00+00:00", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
    ]
    result = validate_nse_equity_dataset(normalize_bars(rows))
    assert result["valid"] is False
    assert result["timezone_inconsistencies"] == 1
