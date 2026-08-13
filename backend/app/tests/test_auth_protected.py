import jwt

from fastapi.testclient import TestClient

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User
from main import app


client = TestClient(app)


TEST_EMAIL = "protected-test@example.com"
TEST_PASSWORD = "TestPassword123!"


def clean_user():
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == TEST_EMAIL
        ).first()

        if user:
            db.delete(user)
            db.commit()

    finally:
        db.close()


def create_test_user():
    clean_user()

    db = SessionLocal()

    try:
        user = User(
            full_name="Protected Test User",
            email=TEST_EMAIL,
            password_hash=hash_password(
                TEST_PASSWORD
            ),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id

    finally:
        db.close()


def get_login_token():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def test_valid_jwt_contains_user_subject():
    user_id = create_test_user()

    try:
        token = get_login_token()

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        assert payload["sub"] == str(user_id)
        assert "iat" in payload
        assert "exp" in payload

    finally:
        clean_user()


def test_current_user_requires_authentication():
    response = client.get(
        "/api/v1/users/me"
    )

    assert response.status_code == 401


def test_current_user_returns_authenticated_user():
    create_test_user()

    try:
        token = get_login_token()

        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["email"] == TEST_EMAIL
        assert data["full_name"] == "Protected Test User"

        assert "password" not in data
        assert "password_hash" not in data

    finally:
        clean_user()


def test_current_user_rejects_invalid_token():
    create_test_user()

    try:
        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": "Bearer invalid-token",
            },
        )

        assert response.status_code == 401

    finally:
        clean_user()


def test_current_user_rejects_expired_token():
    create_test_user()

    try:
        token = jwt.encode(
            {
                "sub": "1",
                "iat": 1,
                "exp": 1,
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )

        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 401

    finally:
        clean_user()


def test_existing_users_endpoint_still_works():
    response = client.get(
        "/api/v1/users/"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
