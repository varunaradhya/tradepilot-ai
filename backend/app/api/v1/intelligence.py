from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.analyst_service import analyze_portfolio, analyze_stock, analyze_watchlist
from app.ai.context import normalize_symbol
from app.ai.trading_intelligence import build_trading_view, scan_opportunities
from app.services.ai_history_service import list_history
from app.services.daily_briefing_service import build_daily_briefing
from app.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.intelligence import HistoryResponse, IntelligenceResponse, OpportunityResponse, TradingViewResponse

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence"])


@router.get("/portfolio", response_model=IntelligenceResponse)
def portfolio_intelligence(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analyze_portfolio(db, current_user.id)


@router.get("/stock/{symbol}", response_model=IntelligenceResponse)
def stock_intelligence(symbol: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return analyze_stock(db, current_user.id, normalize_symbol(symbol))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/watchlist", response_model=IntelligenceResponse)
def watchlist_intelligence(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analyze_watchlist(db, current_user.id)


@router.get("/opportunities", response_model=OpportunityResponse)
def opportunities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return scan_opportunities(db, current_user.id)


@router.get("/trading-view", response_model=TradingViewResponse)
def trading_view(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_trading_view(db, current_user.id)


@router.get("/history", response_model=list[HistoryResponse])
def history(analysis_type: str | None = None, symbol: str | None = None, limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_history(db, current_user.id, analysis_type, normalize_symbol(symbol) if symbol else None, max(1, min(limit, 100)))


@router.get("/daily-briefing")
def daily_briefing(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_daily_briefing(db, current_user.id)
