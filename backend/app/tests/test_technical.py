from app.services.technical_service import (
    atr,
    bollinger,
    ema,
    sma,
    macd,
    momentum,
    rsi,
    technical_snapshot,
)


def test_ema_returns_value():
    assert ema([1, 2, 3, 4, 5], 3) is not None


def test_rsi_rising_market():
    value = rsi(list(range(1, 20)))
    assert value is not None
    assert value == 100.0


def test_macd_shape():
    result = macd(list(range(1, 40)))
    assert set(result) == {"macd", "signal", "histogram"}


def test_bollinger_shape():
    result = bollinger(list(range(1, 30)))
    assert result["upper"] >= result["middle"] >= result["lower"]


def test_atr_returns_value():
    values = list(range(1, 40))
    result = atr(values, [x - 1 for x in values], values)
    assert result is not None
    assert result >= 0


def test_momentum():
    assert momentum(list(range(1, 12)), 10) > 0


def test_snapshot_trend():
    result = technical_snapshot(list(range(1, 60)))
    assert result["trend"] == "BULLISH"


def test_sma_and_indicators_require_enough_data():
    assert sma([1, 2, 3], 5) is None
    assert ema([1, 2, 3], 5) is None
    assert rsi([1, 2, 3], 14) is None
    assert macd(list(range(1, 34)))["macd"] is None
