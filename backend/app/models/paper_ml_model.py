from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaperMlModel(Base):
    __tablename__ = "paper_ml_models"
    __table_args__ = (
        UniqueConstraint("user_id", "strategy_version", "version", name="uq_paper_ml_model"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(40), nullable=False, default="LOGISTIC_REGRESSION")
    feature_names_json: Mapped[str] = mapped_column(Text, nullable=False)
    model_json: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    training_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    strategy_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    feature_schema_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
