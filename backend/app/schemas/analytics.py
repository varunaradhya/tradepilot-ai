from pydantic import BaseModel


class StockPerformance(BaseModel):
    symbol: str
    quantity: float
    invested_amount: float
    current_price: float
    current_value: float
    unrealized_profit_loss: float
    unrealized_profit_loss_percent: float


class PortfolioAnalytics(BaseModel):
    total_invested: float
    current_value: float
    unrealized_profit_loss: float
    unrealized_profit_loss_percent: float
    realized_profit_loss: float
    total_profit_loss: float
    total_return_percent: float
    best_performer: str | None
    worst_performer: str | None
    holdings_count: int
    transactions_count: int
    stocks: list[StockPerformance]
