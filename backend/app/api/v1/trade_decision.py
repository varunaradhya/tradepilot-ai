from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.market_service import MarketSearchProviderError, search_instruments
from app.services.portfolio_risk import PortfolioPosition
from app.services.risk_decision_engine import build_risk_aware_paper_trade_decision
from app.services.trade_decision_service import build_paper_trade_decision

router = APIRouter(prefix="/trade-decision", tags=["Trade Decision"])


def _validated_indian_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized.endswith(".NS") or normalized.endswith(".BO"):
        normalized = normalized.rsplit(".", 1)[0]
    try:
        matches = search_instruments(normalized)
    except MarketSearchProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Indian stock validation is temporarily unavailable. Please try again shortly.",
        ) from exc
    exact = [item for item in matches if item.symbol.upper() == normalized]
    if not exact:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{normalized or 'SYMBOL'} is not available in the Indian NSE/BSE equity universe.",
        )
    return exact[0].symbol.upper()


class PortfolioPositionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    market_value: float = Field(gt=0)
    stop_loss_value: float = Field(ge=0)
    sector: str | None = Field(default=None, max_length=60)


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
    existing_positions: list[PortfolioPositionRequest] = Field(default_factory=list)
    sector: str | None = Field(default=None, max_length=60)


@router.post("/paper", response_model=dict[str, Any])
def paper_trade_decision(payload: TradeDecisionRequest, current_user: User = Depends(get_current_user)):
    values = payload.model_dump(exclude={"existing_positions", "sector"})
    values["symbol"] = _validated_indian_symbol(payload.symbol)
    result = build_paper_trade_decision(**values)
    return {"mode": "SIMULATION_ONLY", "user_id": current_user.id, **result.as_dict()}


@router.post("/paper/risk-aware", response_model=dict[str, Any])
def risk_aware_paper_trade_decision(payload: TradeDecisionRequest, current_user: User = Depends(get_current_user)):
    positions = [PortfolioPosition(**position.model_dump()) for position in payload.existing_positions]
    values = payload.model_dump(exclude={"existing_positions"})
    values["symbol"] = _validated_indian_symbol(payload.symbol)
    result = build_risk_aware_paper_trade_decision(
        **values,
        existing_positions=positions,
    )
    return {"mode": "SIMULATION_ONLY", "user_id": current_user.id, **result.as_dict()}
