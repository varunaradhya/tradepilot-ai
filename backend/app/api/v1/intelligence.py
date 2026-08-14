from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.analyst_service import analyze_portfolio, analyze_stock, analyze_watchlist
from app.ai.context import normalize_symbol
from app.ai.trading_intelligence import build_trading_view, scan_opportunities
from app.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.intelligence import IntelligenceResponse, OpportunityResponse, TradingViewResponse

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence"])


@router.get("/portfolio", response_model=IntelligenceResponse)
def portfolio_intelligence(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return analyze_portfolio(db, current_user.id)


@router.get("/stock/{symbol}", response_model=IntelligenceResponse)
def stock_intelligence(symbol: str, current_user: User = Depends(get_current_user)):
    del current_user
    try:
        return analyze_stock(normalize_symbol(symbol))
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
