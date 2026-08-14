from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai.context import build_portfolio_context, build_stock_context
from app.ai.providers.mock import MockAIProvider
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.broker_connection import BrokerConnection
from app.models.holding import Holding
from app.models.user import User
from app.models.watchlist import Watchlist
from app.providers.market_data import HistoricalData, QuoteData
from main import app

client = TestClient(app)
EMAIL = "ai-intelligence-test@example.com"
PASSWORD = "TestPassword123!"


def _quote(symbol):
    return QuoteData(symbol=symbol, name="Test", currency="INR", exchange="TEST", price=120.0, previous_close=119.0, change=1.0, change_percent=0.84, market_time=datetime(2026, 1, 1))


def _history(symbol, range_="6mo", interval="1d"):
    data = [{"close": float(index), "high": float(index + 1), "low": float(index - 1), "volume": 1000.0} for index in range(1, 65)]
    return HistoricalData(symbol=symbol, currency="INR", interval=interval, range=range_, data=data)


def _clean():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if user:
            db.query(BrokerConnection).filter(BrokerConnection.user_id == user.id).delete()
            db.query(Watchlist).filter(Watchlist.user_id == user.id).delete()
            db.query(Holding).filter(Holding.user_id == user.id).delete()
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _user_and_headers():
    _clean()
    db = SessionLocal()
    try:
        user = User(full_name="AI Test", email=EMAIL, password_hash=hash_password(PASSWORD))
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    return user_id, {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_mock_provider_is_deterministic_and_validates_context():
    context = {"analysis_type": "watchlist", "watchlist": [], "market_data": {"failures": [], "unavailable_symbols": []}}
    provider = MockAIProvider()
    first = provider.analyze(context)
    second = provider.analyze(context)
    assert {key: first[key] for key in first if key != "generated_at"} == {key: second[key] for key in second if key != "generated_at"}
    assert first["signal"] == "NEUTRAL"
    try:
        provider.analyze({})
    except ValueError:
        pass
    else:
        assert False, "Malformed context must be rejected"


@patch("app.ai.context.get_history", side_effect=_history)
@patch("app.ai.context.get_quote", side_effect=_quote)
def test_portfolio_context_is_sanitized_and_has_metrics(mock_quote, mock_history):
    user_id, _ = _user_and_headers()
    db = SessionLocal()
    try:
        db.add(Holding(user_id=user_id, symbol="TCS", quantity=Decimal("2"), average_buy_price=Decimal("100")))
        db.add(BrokerConnection(user_id=user_id, broker_name="dhan", client_id="secret-client", encrypted_access_token="secret-token"))
        db.commit()
        context = build_portfolio_context(db, user_id)
    finally:
        db.close()
        _clean()
    assert context["portfolio"]["holdings_count"] == 1
    assert context["holdings"][0]["symbol"] == "TCS"
    assert context["brokers"] == {"connected_names": ["dhan"]}
    assert "secret-token" not in str(context)
    assert "secret-client" not in str(context)


@patch("app.ai.context.get_history", side_effect=_history)
@patch("app.ai.context.get_quote", side_effect=_quote)
def test_stock_context_and_endpoints(mock_quote, mock_history):
    _, headers = _user_and_headers()
    try:
        response = client.get("/api/v1/intelligence/stock/TCS", headers=headers)
        assert response.status_code == 200
        assert response.json()["analysis"]["signal"] in {"BUY", "HOLD", "SELL", "NEUTRAL"}
        assert 0 <= response.json()["analysis"]["confidence"] <= 100
        assert client.get("/api/v1/intelligence/portfolio").status_code == 401
        assert client.get("/api/v1/intelligence/stock/invalid symbol", headers=headers).status_code == 422
        assert build_stock_context("TCS")["stock"]["symbol"] == "TCS"
    finally:
        _clean()


@patch("app.ai.context.get_history", side_effect=_history)
@patch("app.ai.context.get_quote", side_effect=_quote)
def test_portfolio_and_empty_watchlist_endpoints(mock_quote, mock_history):
    _, headers = _user_and_headers()
    try:
        portfolio = client.get("/api/v1/intelligence/portfolio", headers=headers)
        watchlist = client.get("/api/v1/intelligence/watchlist", headers=headers)
        assert portfolio.status_code == 200
        assert portfolio.json()["analysis"]["signal"] == "NEUTRAL"
        assert watchlist.status_code == 200
        assert watchlist.json()["analysis"]["watch_items"] == []
    finally:
        _clean()
