from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_allows_vite_development_origin():
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_disallows_unknown_origin():
    response = client.get(
        "/health",
        headers={"Origin": "http://example.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
