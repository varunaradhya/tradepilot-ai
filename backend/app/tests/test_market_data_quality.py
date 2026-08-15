from datetime import datetime, timezone

from app.services.market_data_quality import is_indian_cash_market_time, validate_intraday_candles


def _bar(minute: int):
    return {"timestamp": datetime(2026, 8, 14, 9, minute, tzinfo=timezone.utc)}


def test_market_data_quality_rejects_duplicates():
    rows = [_bar(15), _bar(20), _bar(20)]
    result = validate_intraday_candles(rows, expected_minutes=5, stale_after_minutes=99999)
    assert result.valid is False
    assert result.duplicate is True
    assert result.reason == "DUPLICATE_CANDLE"


def test_market_data_quality_detects_missing_intervals():
    rows = [_bar(15), _bar(20), _bar(30)]
    result = validate_intraday_candles(rows, expected_minutes=5, stale_after_minutes=99999)
    assert result.missing_intervals == 1
    assert result.reason == "MISSING_INTERVALS"


def test_market_data_quality_detects_out_of_order_bars():
    rows = [_bar(20), _bar(15)]
    result = validate_intraday_candles(rows, expected_minutes=5, stale_after_minutes=99999)
    assert result.valid is False
    assert result.out_of_order is True


def test_indian_cash_market_session_boundary():
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 9, 15).time()) is True
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 15, 30).time()) is True
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 15, 31).time()) is False
