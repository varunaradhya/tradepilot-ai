from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaperMlDeployment(Base):
    __tablename__ = "paper_ml_deployments"
    __table_args__ = (
        UniqueConstraint("user_id", "strategy_version", name="uq_paper_ml_deployment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="SHADOW")
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.60)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
