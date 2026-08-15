from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.market_service import MarketDataProviderError, get_history
from app.services.manipulation_detector import detect_market_pressure

router = APIRouter(prefix="/market-risk", tags=["Market Risk"])


@router.get("/pressure")
def market_pressure(
    symbol: str = Query(min_length=1, max_length=30),
    current_user: User = Depends(get_current_user),
):
    del current_user
    try:
        history = get_history(symbol.upper(), range_="6mo", interval="1d")
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=503, detail=f"Market data provider error: {exc}") from exc

    rows = [
        row for row in history.data
        if row.get("close") is not None and row.get("high") is not None
        and row.get("low") is not None and row.get("volume") is not None
    ]
    return {
        "symbol": symbol.upper(),
        "analysis": detect_market_pressure(
            [row["close"] for row in rows],
            [row["high"] for row in rows],
            [row["low"] for row in rows],
            [row["volume"] for row in rows],
        ),
    }
