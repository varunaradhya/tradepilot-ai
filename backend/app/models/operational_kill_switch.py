from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class OperationalKillSwitch(Base):
    """Durable singleton kill switch for paper operations."""

    __tablename__ = "operational_kill_switch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="FAIL_CLOSED_DEFAULT")
    activated_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
