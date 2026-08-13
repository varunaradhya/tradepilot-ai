from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.holding import Holding
from app.models.user import User
from app.schemas.advanced_analytics import AdvancedAnalyticsResponse
from app.services.advanced_analytics_service import calculate_advanced_analytics
from app.services.market_service import MarketDataProviderError, get_history, get_quote

router = APIRouter(prefix="/analytics", tags=["Advanced Analytics"])


@router.get("/advanced", response_model=AdvancedAnalyticsResponse)
def advanced_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == current_user.id)
        .all()
    )

    quotes = {}
    histories = {}
    for holding in holdings:
        symbol = holding.symbol.upper()
        try:
            quotes[symbol] = float(get_quote(symbol).price)
            history = get_history(symbol, range_="3mo", interval="1d")
            histories[symbol] = [float(row["close"]) for row in history.data if row.get("close") is not None]
        except MarketDataProviderError:
            continue
    return calculate_advanced_analytics(holdings, quotes, histories)
