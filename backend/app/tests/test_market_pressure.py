from app.services.manipulation_detector import detect_market_pressure


def test_insufficient_data_is_neutral():
    result = detect_market_pressure([100.0] * 10, [101.0] * 10, [99.0] * 10, [1000.0] * 10)
    assert result["risk_level"] == "INSUFFICIENT_DATA"
    assert result["signals"] == []


def test_volume_price_shock_is_flagged():
    closes = [100.0 + i * 0.1 for i in range(30)]
    highs = [value + 1 for value in closes]
    lows = [value - 1 for value in closes]
    volumes = [1000.0] * 29 + [10000.0]
    closes[-1] = closes[-2] * 1.06
    highs[-1] = closes[-1] + 1
    lows[-1] = closes[-1] - 1

    result = detect_market_pressure(closes, highs, lows, volumes)
    names = {signal["name"] for signal in result["signals"]}
    assert "PRICE_VOLUME_SHOCK" in names
    assert result["score"] >= 35


def test_normal_data_does_not_create_false_high_risk():
    closes = [100.0 + i * 0.2 for i in range(40)]
    highs = [value + 1 for value in closes]
    lows = [value - 1 for value in closes]
    volumes = [1000.0 + (i % 3) * 20 for i in range(40)]

    result = detect_market_pressure(closes, highs, lows, volumes)
    assert result["risk_level"] in {"NORMAL", "ELEVATED"}
    assert result["score"] < 50
