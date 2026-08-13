from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=30,
    )

    quantity: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=4,
    )

    average_buy_price: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=4,
    )


class HoldingUpdate(BaseModel):
    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    quantity: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=4,
    )

    average_buy_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=4,
    )


class HoldingResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    quantity: Decimal
    average_buy_price: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
