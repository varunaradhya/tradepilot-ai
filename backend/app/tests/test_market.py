from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from app.services.market_service import MarketDataNotFoundError, MarketDataProviderError

client = TestClient(app)


def fake_quote(symbol):
    from app.providers.market_data import QuoteData

    return QuoteData(
        symbol=symbol.upper(), name="Test Company", currency="USD", exchange="TEST",
        price=100.0, previous_close=95.0, change=5.0,
        change_percent=5.2631578947, market_time=datetime(2026, 1, 1, 10, 0, 0),
    )


def fake_history(symbol, range_="1mo", interval="1d"):
    from app.providers.market_data import HistoricalData

    return HistoricalData(
        symbol=symbol.upper(), currency="USD", interval=interval, range=range_,
        data=[{"timestamp": datetime(2026, 1, 1), "open": 95.0, "high": 102.0,
               "low": 94.0, "close": 100.0, "volume": 100000}],
    )


@patch("app.api.v1.market.get_quote", side_effect=fake_quote)
def test_get_market_quote(mock_quote):
    response = client.get("/api/v1/market/quote/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["price"] == 100.0
    assert data["previous_close"] == 95.0
    assert data["change"] == 5.0
    mock_quote.assert_called_once_with("AAPL")


@patch("app.api.v1.market.get_history", side_effect=fake_history)
def test_get_market_history(mock_history):
    response = client.get("/api/v1/market/history/AAPL?range=1mo&interval=1d")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["range"] == "1mo"
    assert data["interval"] == "1d"
    assert len(data["data"]) == 1
    assert data["data"][0]["close"] == 100.0
    mock_history.assert_called_once_with(symbol="AAPL", range_="1mo", interval="1d")


def test_invalid_market_range():
    response = client.get("/api/v1/market/history/AAPL?range=invalid&interval=1d")
    assert response.status_code == 422


def test_invalid_market_interval():
    response = client.get("/api/v1/market/history/AAPL?range=1mo&interval=invalid")
    assert response.status_code == 422


@patch("app.api.v1.market.get_quote")
def test_market_not_found_returns_404(mock_quote):
    mock_quote.side_effect = MarketDataNotFoundError("No market data found")
    response = client.get("/api/v1/market/quote/INVALID")
    assert response.status_code == 404
    assert response.json()["detail"] == "No market data found"


@patch("app.api.v1.market.get_quote")
def test_market_provider_error_returns_503(mock_quote):
    mock_quote.side_effect = MarketDataProviderError("Provider unavailable")
    response = client.get("/api/v1/market/quote/TCS")
    assert response.status_code == 503
    assert response.json()["detail"] == "Provider unavailable"
