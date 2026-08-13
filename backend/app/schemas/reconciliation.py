from __future__ import annotations

from pydantic import BaseModel, Field


class ReconciliationItem(BaseModel):
    symbol: str
    tradepilot_quantity: float
    broker_quantity: float
    quantity_difference: float
    tradepilot_average_price: float
    broker_average_price: float
    average_price_difference: float
    status: str


class ReconciliationSummary(BaseModel):
    matched: int
    quantity_mismatches: int
    average_price_mismatches: int
    missing_from_tradepilot: int
    missing_from_broker: int


class ReconciliationResponse(BaseModel):
    broker: str
    summary: ReconciliationSummary
    items: list[ReconciliationItem] = Field(default_factory=list)