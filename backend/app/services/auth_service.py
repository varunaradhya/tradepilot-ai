from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_REFRESH_EXPIRE_DAYS, JWT_SECRET_KEY
from app.core.security import hash_password, verify_password
from app.models.user import User


RESET_TOKEN_MINUTES = 15
REFRESH_TOKEN_PURPOSE = "refresh"


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    return db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_user(db: Session, full_name: str, email: str, password: str) -> User:
    user = User(full_name=full_name.strip(), email=email.strip().lower(), password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(user)
    return user


def _create_token(user_id: int, expires: timedelta, purpose: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires}
    if purpose:
        payload["purpose"] = purpose
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: int, expires_minutes: int = JWT_EXPIRE_MINUTES) -> str:
    return _create_token(user_id, timedelta(minutes=expires_minutes))


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, timedelta(days=JWT_REFRESH_EXPIRE_DAYS), REFRESH_TOKEN_PURPOSE)


def decode_access_token(token: str) -> dict:
    """Decode and validate an access JWT."""
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") is not None:
        raise ValueError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != REFRESH_TOKEN_PURPOSE:
        raise ValueError("Invalid refresh token")
    return int(payload["sub"])


def create_password_reset_token(user_id: int) -> str:
    return _create_token(user_id, timedelta(minutes=RESET_TOKEN_MINUTES), "password_reset")


def decode_password_reset_token(token: str) -> int:
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "password_reset":
        raise ValueError("Invalid password reset token")
    return int(payload["sub"])
