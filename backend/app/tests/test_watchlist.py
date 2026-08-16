from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.watchlist import Watchlist
from app.models.user import User
from app.providers.market_search import SearchInstrument
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
        if user:
            return user

        user = User(
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
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
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_add_and_list_watchlist(monkeypatch):

    create_user()
    monkeypatch.setattr(
        "app.services.instrument_service._search_provider.search",
        lambda query: [
            SearchInstrument(
                symbol="RELIANCE",
                name="Reliance Industries Limited",
                exchange="NSE",
            )
        ],
    )

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

    response = client.post(
        "/api/v1/watchlist",
        json={
            "symbol": "reliance",
        },
        headers=headers(),
    )

    assert response.status_code == 201

    response = client.post(
        "/api/v1/watchlist",
        json={
            "symbol": "reliance",
        },
        headers=headers(),
    )

    assert response.status_code == 201

    response = client.get(
        "/api/v1/watchlist",
        headers=headers(),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
