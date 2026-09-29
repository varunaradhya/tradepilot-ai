from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.paper_market_service import PaperMarketCoordinator

router = APIRouter(prefix="/paper-session", tags=["Paper Session"])

_coordinators: dict[int, PaperMarketCoordinator] = {}


class MarketBarRequest(BaseModel):
    session: str = Field(min_length=1, max_length=40)
    symbol: str = Field(min_length=1, max_length=30)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    opening_high: float | None = Field(default=None, gt=0)
    opening_low: float | None = Field(default=None, gt=0)


def _coordinator(user_id: int) -> PaperMarketCoordinator:
    return _coordinators.setdefault(user_id, PaperMarketCoordinator())


@router.get("/summary")
def summary(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"mode": "SIMULATION_ONLY", **_coordinator(current_user.id).orchestrator.summary()}


@router.post("/bar")
def market_bar(payload: MarketBarRequest, current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Legacy mutation path is disabled; use the durable authorized pipeline."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy paper-session mutation is disabled; use /api/v1/paper-trading/session/market-bar.",
    )


@router.post("/reset")
def reset(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Legacy reset path is disabled to prevent a second paper-state model."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy paper-session reset is disabled; use the durable paper-trading session controls.",
    )
