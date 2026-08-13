import os

from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient

from main import app

from app.core.broker_security import (
    decrypt_secret,
    encrypt_secret,
)
from app.db.database import SessionLocal
from app.models.broker_connection import (
    BrokerConnection,
)
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "broker-test@example.com"
PASSWORD = "TestPassword123!"

TEST_KEY = (
    "wYvX8ZVv4vNQh7zVv5W0b"
    "d6o9K0yY4xN5Vv3GQm8sJ0="
)

os.environ[
    "TRADEPILOT_BROKER_ENCRYPTION_KEY"
] = TEST_KEY


def create_user():

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(
                User.email == EMAIL
            )
            .first()
        )

        if user is None:

            user = User(
                full_name="Broker Test User",
                email=EMAIL,
                password_hash=hash_password(
                    PASSWORD
                ),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        db.query(
            BrokerConnection
        ).filter(
            BrokerConnection.user_id
            == user.id
        ).delete(
            synchronize_session=False
        )

        db.commit()

        return user.id

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

    return {
        "Authorization":
            f"Bearer {response.json()['access_token']}"
    }


def test_secret_encryption_roundtrip():

    secret = "dhan-access-token-test"

    encrypted = encrypt_secret(
        secret
    )

    assert encrypted != secret

    assert decrypt_secret(
        encrypted
    ) == secret


def test_broker_list_requires_authentication():

    response = client.get(
        "/api/v1/brokers"
    )

    assert response.status_code == 401


@patch(
    "app.api.v1.brokers.DhanClient.profile"
)
def test_connect_dhan(
    mock_profile,
):

    create_user()

    mock_profile.return_value = {
        "dhanClientId": "TEST123",
        "tokenValidity": "valid",
    }

    response = client.post(
        "/api/v1/brokers/connect",
        json={
            "broker_name": "DHAN",
            "client_id": "TEST123",
            "access_token":
                "test-access-token-123456",
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["broker_name"] == "DHAN"
    assert data["client_id"] == "TEST123"
    assert data["status"] == "CONNECTED"


@patch(
    "app.services.portfolio_sync_service.DhanClient.profile"
)
@patch(
    "app.services.portfolio_sync_service.DhanClient.holdings"
)
@patch(
    "app.services.portfolio_sync_service.DhanClient.trades"
)
def test_dhan_sync(
    mock_trades,
    mock_holdings,
    mock_profile,
):

    create_user()

    mock_profile.return_value = {
        "dhanClientId": "TEST123"
    }

    mock_holdings.return_value = [
        {
            "tradingSymbol": "TCS",
            "totalQty": 10,
            "avgCostPrice": 3000,
        }
    ]

    mock_trades.return_value = [
        {
            "tradingSymbol": "TCS",
            "transactionType": "BUY",
            "tradedQuantity": 10,
            "tradedPrice": 3000,
            "exchangeTime":
                "2026-08-13 10:00:00",
        }
    ]

    connect = client.post(
        "/api/v1/brokers/connect",
        json={
            "broker_name": "DHAN",
            "client_id": "TEST123",
            "access_token":
                "test-access-token-123456",
        },
        headers=auth_headers(),
    )

    assert connect.status_code == 200

    response = client.post(
        "/api/v1/brokers/dhan/sync",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["holdings_updated"] == 1
    assert data["transactions_imported"] == 1


@patch(
    "app.services.portfolio_sync_service.DhanClient.profile"
)
@patch(
    "app.services.portfolio_sync_service.DhanClient.holdings"
)
@patch(
    "app.services.portfolio_sync_service.DhanClient.trades"
)
def test_dhan_sync_is_duplicate_safe(
    mock_trades,
    mock_holdings,
    mock_profile,
):

    create_user()

    mock_profile.return_value = {
        "dhanClientId": "TEST123"
    }

    mock_holdings.return_value = [
        {
            "tradingSymbol": "INFY",
            "totalQty": 5,
            "avgCostPrice": 1500,
        }
    ]

    mock_trades.return_value = [
        {
            "tradingSymbol": "INFY",
            "transactionType": "BUY",
            "tradedQuantity": 5,
            "tradedPrice": 1500,
            "exchangeTime":
                "2026-08-13 11:00:00",
        }
    ]

    headers = auth_headers()

    client.post(
        "/api/v1/brokers/connect",
        json={
            "broker_name": "DHAN",
            "client_id": "TEST123",
            "access_token":
                "test-access-token-123456",
        },
        headers=headers,
    )

    first = client.post(
        "/api/v1/brokers/dhan/sync",
        headers=headers,
    )

    second = client.post(
        "/api/v1/brokers/dhan/sync",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert (
        first.json()["transactions_imported"]
        == 1
    )

    assert (
        second.json()["transactions_imported"]
        == 0
    )


def test_dhan_sync_without_connection():

    create_user()

    response = client.post(
        "/api/v1/brokers/dhan/sync",
        headers=auth_headers(),
    )

    assert response.status_code == 404
