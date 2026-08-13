from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email address, or None when the user does not exist."""
    statement = select(User).where(User.email == email)
    return db.execute(statement).scalar_one_or_none()


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user using email and password.

    Returns the User when credentials are valid.
    Returns None when the user does not exist or the password is incorrect.
    """
    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
