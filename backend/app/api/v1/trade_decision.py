from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.trade_decision_service import build_paper_trade_decision

router = APIRouter(prefix="/trade-decision", tags=["Trade Decision"])


class TradeDecisionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    session: str = Field(min_length=1, max_length=40)
    closes: list[float] = Field(min_length=20)
    highs: list[float] = Field(min_length=20)
    lows: list[float] = Field(min_length=20)
    volumes: list[float] = Field(min_length=20)
    equity: float = Field(gt=0)
    broker: str = Field(default="DHAN", min_length=1, max_length=40)
    opening_high: float | None = Field(default=None, gt=0)
    in_market_session: bool = True
    market_data_healthy: bool = True
    strategy_ready: bool = True
    risk_approved: bool = True
    daily_risk_used: float = Field(default=0, ge=0)
    min_confidence: float = Field(default=65, ge=0, le=100)


@router.post("/paper", response_model=dict[str, Any])
def paper_trade_decision(payload: TradeDecisionRequest, current_user: User = Depends(get_current_user)):
    # User authentication is required, but the decision engine itself is
    # deliberately stateless and does not place broker orders.
    result = build_paper_trade_decision(**payload.model_dump())
    return {"mode": "SIMULATION_ONLY", "user_id": current_user.id, **result.as_dict()}
