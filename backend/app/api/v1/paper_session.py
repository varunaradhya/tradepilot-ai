from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator

router = APIRouter(prefix="/paper-session", tags=["Paper Session"])

_sessions: dict[int, PaperTradingOrchestrator] = {}


class SignalRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=20)
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    symbol: str = Field(default="", max_length=30)


class BarRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)


def _session(user_id: int) -> PaperTradingOrchestrator:
    return _sessions.setdefault(user_id, PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY")))


@router.get("/summary")
def summary(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return _session(current_user.id).summary()


@router.post("/signal")
def signal(payload: SignalRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    result = _session(current_user.id).on_signal(payload.session, payload.model_dump())
    return {"mode": "SIMULATION_ONLY", **result}


@router.post("/bar")
def bar(payload: BarRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    if payload.low > payload.high:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="low cannot exceed high")
    result = _session(current_user.id).on_bar(payload.session, payload.high, payload.low, payload.close)
    return {"mode": "SIMULATION_ONLY", **result}


@router.post("/reset")
def reset(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    _sessions[current_user.id] = PaperTradingOrchestrator(PaperOrchestratorConfig(trade_direction="LONG_ONLY"))
    return {"mode": "SIMULATION_ONLY", "reset": True}
