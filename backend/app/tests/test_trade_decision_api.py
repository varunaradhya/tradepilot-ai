from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.trade_decision import get_current_user
from app.providers.market_search import MarketSearchProviderError, SearchInstrument
from main import app


client = TestClient(app)


def _payload(symbol: str) -> dict:
    closes = [100 + i * 0.35 for i in range(30)]
    return {
        "symbol": symbol,
        "session": "2026-09-28",
        "closes": closes,
        "highs": [x + 0.5 for x in closes],
        "lows": [x - 0.5 for x in closes],
        "volumes": [1000] * 29 + [1500],
        "equity": 100000,
        "broker": "DHAN",
        "opening_high": 108,
    }


def setup_function():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)


def teardown_function():
    app.dependency_overrides.pop(get_current_user, None)


def test_trade_decision_rejects_non_indian_symbol(monkeypatch):
    monkeypatch.setattr("app.api.v1.trade_decision.search_instruments", lambda query: [])

    response = client.post("/api/v1/trade-decision/paper", json=_payload("AAPL"))

    assert response.status_code == 422
    assert "Indian NSE/BSE equity universe" in response.json()["detail"]


def test_trade_decision_normalizes_indian_suffix_before_validation(monkeypatch):
    seen = []

    def fake_search(query):
        seen.append(query)
        return [SearchInstrument("TCS", "Tata Consultancy Services", "NSE")]

    monkeypatch.setattr("app.api.v1.trade_decision.search_instruments", fake_search)

    response = client.post("/api/v1/trade-decision/paper", json=_payload("tcs.ns"))

    assert response.status_code == 200
    assert response.json()["symbol"] == "TCS"
    assert seen == ["TCS"]


def test_trade_decision_fails_closed_when_symbol_validation_provider_is_unavailable(monkeypatch):
    def unavailable(_query):
        raise MarketSearchProviderError("provider unavailable")

    monkeypatch.setattr("app.api.v1.trade_decision.search_instruments", unavailable)

    response = client.post("/api/v1/trade-decision/paper", json=_payload("TCS"))

    assert response.status_code == 503
    assert "validation is temporarily unavailable" in response.json()["detail"]
