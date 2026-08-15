from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_intraday_signal_requires_auth():
    response = client.post("/api/v1/intraday/signal", json={"opens":[],"highs":[],"lows":[],"closes":[],"volumes":[]})
    assert response.status_code in {401, 403}
