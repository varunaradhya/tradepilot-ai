from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AIAnalysis(BaseModel):
    summary: str
    market_view: str
    signal: Literal["BUY", "HOLD", "SELL", "NEUTRAL"]
    confidence: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)
    data_quality: str
    generated_at: datetime


class IntelligenceResponse(BaseModel):
    analysis: AIAnalysis
    context_summary: dict[str, Any]
