from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime


class SignalResponse(BaseModel):
    symbol: str
    signal: str
    confidence: float
    risk_level: str
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    risk_reward: float | None = None
    reasons: list[str] = Field(default_factory=list)
    indicators: dict = Field(default_factory=dict)
    timestamp: datetime
    data_status: str
