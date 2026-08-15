from pydantic import BaseModel, Field


class WatchlistCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)


class WatchlistResponse(BaseModel):
    id: int
    symbol: str

    model_config = {"from_attributes": True}


class WatchlistQuote(BaseModel):
    id: int
    symbol: str
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    market_data_available: bool = False
