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
    limitations: list[str] = Field(default_factory=list)
    generated_at: datetime


class IntelligenceResponse(BaseModel):
    analysis: AIAnalysis
    context_summary: dict[str, Any]


class Opportunity(BaseModel):
    symbol: str
    score: int = Field(ge=0, le=100)
    signal: Literal["BUY", "HOLD", "SELL"]
    reasons: list[str]
    risks: list[str]
    data_quality: str
    price_context: dict[str, float | None]
    technical_summary: dict[str, Any]
    momentum_percent: float | None
    risk_score: int = Field(ge=0, le=100)


class OpportunityResponse(BaseModel):
    opportunities: list[Opportunity]
    unavailable_symbols: list[str]
    data_quality: str


class TradingViewResponse(BaseModel):
    market_candidates: list[Opportunity]
    buy_candidates: list[Opportunity]
    hold_candidates: list[Opportunity]
    sell_candidates: list[Opportunity]
    strongest_momentum: Opportunity | None
    highest_risk: Opportunity | None
    requires_attention: list[Opportunity]
    unavailable_symbols: list[str]
    data_quality: str
    disclaimer: str


class HistoryResponse(BaseModel):
    id: int
    analysis_type: str
    symbol: str | None
    provider: str
    signal: str
    confidence: int
    summary: str
    generated_at: datetime
