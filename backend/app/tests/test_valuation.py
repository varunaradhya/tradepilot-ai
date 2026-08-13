from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "valuation@example.com"
PASSWORD = "TestPassword123!"


def create_test_user():
    db = SessionLocal()

    try:
        existing = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        if existing:
            user_id = existing.id

            db.query(Holding).filter(
                Holding.user_id == user_id
            ).delete(
                synchronize_session=False
            )

            db.commit()

        else:
            user = User(
                full_name="Valuation User",
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            user_id = user.id

        return user_id

    finally:
        db.close()

def auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_valuation_requires_authentication():

    response = client.get(
        "/api/v1/portfolio/valuation"
    )

    assert response.status_code == 401


@patch("app.services.valuation_service.get_quote")
def test_empty_portfolio_valuation(mock_quote):

    create_test_user()

    response = client.get(
        "/api/v1/portfolio/valuation",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_invested"] == 0
    assert data["summary"]["current_value"] == 0
    assert data["summary"]["profit_loss"] == 0
    assert data["summary"]["profit_loss_percent"] == 0
    assert data["summary"]["holdings_count"] == 0
    assert data["holdings"] == []

    mock_quote.assert_not_called()


@patch("app.services.valuation_service.get_quote")
def test_portfolio_valuation(mock_quote):

    create_test_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        holding = Holding(
            user_id=user.id,
            symbol="TEST",
            quantity=10,
            average_buy_price=100,
        )

        db.add(holding)
        db.commit()

    finally:
        db.close()

    class Quote:
        price = 120.0

    mock_quote.return_value = Quote()

    response = client.get(
        "/api/v1/portfolio/valuation",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_invested"] == 1000
    assert data["summary"]["current_value"] == 1200
    assert data["summary"]["profit_loss"] == 200
    assert data["summary"]["profit_loss_percent"] == 20
    assert data["summary"]["holdings_count"] == 1

    holding = data["holdings"][0]

    assert holding["symbol"] == "TEST"
    assert holding["quantity"] == 10
    assert holding["average_buy_price"] == 100
    assert holding["invested_amount"] == 1000
    assert holding["current_price"] == 120
    assert holding["current_value"] == 1200
    assert holding["profit_loss"] == 200
    assert holding["profit_loss_percent"] == 20


@patch("app.services.valuation_service.get_quote")
def test_multiple_holdings_are_aggregated(mock_quote):

    create_test_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        db.query(Holding).filter(
            Holding.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.query(Holding).filter(
            Holding.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.add_all(
            [
                Holding(
                    user_id=user.id,
                    symbol="AAA",
                    quantity=10,
                    average_buy_price=100,
                ),
                Holding(
                    user_id=user.id,
                    symbol="BBB",
                    quantity=20,
                    average_buy_price=50,
                ),
            ]
        )

        db.commit()

    finally:
        db.close()

    class Quote:
        def __init__(self, price):
            self.price = price

    def quote_side_effect(symbol):

        if symbol == "AAA":
            return Quote(120)

        return Quote(60)

    mock_quote.side_effect = quote_side_effect

    response = client.get(
        "/api/v1/portfolio/valuation",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_invested"] == 2000
    assert data["summary"]["current_value"] == 2400
    assert data["summary"]["profit_loss"] == 400
    assert data["summary"]["profit_loss_percent"] == 20
    assert data["summary"]["holdings_count"] == 2
