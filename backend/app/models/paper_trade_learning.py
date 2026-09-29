from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaperTradeLearningEvent(Base):
    __tablename__ = "paper_trade_learning_events"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_paper_learning_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    session: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    dataset_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    strategy_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="RULES_V1")
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    features_json: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[int] = mapped_column(Integer, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, nullable=False)
    r_multiple: Mapped[float] = mapped_column(Float, nullable=False)
    exit_reason: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
