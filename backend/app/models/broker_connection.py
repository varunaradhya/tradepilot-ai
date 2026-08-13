from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class BrokerConnection(Base):

    __tablename__ = "broker_connections"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "broker_name",
            name="uq_broker_connection_user_broker",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    broker_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    client_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    encrypted_access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="CONNECTED",
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_sync_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    last_sync_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
