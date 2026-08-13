from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.database import Base
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    get_user_by_email,
)


def create_test_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    return SessionLocal()


def create_test_user(db):
    user = User(
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def test_get_user_by_email_returns_user():
    db = create_test_session()

    try:
        user = create_test_user(db)

        result = get_user_by_email(
            db,
            "test@example.com",
        )

        assert result is not None
        assert result.id == user.id
        assert result.email == "test@example.com"
    finally:
        db.close()


def test_get_user_by_email_returns_none_for_unknown_email():
    db = create_test_session()

    try:
        result = get_user_by_email(
            db,
            "missing@example.com",
        )

        assert result is None
    finally:
        db.close()


def test_authenticate_user_returns_user_for_valid_credentials():
    db = create_test_session()

    try:
        user = create_test_user(db)

        result = authenticate_user(
            db,
            "test@example.com",
            "TestPassword123!",
        )

        assert result is not None
        assert result.id == user.id
        assert result.email == "test@example.com"
    finally:
        db.close()


def test_authenticate_user_returns_none_for_wrong_password():
    db = create_test_session()

    try:
        create_test_user(db)

        result = authenticate_user(
            db,
            "test@example.com",
            "WrongPassword123!",
        )

        assert result is None
    finally:
        db.close()


def test_authenticate_user_returns_none_for_unknown_email():
    db = create_test_session()

    try:
        result = authenticate_user(
            db,
            "missing@example.com",
            "TestPassword123!",
        )

        assert result is None
    finally:
        db.close()
