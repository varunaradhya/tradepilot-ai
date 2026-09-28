from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class PaperValidationSymbol(Base):
    __tablename__ = "paper_validation_symbols"
    __table_args__ = (UniqueConstraint("user_id", "validation_run", "session_date", "symbol", name="uq_paper_validation_symbol"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    validation_run: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NO_DATA")
    bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    data_quality_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
