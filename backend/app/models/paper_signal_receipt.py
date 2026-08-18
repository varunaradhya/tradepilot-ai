from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaperSignalReceipt(Base):
    __tablename__ = "paper_signal_receipts"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_paper_signal_receipt_user_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    session: Mapped[str] = mapped_column(String(40), nullable=False)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(10), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
