from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_get_users_returns_working_message():
    response = client.get("/api/v1/users/")

    assert response.status_code == 200
    assert response.json() == {"message": "User endpoint is working"}
