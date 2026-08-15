from fastapi.testclient import TestClient

from main import app
from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import hash_password

client = TestClient(app)
EMAIL = "transaction-test@example.com"
PASSWORD = "TestPassword123!"


def create_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if user is None:
            user = User(full_name="Transaction Test User", email=EMAIL, password_hash=hash_password(PASSWORD))
            db.add(user)
            db.commit()
            db.refresh(user)
        db.query(Transaction).filter(Transaction.user_id == user.id).delete(synchronize_session=False)
        db.query(Holding).filter(Holding.user_id == user.id).delete(synchronize_session=False)
        db.commit()
        return user.id
    finally:
        db.close()


def auth_headers():
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_transactions_require_authentication():
    assert client.get("/api/v1/transactions").status_code == 401


def test_buy_transaction_creates_holding():
    create_user()
    response = client.post("/api/v1/transactions", json={"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 3000}, headers=auth_headers())
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "TCS"
    assert data["transaction_type"] == "BUY"
    assert data["quantity"] == 10
    assert data["price"] == 3000


def test_multiple_buys_calculate_weighted_average():
    create_user()
    headers = auth_headers()
    for price in (1000, 1200):
        assert client.post("/api/v1/transactions", json={"symbol": "INFY", "transaction_type": "BUY", "quantity": 10, "price": price}, headers=headers).status_code == 201
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        holding = db.query(Holding).filter(Holding.user_id == user.id, Holding.symbol == "INFY").first()
        assert holding is not None
        assert holding.quantity == 20
        assert holding.average_buy_price == 1100
    finally:
        db.close()


def test_sell_transaction_reduces_holding():
    create_user()
    headers = auth_headers()
    assert client.post("/api/v1/transactions", json={"symbol": "RELIANCE", "transaction_type": "BUY", "quantity": 20, "price": 2500}, headers=headers).status_code == 201
    assert client.post("/api/v1/transactions", json={"symbol": "RELIANCE", "transaction_type": "SELL", "quantity": 5, "price": 2800}, headers=headers).status_code == 201
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        holding = db.query(Holding).filter(Holding.user_id == user.id, Holding.symbol == "RELIANCE").first()
        assert holding is not None
        assert holding.quantity == 15
        assert holding.average_buy_price == 2500
    finally:
        db.close()


def test_sell_more_than_holding_is_rejected():
    create_user()
    headers = auth_headers()
    assert client.post("/api/v1/transactions", json={"symbol": "HDFC", "transaction_type": "BUY", "quantity": 5, "price": 1500}, headers=headers).status_code == 201
    response = client.post("/api/v1/transactions", json={"symbol": "HDFC", "transaction_type": "SELL", "quantity": 10, "price": 1600}, headers=headers)
    assert response.status_code == 400


def test_invalid_transaction_type_is_rejected():
    create_user()
    response = client.post("/api/v1/transactions", json={"symbol": "TCS", "transaction_type": "INVALID", "quantity": 10, "price": 3000}, headers=auth_headers())
    assert response.status_code == 422


def test_transaction_history():
    create_user()
    headers = auth_headers()
    client.post("/api/v1/transactions", json={"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 3000}, headers=headers)
    client.post("/api/v1/transactions", json={"symbol": "INFY", "transaction_type": "BUY", "quantity": 5, "price": 1500}, headers=headers)
    response = client.get("/api/v1/transactions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_transactions"] == 2
    assert len(data["transactions"]) == 2


def test_transaction_summary_realized_pnl_uses_fifo():
    create_user()
    headers = auth_headers()
    for payload in [
        {"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 100},
        {"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 200},
        {"symbol": "TCS", "transaction_type": "SELL", "quantity": 5, "price": 180},
    ]:
        assert client.post("/api/v1/transactions", json=payload, headers=headers).status_code == 201
    data = client.get("/api/v1/transactions", headers=headers).json()
    assert data["summary"]["realized_profit_loss"] == 400


def test_transaction_belongs_to_user():
    create_user()
    headers = auth_headers()
    response = client.post("/api/v1/transactions", json={"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 3000}, headers=headers)
    assert response.status_code == 201
    transaction_id = response.json()["id"]
    response = client.get(f"/api/v1/transactions/{transaction_id}", headers=headers)
    assert response.status_code == 200
