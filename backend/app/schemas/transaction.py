from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=20,
    )

    transaction_type: str

    quantity: float = Field(
        gt=0,
    )

    price: float = Field(
        gt=0,
    )

    transaction_date: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, value: str) -> str:

        value = value.strip().upper()

        if value not in {"BUY", "SELL"}:
            raise ValueError(
                "transaction_type must be BUY or SELL"
            )

        return value


class TransactionResponse(BaseModel):
    id: int
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    transaction_date: datetime

    model_config = {
        "from_attributes": True,
    }


class TransactionSummary(BaseModel):
    total_transactions: int
    total_buy_value: float
    total_sell_value: float
    realized_profit_loss: float


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    summary: TransactionSummary
