from __future__ import annotations

from app.services.intraday_strategy_v2 import (
    IntradayV2AConfig,
    generate_intraday_v2a_signal,
)


def _series(final_close: float = 101.6, final_high: float = 101.9):
    opens = [99.8, 100.0, 100.2]
    highs = [100.5, 100.7, 101.0]
    lows = [99.5, 99.7, 99.9]
    closes = [100.2, 100.5, 100.8]
    volumes = [1000.0, 1000.0, 1000.0]
    for i in range(22):
        base = 100.7 + i * 0.01
        opens.append(base)
        highs.append(base + 0.45)
        lows.append(base - 0.45)
        closes.append(base + 0.25)
        volumes.append(1100.0)
    opens.append(101.25)
    highs.append(final_high)
    lows.append(100.9)
    closes.append(final_close)
    volumes.append(2200.0)
    return opens, highs, lows, closes, volumes


def test_v2a_accepts_strong_breakout_without_market_data():
    opens, highs, lows, closes, volumes = _series()
    signal = generate_intraday_v2a_signal(
        opens,
        highs,
        lows,
        closes,
        volumes,
        opening_high=101.0,
        config=IntradayV2AConfig(),
    )

    assert signal["action"] == "BUY"
    assert signal["reason"] == "ORB_V2A_QUALITY_CONFIRMED"
    assert signal["checks"]["opening_breakout"] is True
    assert signal["checks"]["breakout_distance"] is True
    assert signal["checks"]["close_location"] is True
    assert signal["checks"]["range_expansion"] is True
    assert signal["checks"]["vwap"] is True
    assert "market_closes" not in signal


def test_v2a_rejects_extended_breakout():
    opens, highs, lows, closes, volumes = _series(final_close=106.0, final_high=106.5)
    signal = generate_intraday_v2a_signal(
        opens,
        highs,
        lows,
        closes,
        volumes,
        opening_high=101.0,
        config=IntradayV2AConfig(),
    )

    assert signal["action"] == "NEUTRAL"
    assert signal["reason"] == "BREAKOUT_QUALITY_FILTER"
    assert "breakout_distance" in signal["failed_checks"]


def test_v2a_does_not_require_market_or_sector_context():
    opens, highs, lows, closes, volumes = _series()
    signal = generate_intraday_v2a_signal(
        opens,
        highs,
        lows,
        closes,
        volumes,
        market_closes=None,
        sector_closes=None,
        opening_high=101.0,
    )

    assert signal["action"] in {"BUY", "NEUTRAL"}
    assert "checks" in signal


def test_v2a_handles_zero_range_breakout_bar_without_key_error():
    opens = [100.0] * 25
    highs = [101.0] * 25
    lows = [99.0] * 25
    closes = [100.5] * 25
    volumes = [1000.0] * 25
    opens[-1] = highs[-1] = lows[-1] = closes[-1] = 102.0

    signal = generate_intraday_v2a_signal(
        opens,
        highs,
        lows,
        closes,
        volumes,
        opening_high=101.0,
    )

    assert signal["action"] == "NEUTRAL"
    assert "checks" in signal
    assert signal["breakout_quality"]["bullish_body"] is False
