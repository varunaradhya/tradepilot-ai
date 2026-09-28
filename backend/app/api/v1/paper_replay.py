from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.intraday_strategy import IntradayConfig
from app.services.paper_evaluation_service import compare_strategy_results, evaluate_replay
from app.services.paper_replay_service import run_paper_replay

router = APIRouter(prefix="/paper-replay", tags=["Paper Replay"])


class ReplayBar(BaseModel):
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    opening_high: float | None = Field(default=None, gt=0)
    opening_low: float | None = Field(default=None, gt=0)


class ReplayRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    symbol: str = Field(min_length=1, max_length=30)
    bars: list[ReplayBar] = Field(min_length=1, max_length=10000)


class CompareRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    symbol: str = Field(min_length=1, max_length=30)
    bars: list[ReplayBar] = Field(min_length=1, max_length=10000)


@router.post("/run")
def replay(payload: ReplayRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    for bar in payload.bars:
        if bar.low > bar.high or not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid OHLC range")
    result = run_paper_replay([bar.model_dump() for bar in payload.bars], session=payload.session, symbol=payload.symbol)
    return {**result, "evaluation": evaluate_replay(result)}


@router.post("/compare")
def compare(payload: CompareRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    bars = [bar.model_dump() for bar in payload.bars]
    if any(bar["low"] > bar["high"] or not (bar["low"] <= bar["open"] <= bar["high"] and bar["low"] <= bar["close"] <= bar["high"]) for bar in bars):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid OHLC range")
    a = run_paper_replay(bars, session=payload.session, symbol=payload.symbol, strategy=IntradayConfig())
    b = run_paper_replay(bars, session=payload.session, symbol=payload.symbol, strategy=IntradayConfig(min_volume_ratio=1.8, min_quality_score=40))
    return compare_strategy_results({"V1_DEFAULT": a, "V1_STRICT": b})
