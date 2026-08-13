from app.services.signal_service import generate_signal


def test_signal_contains_required_fields():
    prices = list(range(1, 80))
    result = generate_signal("TEST", prices)

    assert result["symbol"] == "TEST"
    assert result["signal"] in {"BUY", "HOLD", "SELL"}
    assert 0 <= result["confidence"] <= 100
    assert isinstance(result["reasons"], list)
    assert "indicators" in result
    assert result["data_status"] == "AVAILABLE"


def test_insufficient_data_does_not_create_trade_signal():
    result = generate_signal("TEST", [1, 2, 3])

    assert result["signal"] == "HOLD"
    assert result["data_status"] == "INSUFFICIENT_DATA"
