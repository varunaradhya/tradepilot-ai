from datetime import datetime, timezone

from app.services.market_data_quality import is_indian_cash_market_time, validate_intraday_candles


def _bar(minute: int, *, day: int = 14, open_price: float = 100, high: float = 101, low: float = 99, close: float = 100):
    return {
        "timestamp": datetime(2026, 8, day, 9, minute, tzinfo=timezone.utc),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1000,
    }


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


def test_market_data_quality_rejects_invalid_ohlc():
    rows = [_bar(15, open_price=110, high=101, low=99, close=100)]
    result = validate_intraday_candles(rows, stale_after_minutes=99999)
    assert result.valid is False
    assert result.invalid_ohlc == 1
    assert result.reason == "INVALID_OHLC"


def test_market_data_quality_rejects_weekend_data():
    # 2026-08-15 is Saturday.
    rows = [_bar(15, day=15)]
    result = validate_intraday_candles(rows, stale_after_minutes=99999)
    assert result.valid is False
    assert result.non_trading_day == 1
    assert result.reason == "NON_TRADING_DAY"


def test_indian_cash_market_session_boundary():
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 9, 15).time()) is True
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 15, 30).time()) is True
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 15, 31).time()) is False
