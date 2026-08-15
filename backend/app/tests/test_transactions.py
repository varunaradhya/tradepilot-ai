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


def post_trade(headers, symbol, tx_type, quantity, price, transaction_date=None):
    payload = {"symbol": symbol, "transaction_type": tx_type, "quantity": quantity, "price": price}
    if transaction_date:
        payload["transaction_date"] = transaction_date
    return client.post("/api/v1/transactions", json=payload, headers=headers)


def get_holding(symbol):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        return db.query(Holding).filter(Holding.user_id == user.id, Holding.symbol == symbol).first()
    finally:
        db.close()


def test_transactions_require_authentication():
    assert client.get("/api/v1/transactions").status_code == 401


def test_buy_transaction_creates_holding():
    create_user()
    response = post_trade(auth_headers(), "TCS", "BUY", 10, 3000)
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
        assert post_trade(headers, "INFY", "BUY", 10, price).status_code == 201
    holding = get_holding("INFY")
    assert holding is not None
    assert float(holding.quantity) == 20
    assert float(holding.average_buy_price) == 1100


def test_sell_transaction_reduces_holding():
    create_user()
    headers = auth_headers()
    assert post_trade(headers, "RELIANCE", "BUY", 20, 2500).status_code == 201
    assert post_trade(headers, "RELIANCE", "SELL", 5, 2800).status_code == 201
    holding = get_holding("RELIANCE")
    assert holding is not None
    assert float(holding.quantity) == 15
    assert float(holding.average_buy_price) == 2500


def test_sell_more_than_holding_is_rejected_and_history_is_unchanged():
    create_user()
    headers = auth_headers()
    assert post_trade(headers, "HDFC", "BUY", 5, 1500).status_code == 201
    response = post_trade(headers, "HDFC", "SELL", 10, 1600)
    assert response.status_code == 400
    holding = get_holding("HDFC")
    assert holding is not None
    assert float(holding.quantity) == 5
    assert client.get("/api/v1/transactions", headers=headers).json()["summary"]["total_transactions"] == 1


def test_invalid_transaction_type_is_rejected():
    create_user()
    response = post_trade(auth_headers(), "TCS", "INVALID", 10, 3000)
    assert response.status_code == 422


def test_transaction_history():
    create_user()
    headers = auth_headers()
    post_trade(headers, "TCS", "BUY", 10, 3000)
    post_trade(headers, "INFY", "BUY", 5, 1500)
    response = client.get("/api/v1/transactions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_transactions"] == 2
    assert len(data["transactions"]) == 2


def test_transaction_summary_realized_pnl_uses_fifo():
    create_user()
    headers = auth_headers()
    for payload in [
        ("TCS", "BUY", 10, 100),
        ("TCS", "BUY", 10, 200),
        ("TCS", "SELL", 5, 180),
    ]:
        assert post_trade(headers, *payload).status_code == 201
    data = client.get("/api/v1/transactions", headers=headers).json()
    assert data["summary"]["realized_profit_loss"] == 400


def test_edit_transaction_rebuilds_fifo_holdings():
    create_user()
    headers = auth_headers()
    first = post_trade(headers, "TCS", "BUY", 10, 100).json()
    assert post_trade(headers, "TCS", "BUY", 10, 200).status_code == 201
    assert post_trade(headers, "TCS", "SELL", 5, 180).status_code == 201
    response = client.put(
        f"/api/v1/transactions/{first['id']}",
        json={"symbol": "TCS", "transaction_type": "BUY", "quantity": 20, "price": 100, "transaction_date": first["transaction_date"]},
        headers=headers,
    )
    assert response.status_code == 200
    holding = get_holding("TCS")
    assert holding is not None
    assert float(holding.quantity) == 25
    assert round(float(holding.average_buy_price), 2) == 140


def test_edit_transaction_that_creates_invalid_sell_rolls_back():
    create_user()
    headers = auth_headers()
    buy = post_trade(headers, "INFY", "BUY", 5, 100).json()
    sell = post_trade(headers, "INFY", "SELL", 2, 120).json()
    response = client.put(
        f"/api/v1/transactions/{sell['id']}",
        json={"symbol": "INFY", "transaction_type": "SELL", "quantity": 10, "price": 120, "transaction_date": sell["transaction_date"]},
        headers=headers,
    )
    assert response.status_code == 400
    holding = get_holding("INFY")
    assert holding is not None
    assert float(holding.quantity) == 3
    assert client.get("/api/v1/transactions", headers=headers).json()["summary"]["total_transactions"] == 2


def test_delete_transaction_rebuilds_holdings():
    create_user()
    headers = auth_headers()
    buy = post_trade(headers, "RELIANCE", "BUY", 10, 100).json()
    assert post_trade(headers, "RELIANCE", "BUY", 5, 200).status_code == 201
    response = client.delete(f"/api/v1/transactions/{buy['id']}", headers=headers)
    assert response.status_code == 204
    holding = get_holding("RELIANCE")
    assert holding is not None
    assert float(holding.quantity) == 5
    assert float(holding.average_buy_price) == 200


def test_edit_and_delete_require_ownership():
    create_user()
    headers = auth_headers()
    trade = post_trade(headers, "TCS", "BUY", 10, 3000).json()
    db = SessionLocal()
    try:
        other = User(full_name="Other User", email="transaction-other@example.com", password_hash=hash_password(PASSWORD))
        db.add(other)
        db.commit()
    finally:
        db.close()
    other_login = client.post("/api/v1/auth/login", json={"email": "transaction-other@example.com", "password": PASSWORD})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    assert client.put(f"/api/v1/transactions/{trade['id']}", json={"quantity": 20}, headers=other_headers).status_code == 404
    assert client.delete(f"/api/v1/transactions/{trade['id']}", headers=other_headers).status_code == 404


def test_transaction_belongs_to_user():
    create_user()
    headers = auth_headers()
    response = post_trade(headers, "TCS", "BUY", 10, 3000)
    assert response.status_code == 201
    transaction_id = response.json()["id"]
    response = client.get(f"/api/v1/transactions/{transaction_id}", headers=headers)
    assert response.status_code == 200
