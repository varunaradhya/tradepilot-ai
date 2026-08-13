from __future__ import annotations

from pydantic import BaseModel, Field


class StockPerformance(BaseModel):
    symbol: str
    invested: float
    current_value: float
    pnl: float
    return_percent: float


class AdvancedAnalyticsResponse(BaseModel):
    total_invested: float
    current_value: float
    total_pnl: float
    return_percent: float
    concentration_percent: float
    top_holding: str | None = None
    holdings: list[StockPerformance] = Field(default_factory=list)
    diversification_score: float
    risk_summary: str
    volatility_percent: float | None = None
    maximum_drawdown_percent: float | None = None
    unavailable_symbols: list[str] = Field(default_factory=list)
