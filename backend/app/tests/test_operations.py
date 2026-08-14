from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_does_not_expose_secrets():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "not_ready"}
    assert "password" not in str(response.json()).lower()
