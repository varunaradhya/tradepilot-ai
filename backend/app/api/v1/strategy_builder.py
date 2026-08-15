from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig
from app.services.intraday_strategy_comparison import compare_intraday_strategies
from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward
from app.services.research_store import research_store

router = APIRouter(prefix="/strategy-builder", tags=["Strategy Builder"])

class StrategyBuildRequest(BaseModel):
    initial_capital: float = Field(default=100000, gt=0, le=100000000)
    brokerage_rate: float = Field(default=0.0003, ge=0, le=0.01)
    slippage_rate: float = Field(default=0.0005, ge=0, le=0.01)
    max_daily_loss_percent: float = Field(default=1.0, gt=0, le=20)
    max_trades_per_session: int = Field(default=3, ge=1, le=50)
    opening_bars: int = Field(default=3, ge=1, le=12)
    fast_period: int = Field(default=9, ge=2, le=100)
    slow_period: int = Field(default=20, ge=3, le=200)
    volume_period: int = Field(default=20, ge=3, le=200)
    min_volume_ratio: float = Field(default=1.5, ge=0.1, le=10)
    max_gap_percent: float = Field(default=3.0, ge=0, le=20)
    risk_per_trade: float = Field(default=0.005, gt=0, le=0.1)
    max_position_percent: float = Field(default=0.20, gt=0, le=1)
    atr_period: int = Field(default=14, ge=2, le=100)
    atr_stop_multiple: float = Field(default=1.5, gt=0.1, le=10)
    reward_multiple: float = Field(default=2.0, gt=0.1, le=20)

def _rows(symbol: str, interval: str):
    dataset = f"nse/{symbol.strip().upper()}_intraday_{interval}m"
    bars = research_store.load(dataset)
    rows = []
    for bar in bars:
        row = bar.as_row()
        row["session"] = row["timestamp"].date().isoformat()
        rows.append(row)
    return dataset, rows

def _strategy(request: StrategyBuildRequest) -> IntradayConfig:
    if request.fast_period >= request.slow_period:
        raise HTTPException(status_code=422, detail="Fast EMA period must be smaller than slow EMA period")
    return IntradayConfig(opening_bars=request.opening_bars, fast_period=request.fast_period, slow_period=request.slow_period, volume_period=request.volume_period, min_volume_ratio=request.min_volume_ratio, max_gap_percent=request.max_gap_percent, risk_per_trade=request.risk_per_trade, max_position_percent=request.max_position_percent, atr_period=request.atr_period, atr_stop_multiple=request.atr_stop_multiple, reward_multiple=request.reward_multiple)

def _backtest_config(request: StrategyBuildRequest, strategy: IntradayConfig, version: str = "V1") -> IntradayBacktestConfig:
    return IntradayBacktestConfig(initial_capital=request.initial_capital, brokerage_rate=request.brokerage_rate, slippage_rate=request.slippage_rate, max_daily_loss_percent=request.max_daily_loss_percent, max_trades_per_session=request.max_trades_per_session, strategy=strategy, strategy_version=version)

@router.post("/backtest")
def build_and_backtest(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows:
        raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    strategy = _strategy(request)
    result = run_intraday_backtest(rows, _backtest_config(request, strategy))
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, "strategy": strategy.__dict__, "execution": {"brokerage_rate": request.brokerage_rate, "slippage_rate": request.slippage_rate, "max_daily_loss_percent": request.max_daily_loss_percent, "max_trades_per_session": request.max_trades_per_session}, **result}

@router.post("/compare")
def compare_versions(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows:
        raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    strategy = _strategy(request)
    comparison = compare_intraday_strategies(rows, _backtest_config(request, strategy))
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **comparison}

@router.post("/walk-forward")
def walk_forward_validation(
    symbol: str = Query(min_length=1, max_length=30),
    interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"),
    train_size: int = Query(default=60, ge=10, le=5000),
    validation_size: int = Query(default=20, ge=5, le=2000),
    step: int | None = Query(default=None, ge=1, le=2000),
    request: StrategyBuildRequest = ...,
    current_user: User = Depends(get_current_user),
):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows:
        raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    if train_size + validation_size > len(rows):
        raise HTTPException(status_code=422, detail="Not enough bars for the requested train and validation windows")
    strategy = _strategy(request)
    result = run_fixed_parameter_walk_forward(rows, train_size, validation_size, step, _backtest_config(request, strategy))
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **result}
