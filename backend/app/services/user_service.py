from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_users(db: Session) -> list[User]:
    return list(db.scalars(select(User)).all())
