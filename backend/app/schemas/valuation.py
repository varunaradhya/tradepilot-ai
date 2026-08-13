from pydantic import BaseModel


class HoldingValuation(BaseModel):
    id: int
    symbol: str
    quantity: float
    average_buy_price: float
    invested_amount: float
    current_price: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float


class PortfolioSummary(BaseModel):
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float
    holdings_count: int


class PortfolioValuationResponse(BaseModel):
    summary: PortfolioSummary
    holdings: list[HoldingValuation]
