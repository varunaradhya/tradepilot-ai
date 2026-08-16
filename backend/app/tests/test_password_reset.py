import jwt
import pytest

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.services.auth_service import create_password_reset_token, decode_password_reset_token


def test_password_reset_token_round_trip():
    token = create_password_reset_token(42)
    assert decode_password_reset_token(token) == 42


def test_password_reset_token_rejects_access_token():
    access_like = jwt.encode(
        {"sub": "42", "purpose": "access"},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(ValueError):
        decode_password_reset_token(access_like)
