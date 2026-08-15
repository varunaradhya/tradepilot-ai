from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_market_bar_requires_auth():
    response = client.post(
        "/api/v1/paper-trading/session/market-bar",
        json={"session":"2026-08-15","symbol":"TCS","open":100,"high":101,"low":99,"close":100.5,"volume":1000},
    )
    assert response.status_code in {401, 403}


def test_dhan_paper_session_requires_auth():
    response = client.post(
        "/api/v1/paper-trading/session/dhan",
        json={"symbol":"TCS","session":"2026-08-14","interval":"5"},
    )
    assert response.status_code in {401, 403}


def test_readiness_requires_auth():
    response = client.get("/api/v1/paper-trading/readiness")
    assert response.status_code in {401, 403}
