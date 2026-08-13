from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.user import User
from main import app


client = TestClient(app)


EMAIL = "portfolio-test@example.com"
PASSWORD = "TestPassword123!"


def clean_test_data():
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == EMAIL
        ).first()

        if user:
            db.query(Holding).filter(
                Holding.user_id == user.id
            ).delete()

            db.delete(user)
            db.commit()

    finally:
        db.close()


def create_user():
    clean_test_data()

    db = SessionLocal()

    try:
        user = User(
            full_name="Portfolio Test",
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id

    finally:
        db.close()


def login():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def auth_headers():
    token = login()

    return {
        "Authorization": f"Bearer {token}"
    }


def test_holdings_requires_authentication():

    response = client.get(
        "/api/v1/portfolio/holdings"
    )

    assert response.status_code == 401


def test_create_holding():

    create_user()

    try:
        response = client.post(
            "/api/v1/portfolio/holdings",
            json={
                "symbol": "reliance",
                "quantity": 10,
                "average_buy_price": 2500,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 201

        data = response.json()

        assert data["symbol"] == "RELIANCE"
        assert float(data["quantity"]) == 10
        assert float(data["average_buy_price"]) == 2500

    finally:
        clean_test_data()


def test_get_holdings():

    user_id = create_user()

    db = SessionLocal()

    try:
        holding = Holding(
            user_id=user_id,
            symbol="TCS",
            quantity=5,
            average_buy_price=3000,
        )

        db.add(holding)
        db.commit()

    finally:
        db.close()

    try:
        response = client.get(
            "/api/v1/portfolio/holdings",
            headers=auth_headers(),
        )

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["symbol"] == "TCS"

    finally:
        clean_test_data()


def test_update_holding():

    user_id = create_user()

    db = SessionLocal()

    try:
        holding = Holding(
            user_id=user_id,
            symbol="INFY",
            quantity=10,
            average_buy_price=1500,
        )

        db.add(holding)
        db.commit()
        db.refresh(holding)

        holding_id = holding.id

    finally:
        db.close()

    try:
        response = client.put(
            f"/api/v1/portfolio/holdings/{holding_id}",
            json={
                "quantity": 20,
                "average_buy_price": 1600,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 200

        data = response.json()

        assert float(data["quantity"]) == 20
        assert float(data["average_buy_price"]) == 1600

    finally:
        clean_test_data()


def test_delete_holding():

    user_id = create_user()

    db = SessionLocal()

    try:
        holding = Holding(
            user_id=user_id,
            symbol="HDFCBANK",
            quantity=5,
            average_buy_price=1700,
        )

        db.add(holding)
        db.commit()
        db.refresh(holding)

        holding_id = holding.id

    finally:
        db.close()

    try:
        response = client.delete(
            f"/api/v1/portfolio/holdings/{holding_id}",
            headers=auth_headers(),
        )

        assert response.status_code == 204

        check = client.get(
            "/api/v1/portfolio/holdings",
            headers=auth_headers(),
        )

        assert check.status_code == 200
        assert check.json() == []

    finally:
        clean_test_data()


def test_user_cannot_modify_another_users_holding():

    create_user()

    db = SessionLocal()

    try:
        first_user = db.query(User).filter(
            User.email == EMAIL
        ).first()

        holding = Holding(
            user_id=first_user.id,
            symbol="AAPL",
            quantity=10,
            average_buy_price=200,
        )

        db.add(holding)
        db.commit()
        db.refresh(holding)

        holding_id = holding.id

        second_user = User(
            full_name="Second User",
            email="portfolio-second@example.com",
            password_hash=hash_password(PASSWORD),
        )

        db.add(second_user)
        db.commit()

    finally:
        db.close()

    try:
        second_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "portfolio-second@example.com",
                "password": PASSWORD,
            },
        )

        assert second_login.status_code == 200

        second_token = second_login.json()["access_token"]

        second_headers = {
            "Authorization": f"Bearer {second_token}"
        }

        response = client.put(
            f"/api/v1/portfolio/holdings/{holding_id}",
            json={
                "quantity": 100,
            },
            headers=second_headers,
        )

        assert response.status_code == 404

    finally:
        db = SessionLocal()

        try:
            second = db.query(User).filter(
                User.email == "portfolio-second@example.com"
            ).first()

            if second:
                db.query(Holding).filter(
                    Holding.user_id == second.id
                ).delete()

                db.delete(second)

            db.commit()

        finally:
            db.close()

        clean_test_data()


def test_invalid_quantity_is_rejected():

    create_user()

    try:
        response = client.post(
            "/api/v1/portfolio/holdings",
            json={
                "symbol": "TCS",
                "quantity": 0,
                "average_buy_price": 3000,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 422

    finally:
        clean_test_data()
