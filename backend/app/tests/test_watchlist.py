from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.watchlist import Watchlist
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "watchlist-test@example.com"
PASSWORD = "TestPassword123!"


def create_user():

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        if user is None:

            user = User(
                full_name="Watchlist Test User",
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        db.query(Watchlist).filter(
            Watchlist.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()


def headers():

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization":
            f"Bearer {response.json()['access_token']}"
    }


def test_watchlist_requires_authentication():

    response = client.get(
        "/api/v1/watchlist"
    )

    assert response.status_code == 401


def test_add_and_list_watchlist():

    create_user()

    response = client.post(
        "/api/v1/watchlist",
        json={
            "symbol": "reliance",
        },
        headers=headers(),
    )

    assert response.status_code == 201
    assert response.json()["symbol"] == "RELIANCE"

    response = client.get(
        "/api/v1/watchlist",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["symbol"] == "RELIANCE"


def test_duplicate_watchlist_is_safe():

    create_user()

    auth = headers()

    first = client.post(
        "/api/v1/watchlist",
        json={"symbol": "TCS"},
        headers=auth,
    )

    second = client.post(
        "/api/v1/watchlist",
        json={"symbol": "TCS"},
        headers=auth,
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        "/api/v1/watchlist",
        headers=auth,
    )

    assert len(response.json()) == 1


@patch(
    "app.api.v1.watchlist.get_quote"
)
def test_watchlist_quotes(mock_quote):

    create_user()

    auth = headers()

    client.post(
        "/api/v1/watchlist",
        json={"symbol": "INFY"},
        headers=auth,
    )

    class Quote:
        price = 1500
        change = 25
        change_percent = 1.69

    mock_quote.return_value = Quote()

    response = client.get(
        "/api/v1/watchlist/quotes",
        headers=auth,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["symbol"] == "INFY"
    assert data[0]["price"] == 1500
    assert data[0]["change"] == 25


def test_delete_watchlist():

    create_user()

    auth = headers()

    response = client.post(
        "/api/v1/watchlist",
        json={"symbol": "HDFCBANK"},
        headers=auth,
    )

    item_id = response.json()["id"]

    response = client.delete(
        f"/api/v1/watchlist/{item_id}",
        headers=auth,
    )

    assert response.status_code == 204

    response = client.get(
        "/api/v1/watchlist",
        headers=auth,
    )

    assert response.json() == []
