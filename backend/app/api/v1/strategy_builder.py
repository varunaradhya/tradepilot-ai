from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig
from app.services.intraday_strategy_comparison import compare_intraday_strategies
from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward
from app.services.intraday_robustness import run_robustness_analysis
from app.services.strategy_qualification import QualificationPolicy, qualify_strategy
from app.services.strategy_readiness import ReadinessPolicy, build_strategy_readiness
from app.services.research_store import research_store
from app.services.intraday_scorecard import build_intraday_scorecard, ScorecardConfig
from app.services.intraday_evidence_aggregation import aggregate_scorecards
from app.services.intraday_historical_validation import HistoricalValidationConfig, validate_historical_datasets
from app.models.paper_trade import PaperTrade

router = APIRouter(prefix="/strategy-builder", tags=["Strategy Builder"])

class StrategyBuildRequest(BaseModel):
    trade_direction: str = Field(default="LONG_ONLY", pattern="^(LONG_ONLY|LONG_SHORT)$")
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
    min_trades: int = Field(default=30, ge=1, le=100000)
    min_profit_factor: float = Field(default=1.10, ge=0, le=10)
    min_positive_sensitivity_percent: float = Field(default=60.0, ge=0, le=100)
    min_stable_profit_factor_percent: float = Field(default=60.0, ge=0, le=100)
    max_drawdown_percent: float = Field(default=15.0, ge=0, le=100)
    min_walk_forward_success_percent: float = Field(default=55.0, ge=0, le=100)

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
    return IntradayConfig(trade_direction=request.trade_direction, opening_bars=request.opening_bars, fast_period=request.fast_period, slow_period=request.slow_period, volume_period=request.volume_period, min_volume_ratio=request.min_volume_ratio, max_gap_percent=request.max_gap_percent, risk_per_trade=request.risk_per_trade, max_position_percent=request.max_position_percent, atr_period=request.atr_period, atr_stop_multiple=request.atr_stop_multiple, reward_multiple=request.reward_multiple)

def _backtest_config(request: StrategyBuildRequest, strategy: IntradayConfig, version: str = "V1") -> IntradayBacktestConfig:
    return IntradayBacktestConfig(initial_capital=request.initial_capital, brokerage_rate=request.brokerage_rate, slippage_rate=request.slippage_rate, max_daily_loss_percent=request.max_daily_loss_percent, max_trades_per_session=request.max_trades_per_session, strategy=strategy, strategy_version=version)

def _policy(request: StrategyBuildRequest) -> QualificationPolicy:
    return QualificationPolicy(min_trades=request.min_trades, min_profit_factor=request.min_profit_factor, min_positive_return_percent=request.min_positive_sensitivity_percent, min_pf_above_one_percent=request.min_stable_profit_factor_percent, max_drawdown_percent=request.max_drawdown_percent, min_walk_forward_success_percent=request.min_walk_forward_success_percent)

def _qualification(request: StrategyBuildRequest, rows: list[dict], train_size: int, validation_size: int, step: int | None):
    strategy = _strategy(request); config = _backtest_config(request, strategy)
    if train_size + validation_size > len(rows):
        raise HTTPException(status_code=422, detail="Not enough bars for the requested train and validation windows")
    backtest = run_intraday_backtest(rows, config)
    robustness = run_robustness_analysis(rows, config, stress_costs=True)
    walk_forward = run_fixed_parameter_walk_forward(rows, train_size, validation_size, step, config)
    qualification = qualify_strategy(backtest, robustness, walk_forward, _policy(request))
    return strategy, config, backtest, robustness, walk_forward, qualification

def _basket(symbols: str, interval: str):
    requested = list(dict.fromkeys(item.strip().upper() for item in symbols.split(",") if item.strip()))
    datasets: dict[str, list[dict]] = {}
    missing: list[str] = []
    for item in requested:
        _, item_rows = _rows(item, interval)
        if item_rows:
            datasets[item] = item_rows
        else:
            missing.append(item)
    return requested, datasets, missing

@router.post("/backtest")
def build_and_backtest(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    strategy = _strategy(request)
    result = run_intraday_backtest(rows, _backtest_config(request, strategy))
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, "strategy": strategy.__dict__, "execution": {"brokerage_rate": request.brokerage_rate, "slippage_rate": request.slippage_rate, "max_daily_loss_percent": request.max_daily_loss_percent, "max_trades_per_session": request.max_trades_per_session}, **result}

@router.post("/compare")
def compare_versions(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    strategy = _strategy(request)
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **compare_intraday_strategies(rows, _backtest_config(request, strategy))}

@router.post("/walk-forward")
def walk_forward_validation(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), train_size: int = Query(default=60, ge=10, le=5000), validation_size: int = Query(default=20, ge=5, le=2000), step: int | None = Query(default=None, ge=1, le=2000), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    if train_size + validation_size > len(rows): raise HTTPException(status_code=422, detail="Not enough bars for the requested train and validation windows")
    strategy = _strategy(request)
    result = run_fixed_parameter_walk_forward(rows, train_size, validation_size, step, _backtest_config(request, strategy))
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **result}

