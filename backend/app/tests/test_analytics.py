from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "analytics-test@example.com"
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
                full_name="Analytics Test User",
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        db.query(Transaction).filter(
            Transaction.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.query(Holding).filter(
            Holding.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.commit()

        return user.id

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


def test_analytics_requires_authentication():

    response = client.get(
        "/api/v1/analytics/portfolio"
    )

    assert response.status_code == 401


@patch(
    "app.services.analytics_service.get_quote"
)
def test_analytics_calculates_unrealized_pnl(
    mock_quote,
):

    create_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        db.add(
            Holding(
                user_id=user.id,
                symbol="TCS",
                quantity=10,
                average_buy_price=100,
            )
        )

        db.add(
            Transaction(
                user_id=user.id,
                symbol="TCS",
                transaction_type="BUY",
                quantity=10,
                price=100,
            )
        )

        db.commit()

    finally:
        db.close()

    class Quote:
        price = 120

    mock_quote.return_value = Quote()

    response = client.get(
        "/api/v1/analytics/portfolio",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_invested"] == 1000
    assert data["current_value"] == 1200
    assert data["unrealized_profit_loss"] == 200
    assert data["unrealized_profit_loss_percent"] == 20
    assert data["total_profit_loss"] == 200
    assert data["total_return_percent"] == 20


def test_analytics_calculates_realized_pnl():

    create_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        db.add_all(
            [
                Transaction(
                    user_id=user.id,
                    symbol="INFY",
                    transaction_type="BUY",
                    quantity=10,
                    price=100,
                ),
                Transaction(
                    user_id=user.id,
                    symbol="INFY",
                    transaction_type="SELL",
                    quantity=5,
                    price=130,
                ),
            ]
        )

        db.commit()

    finally:
        db.close()

    response = client.get(
        "/api/v1/analytics/portfolio",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["realized_profit_loss"] == 150


def test_empty_analytics():

    create_user()

    response = client.get(
        "/api/v1/analytics/portfolio",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_invested"] == 0
    assert data["current_value"] == 0
    assert data["total_profit_loss"] == 0
    assert data["holdings_count"] == 0
