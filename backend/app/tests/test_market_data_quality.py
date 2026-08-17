from datetime import datetime, timezone

from app.services.market_data_quality import is_indian_cash_market_time, validate_intraday_candles


def _bar(minute: int, *, hour: int = 9, day: int = 14, open_price: float = 100, high: float = 101, low: float = 99, close: float = 100):
    return {
        "timestamp": datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc),
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


def test_market_data_quality_does_not_count_overnight_as_missing():
    rows = [_bar(25, hour=15, day=14), _bar(15, hour=9, day=15)]
    result = validate_intraday_candles(rows, expected_minutes=5, stale_after_minutes=99999)
    assert result.missing_intervals == 0


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
    rows = [_bar(15, day=15)]
    result = validate_intraday_candles(rows, stale_after_minutes=99999)
    assert result.valid is False
    assert result.non_trading_day == 1
    assert result.reason == "NON_TRADING_DAY"


def test_market_data_quality_rejects_outside_session():
    # 03:00 UTC = 08:30 IST, before the cash session.
    rows = [_bar(0, hour=3)]
    result = validate_intraday_candles(rows, stale_after_minutes=99999)
    assert result.valid is False
    assert result.outside_session == 1
    assert result.reason == "OUTSIDE_MARKET_SESSION"


def test_historical_data_is_not_marked_stale_without_reference_time():
    rows = [_bar(15)]
    result = validate_intraday_candles(rows, stale_after_minutes=1)
    assert result.stale is False
    assert result.valid is True


def test_live_reference_time_marks_stale_data():
    rows = [_bar(15)]
    reference = datetime(2026, 8, 14, 9, 40, tzinfo=timezone.utc)
    result = validate_intraday_candles(rows, stale_after_minutes=15, reference_time=reference)
    assert result.stale is True
    assert result.valid is False
    assert result.reason == "STALE_DATA"


def test_indian_cash_market_session_boundary():
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 9, 15).time()) is True
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 15, 30).time()) is True
    assert is_indian_cash_market_time(datetime(2026, 8, 14, 15, 31).time()) is False
