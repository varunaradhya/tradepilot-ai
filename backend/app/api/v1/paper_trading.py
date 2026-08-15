from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.paper_trading_service import close_paper_trade, list_paper_trades, open_paper_trade, paper_summary, update_paper_trade
from app.models.paper_trade import PaperTrade

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])


class PaperTradeCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    quantity: int = Field(gt=0, le=1_000_000)
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    target_price: float = Field(gt=0)
    strategy_version: str = Field(default="V1", pattern="^(V1|V2)$")


class PaperMarkRequest(BaseModel):
    price: float = Field(gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)


class PaperCloseRequest(BaseModel):
    exit_price: float = Field(gt=0)
    reason: str = Field(default="MANUAL", min_length=1, max_length=40)


def _owned(db: Session, user_id: int, trade_id: int) -> PaperTrade:
    trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id, PaperTrade.user_id == user_id).first()
    if trade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper trade not found")
    return trade


@router.post("/trades", status_code=status.HTTP_201_CREATED)
def create_paper_trade(payload: PaperTradeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return open_paper_trade(db, current_user.id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/trades")
def get_paper_trades(status_filter: str | None = Query(default=None, alias="status", pattern="^(OPEN|CLOSED)$"), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trades = list_paper_trades(db, current_user.id, status_filter)
    return {"trades": trades, "summary": paper_summary(trades), "mode": "SIMULATION_ONLY"}


@router.post("/trades/{trade_id}/mark")
def mark_paper_trade(trade_id: int, payload: PaperMarkRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trade = _owned(db, current_user.id, trade_id)
    try:
        return update_paper_trade(db, trade, payload.price, market_high=payload.high, market_low=payload.low)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.post("/trades/{trade_id}/close")
def close_trade(trade_id: int, payload: PaperCloseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trade = _owned(db, current_user.id, trade_id)
    try:
        return close_paper_trade(db, trade, payload.exit_price, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
