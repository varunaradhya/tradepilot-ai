from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from app.services.market_service import MarketDataNotFoundError

client = TestClient(app)


def test_invalid_market_range():
    response = client.get(
        "/api/v1/market/history/AAPL"
        "?range=invalid&interval=1d"
    )

    assert response.status_code == 422


def test_invalid_market_interval():
    response = client.get(
        "/api/v1/market/history/AAPL"
        "?range=1mo&interval=invalid"
    )

    assert response.status_code == 422


@patch("app.api.v1.market.get_quote")
def test_market_provider_error_returns_404(mock_quote):
    mock_quote.side_effect = MarketDataNotFoundError(
        "No market data found"
    )

    response = client.get("/api/v1/market/quote/INVALID")

    assert response.status_code == 404
    assert response.json()["detail"] == "No market data found"


@patch("app.api.v1.market.get_quote")
def test_market_provider_unavailable_returns_503(mock_quote):
    from app.services.market_service import MarketDataProviderError

    mock_quote.side_effect = MarketDataProviderError(
        "Market data provider is temporarily unavailable"
    )

    response = client.get("/api/v1/market/quote/TCS")

    assert response.status_code == 503
    assert response.json()["detail"] == "Market data provider is temporarily unavailable"
