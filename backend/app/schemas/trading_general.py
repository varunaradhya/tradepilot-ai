from __future__ import annotations

from pydantic import BaseModel, Field


class TradingTradeStat(BaseModel):
    symbol: str
    realized_pnl: float
    return_percent: float
    quantity: float
    sell_price: float
    cost_basis: float


class TradingGeneralResponse(BaseModel):
    realized_pnl: float
    total_closed_quantity: float
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate_percent: float
    average_win: float
    average_loss: float
    profit_factor: float | None
    expectancy_per_trade: float
    best_trade: TradingTradeStat | None
    worst_trade: TradingTradeStat | None
    largest_win_percent: float | None
    largest_loss_percent: float | None
    strategy_score: int = Field(ge=0, le=100)
    strategy_label: str
    strategy_insights: list[str]
    loss_patterns: list[str]
    profit_patterns: list[str]
    suggested_rules: list[str]
    sample_size: int
    disclaimer: str
