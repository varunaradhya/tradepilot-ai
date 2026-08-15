from pydantic import BaseModel, Field


class AlgoBacktestResponse(BaseModel):
    symbol: str
    range: str
    interval: str
    strategy: str
    initial_capital: float
    ending_capital: float
    return_percent: float
    trades: int
    wins: int
    losses: int
    win_rate_percent: float
    profit_factor: float | None
    max_drawdown_percent: float
    gross_profit: float
    gross_loss: float


class AlgoBacktestRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    range: str = Field(default="5y", pattern="^(1y|2y|5y)$")
    initial_capital: float = Field(default=100000, gt=0)
