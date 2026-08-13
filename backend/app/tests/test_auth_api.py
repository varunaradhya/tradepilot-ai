from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User
from main import app


client = TestClient(app)


def clean_user(email: str):
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == email
        ).first()

        if user:
            db.delete(user)
            db.commit()

    finally:
        db.close()


def test_register_user():
    email = "register-test@example.com"

    clean_user(email)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Register Test",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["full_name"] == "Register Test"
    assert "password" not in data
    assert "password_hash" not in data

    clean_user(email)


def test_duplicate_registration_returns_conflict():
    email = "duplicate-test@example.com"

    clean_user(email)

    first = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Duplicate Test",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Duplicate Test",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert second.status_code == 409

    clean_user(email)


def test_register_rejects_short_password():
    email = "short-password@example.com"

    clean_user(email)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Short Password",
            "email": email,
            "password": "short",
        },
    )

    assert response.status_code == 422

    clean_user(email)


def test_login_returns_jwt():
    email = "login-test@example.com"

    clean_user(email)

    db = SessionLocal()

    try:
        user = User(
            full_name="Login Test",
            email=email,
            password_hash=hash_password(
                "TestPassword123!"
            ),
        )

        db.add(user)
        db.commit()

    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert isinstance(
        data["access_token"],
        str,
    )
    assert len(data["access_token"]) > 20

    clean_user(email)


def test_login_rejects_wrong_password():
    email = "wrong-password@example.com"

    clean_user(email)

    db = SessionLocal()

    try:
        user = User(
            full_name="Wrong Password Test",
            email=email,
            password_hash=hash_password(
                "TestPassword123!"
            ),
        )

        db.add(user)
        db.commit()

    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    clean_user(email)


def test_login_rejects_unknown_user():
    email = "unknown-user@example.com"

    clean_user(email)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401