@router.post("/robustness")
def robustness_validation(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), stress_costs: bool = Query(default=True), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    strategy = _strategy(request)
    result = run_robustness_analysis(rows, _backtest_config(request, strategy), stress_costs=stress_costs)
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **result}

@router.post("/qualify")
def qualify_strategy_for_paper(symbol: str = Query(min_length=1, max_length=30), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), train_size: int = Query(default=60, ge=10, le=5000), validation_size: int = Query(default=20, ge=5, le=2000), step: int | None = Query(default=None, ge=1, le=2000), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    dataset, rows = _rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    _, _, backtest, robustness, walk_forward, qualification = _qualification(request, rows, train_size, validation_size, step)
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, "qualification": qualification, "backtest": {k: v for k, v in backtest.items() if k != "trades_detail"}, "robustness": robustness["summary"], "walk_forward": {"windows": walk_forward["windows"], "v2_summary": walk_forward["v2"]["summary"]}}

@router.post("/historical-validation")
def historical_validation(symbols: str = Query(default="", max_length=2000), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), train_fraction: float = Query(default=0.70, ge=0.5, lt=1.0), min_train_bars: int = Query(default=40, ge=10, le=50000), min_test_bars: int = Query(default=20, ge=5, le=50000), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    requested, datasets, missing = _basket(symbols, interval)
    if not requested: raise HTTPException(status_code=422, detail="At least one symbol is required")
    strategy = _strategy(request)
    result = validate_historical_datasets(datasets, _backtest_config(request, strategy), HistoricalValidationConfig(train_fraction=train_fraction, min_train_bars=min_train_bars, min_test_bars=min_test_bars))
    return {"interval": interval, "requested_symbols": requested, "missing_symbols": missing, **result}

@router.post("/evidence")
def evidence_report(symbols: str = Query(default="", max_length=2000), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), train_fraction: float = Query(default=0.70, ge=0.5, lt=1.0), min_train_bars: int = Query(default=40, ge=10, le=50000), min_test_bars: int = Query(default=20, ge=5, le=50000), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user)):
    del current_user
    requested, datasets, missing = _basket(symbols, interval)
    if not requested: raise HTTPException(status_code=422, detail="At least one symbol is required")
    strategy = _strategy(request)
    backtest_config = _backtest_config(request, strategy)
    scorecard = build_intraday_scorecard(datasets, ScorecardConfig(initial_capital=request.initial_capital, minimum_trades=request.min_trades, slippage_rate=request.slippage_rate))
    evidence = aggregate_scorecards(scorecard.get("ranked", []), interval=interval, requested_symbols=requested, missing_symbols=missing)
    historical = validate_historical_datasets(datasets, backtest_config, HistoricalValidationConfig(train_fraction=train_fraction, min_train_bars=min_train_bars, min_test_bars=min_test_bars))
    return {"interval": interval, "requested_symbols": requested, "missing_symbols": missing, "cross_stock": evidence, "historical_out_of_sample": historical, "research_policy": {"parameter_selection": False, "cross_stock_optimization": False, "fixed_parameters": True}}

@router.post("/readiness")
def strategy_readiness(symbol: str = Query(min_length=1, max_length=30), symbols: str = Query(default="", max_length=2000), strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"), interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"), train_size: int = Query(default=60, ge=10, le=5000), validation_size: int = Query(default=20, ge=5, le=2000), step: int | None = Query(default=None, ge=1, le=2000), request: StrategyBuildRequest = ..., current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset, rows = _rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    _, _, backtest, robustness, walk_forward, qualification = _qualification(request, rows, train_size, validation_size, step)
    requested, datasets, missing = _basket(symbols or symbol, interval)
    scorecard = build_intraday_scorecard(datasets, ScorecardConfig(minimum_trades=request.min_trades, slippage_rate=request.slippage_rate))
    evidence = aggregate_scorecards(scorecard.get("ranked", []), interval=interval, requested_symbols=requested, missing_symbols=missing)
    paper_trades = db.query(PaperTrade).filter(PaperTrade.user_id == current_user.id, PaperTrade.strategy_version == strategy_version).all()
    readiness = build_strategy_readiness(qualification, evidence, paper_trades, ReadinessPolicy())
    return {"symbol": symbol.strip().upper(), "interval": interval, "strategy_version": strategy_version, "dataset": dataset, "qualification": qualification, "backtest": {k: v for k, v in backtest.items() if k != "trades_detail"}, "robustness": robustness["summary"], "walk_forward": {"windows": walk_forward["windows"], "v1_summary": walk_forward["v1"]["summary"], "v2_summary": walk_forward["v2"]["summary"]}, "cross_stock": evidence, "readiness": readiness}
