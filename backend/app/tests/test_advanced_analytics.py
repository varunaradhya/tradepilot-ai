from app.services.advanced_analytics_service import calculate_advanced_analytics


class Holding:
    def __init__(self, symbol, quantity, average_buy_price):
        self.symbol, self.quantity, self.average_buy_price = symbol, quantity, average_buy_price


def test_advanced_analytics_does_not_fabricate_missing_prices():
    result = calculate_advanced_analytics([Holding("TCS", 2, 100), Holding("INFY", 1, 200)], {"TCS": 120}, {"TCS": [100, 110, 120]})
    assert result["current_value"] == 240
    assert result["unavailable_symbols"] == ["INFY"]
    assert result["concentration_percent"] == 100


def test_advanced_analytics_empty_portfolio():
    result = calculate_advanced_analytics([], {})
    assert result["risk_summary"] == "NO_MARKET_DATA"
    assert result["holdings"] == []
