from datetime import datetime

from pydantic import BaseModel


class QuoteResponse(BaseModel):
    symbol: str
    name: str | None = None
    currency: str | None = None
    exchange: str | None = None
    price: float
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    market_time: datetime | None = None


class HistoricalPrice(BaseModel):
    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


class HistoryResponse(BaseModel):
    symbol: str
    currency: str | None = None
    interval: str
    range: str
    data: list[HistoricalPrice]


class SearchInstrumentResponse(BaseModel):
    symbol: str
    name: str
    exchange: str
