from datetime import datetime, timezone

from fastapi.testclient import TestClient

from main import app
from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import hash_password

client = TestClient(app)
EMAIL = "transaction-ledger-hardening@example.com"
PASSWORD = "TestPassword123!"


def reset_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if user is None:
            user = User(full_name="Ledger Test User", email=EMAIL, password_hash=hash_password(PASSWORD))
            db.add(user)
            db.commit()
            db.refresh(user)
        db.query(Transaction).filter(Transaction.user_id == user.id).delete(synchronize_session=False)
        db.query(Holding).filter(Holding.user_id == user.id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def headers():
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def post(payload, h):
    response = client.post("/api/v1/transactions", json=payload, headers=h)
    assert response.status_code == 201, response.text
    return response.json()


def holding(symbol):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        return db.query(Holding).filter(Holding.user_id == user.id, Holding.symbol == symbol).first()
    finally:
        db.close()


def test_multiple_lots_partial_sells_rebuild_fifo_holding():
    reset_user()
    h = headers()
    post({"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 100, "transaction_date": "2026-01-01T09:00:00Z"}, h)
    post({"symbol": "TCS", "transaction_type": "BUY", "quantity": 10, "price": 200, "transaction_date": "2026-01-02T09:00:00Z"}, h)
    post({"symbol": "TCS", "transaction_type": "SELL", "quantity": 5, "price": 180, "transaction_date": "2026-01-03T09:00:00Z"}, h)
    post({"symbol": "TCS", "transaction_type": "SELL", "quantity": 8, "price": 220, "transaction_date": "2026-01-04T09:00:00Z"}, h)
    item = holding("TCS")
    assert item is not None
    assert item.quantity == 7
    assert round(item.average_buy_price, 2) == round((7 * 200) / 7, 2)


def test_edit_transaction_rebuilds_holding():
    reset_user()
    h = headers()
    first = post({"symbol": "INFY", "transaction_type": "BUY", "quantity": 10, "price": 100}, h)
    post({"symbol": "INFY", "transaction_type": "BUY", "quantity": 10, "price": 200}, h)
    response = client.put(f"/api/v1/transactions/{first['id']}", json={"symbol": "INFY", "transaction_type": "BUY", "quantity": 20, "price": 50}, headers=h)
    assert response.status_code == 200
    item = holding("INFY")
    assert item is not None
    assert item.quantity == 30
    assert round(item.average_buy_price, 2) == round((20 * 50 + 10 * 200) / 30, 2)


def test_delete_transaction_rebuilds_holding():
    reset_user()
    h = headers()
    first = post({"symbol": "RELIANCE", "transaction_type": "BUY", "quantity": 10, "price": 100}, h)
    post({"symbol": "RELIANCE", "transaction_type": "BUY", "quantity": 5, "price": 200}, h)
    response = client.delete(f"/api/v1/transactions/{first['id']}", headers=h)
    assert response.status_code == 204
    item = holding("RELIANCE")
    assert item is not None
    assert item.quantity == 5
    assert item.average_buy_price == 200


def test_invalid_historical_sell_is_rejected_and_rolled_back():
    reset_user()
    h = headers()
    post({"symbol": "HDFCBANK", "transaction_type": "BUY", "quantity": 5, "price": 100}, h)
    response = client.post("/api/v1/transactions", json={"symbol": "HDFCBANK", "transaction_type": "SELL", "quantity": 10, "price": 120}, headers=h)
    assert response.status_code == 400
    item = holding("HDFCBANK")
    assert item is not None and item.quantity == 5


def test_editing_sell_that_breaks_history_is_rejected():
    reset_user()
    h = headers()
    post({"symbol": "SBIN", "transaction_type": "BUY", "quantity": 10, "price": 100}, h)
    sell = post({"symbol": "SBIN", "transaction_type": "SELL", "quantity": 5, "price": 120}, h)
    response = client.put(f"/api/v1/transactions/{sell['id']}", json={"symbol": "SBIN", "transaction_type": "SELL", "quantity": 15, "price": 120}, headers=h)
    assert response.status_code == 400
    item = holding("SBIN")
    assert item is not None and item.quantity == 5
