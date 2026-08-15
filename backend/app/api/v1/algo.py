from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.algo import AlgoBacktestRequest, AlgoBacktestResponse
from app.services.algo_strategy import StrategyConfig
from app.services.backtest_service import BacktestConfig, run_daily_backtest
from app.services.market_service import MarketDataNotFoundError, MarketDataProviderError, get_history

router = APIRouter(prefix="/algo", tags=["Algo Research"])


@router.post("/backtest", response_model=AlgoBacktestResponse)
def backtest(request: AlgoBacktestRequest, current_user: User = Depends(get_current_user)):
    del current_user
    try:
        history = get_history(request.symbol.upper(), range_=request.range, interval="1d")
    except MarketDataNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    rows = [
        {"close": float(x["close"]), "high": float(x["high"]), "low": float(x["low"]), "volume": x.get("volume")}
        for x in history.data
        if x.get("close") is not None and x.get("high") is not None and x.get("low") is not None
    ]
    if len(rows) < 80:
        raise HTTPException(status_code=422, detail="Not enough historical data for a reliable backtest")

    result = run_daily_backtest(rows, BacktestConfig(initial_capital=request.initial_capital, strategy=StrategyConfig()))
    return {"symbol": request.symbol.upper(), "range": request.range, "interval": "1d", "strategy": "Regime Momentum Breakout v1", **{k: result[k] for k in AlgoBacktestResponse.model_fields if k in result}}
