from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.brokers.dhan import DhanAPIError, DhanClient
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.broker_service import get_access_token, get_user_broker
from app.services.instrument_master_service import InstrumentMasterError, instrument_master
from app.services.intraday_research_service import backtest_intraday_dataset, download_intraday_dataset
from app.services.research_lab import analyze_dataset
from app.services.research_service import download_daily_dataset
from app.services.research_store import research_store
from app.services.intraday_experiment import run_intraday_experiment
from app.services.intraday_batch_research import run_multi_stock_research
from app.services.intraday_regime_analysis import build_benchmark_regime_analysis
from app.services.intraday_regime_report import build_intraday_regime_report
from app.services.intraday_research_lab import run_research_lab
from app.services.intraday_scorecard import build_intraday_scorecard, ScorecardConfig
from app.services.intraday_performance_report import build_intraday_performance_report
from app.services.intraday_evidence_aggregation import aggregate_scorecards
from app.services.intraday_backtest import IntradayBacktestConfig

router = APIRouter(prefix="/research", tags=["Research"])

@router.get("/instruments")
def search_research_instruments(q: str = Query(min_length=2, max_length=80), current_user: User = Depends(get_current_user)):
    del current_user
    try:
        return [{"security_id": item.security_id, "symbol": item.symbol, "name": item.name, "exchange": "NSE", "exchange_segment": item.exchange_segment, "isin": item.isin} for item in instrument_master.search(q)]
    except InstrumentMasterError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

def _dhan_client(db: Session, current_user: User) -> DhanClient:
    connection = get_user_broker(db, current_user.id, "dhan")
    if connection is None: raise HTTPException(status_code=404, detail="Dhan is not connected.")
    return DhanClient(connection.client_id, get_access_token(connection))

def _dataset_rows(symbol: str, interval: str):
    dataset = f"nse/{symbol.strip().upper()}_intraday_{interval}m"
    bars = research_store.load(dataset)
    rows = []
    for bar in bars:
        row = bar.as_row(); row["session"] = row["timestamp"].date().isoformat(); rows.append(row)
    return dataset, rows

def _requested_rows(symbols: str, interval: str):
    datasets = {}; missing = []
    for symbol in dict.fromkeys(s.strip().upper() for s in symbols.split(",") if s.strip()):
        _, rows = _dataset_rows(symbol, interval)
        if rows: datasets[symbol] = rows
        else: missing.append(symbol)
    return datasets, missing

def _requested_symbols(symbols: str) -> list[str]:
    return list(dict.fromkeys(s.strip().upper() for s in symbols.split(",") if s.strip()))

@router.post("/daily")
def download_research_daily(symbol: str = Query(min_length=1, max_length=30), start: date | None = None, end: date | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    end_date=end or date.today(); start_date=start or (end_date-timedelta(days=365*5))
    if start_date>=end_date: raise HTTPException(status_code=422, detail="start must be before end")
    if (end_date-start_date).days>365*10: raise HTTPException(status_code=422, detail="Research history is limited to 10 years per request")
    try: result=download_daily_dataset(_dhan_client(db,current_user),symbol,start_date,end_date)
    except (ValueError,InstrumentMasterError) as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except DhanAPIError as exc: raise HTTPException(status_code=502,detail=str(exc)) from exc
    return {"status":"stored","symbol":result.symbol,"dataset":result.dataset,"bars":result.bars,"start":result.start,"end":result.end,"valid":result.valid}

@router.post("/intraday")
def download_research_intraday(symbol: str = Query(min_length=1,max_length=30), interval: str = Query(default="5",pattern="^(1|5|15|25|60)$"), start: date | None=None, end: date | None=None, current_user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    end_date=end or date.today(); start_date=start or (end_date-timedelta(days=365*5))
    if start_date>=end_date: raise HTTPException(status_code=422,detail="start must be before end")
    if (end_date-start_date).days>365*5: raise HTTPException(status_code=422,detail="Intraday research history is limited to 5 years per request")
    try: result=download_intraday_dataset(_dhan_client(db,current_user),symbol,start_date,end_date,interval)
    except (ValueError,InstrumentMasterError) as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except DhanAPIError as exc: raise HTTPException(status_code=502,detail=str(exc)) from exc
    return {"status":"stored","symbol":result.symbol,"interval":result.interval,"dataset":result.dataset,"bars":result.bars,"start":result.start,"end":result.end,"valid":result.valid}

@router.get("/intraday/backtest")
def backtest_research_intraday(symbol: str=Query(min_length=1,max_length=30), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), current_user: User=Depends(get_current_user)):
    del current_user
    try: return backtest_intraday_dataset(symbol,interval)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@router.get("/intraday/performance")
def intraday_performance(symbol: str=Query(min_length=1,max_length=30), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), current_user: User=Depends(get_current_user)):
    del current_user
    dataset, rows = _dataset_rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **build_intraday_performance_report(rows, IntradayBacktestConfig())}

@router.get("/intraday/experiment")
def experiment_research_intraday(symbol: str=Query(min_length=1,max_length=30), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), current_user: User=Depends(get_current_user)):
    del current_user
    dataset, rows = _dataset_rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404,detail=f"Intraday dataset not found: {dataset}")
    return {"symbol": symbol.strip().upper(),"interval":interval,"dataset":dataset,**run_intraday_experiment(rows)}

@router.get("/intraday/batch")
def batch_research_intraday(symbols: str=Query(min_length=1, max_length=1000), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), current_user: User=Depends(get_current_user)):
    del current_user
    try: return run_multi_stock_research([item for item in symbols.split(",")], interval=interval)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.get("/intraday/scorecard")
def intraday_scorecard(symbols: str=Query(min_length=1, max_length=2000), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), min_trades: int=Query(default=20, ge=1, le=100000), slippage: float=Query(default=0.001, ge=0, le=0.01), current_user: User = Depends(get_current_user)):
    del current_user
    datasets, missing = _requested_rows(symbols, interval)
    result = build_intraday_scorecard(datasets, ScorecardConfig(minimum_trades=min_trades, slippage_rate=slippage)); result["missing_datasets"] = missing; result["interval"] = interval
    return result

@router.get("/intraday/evidence")
def intraday_evidence(symbols: str=Query(min_length=1, max_length=2000), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), min_trades: int=Query(default=20, ge=1, le=100000), slippage: float=Query(default=0.001, ge=0, le=0.01), current_user: User = Depends(get_current_user)):
    del current_user
    requested = _requested_symbols(symbols)
    datasets, missing = _requested_rows(symbols, interval)
    scorecard = build_intraday_scorecard(datasets, ScorecardConfig(minimum_trades=min_trades, slippage_rate=slippage))
    result = aggregate_scorecards(scorecard.get("ranked", []), interval=interval, requested_symbols=requested, missing_symbols=missing)
    result["assumptions"] = scorecard.get("assumptions", {})
    return result

@router.get("/intraday/research-lab")
def intraday_research_lab(symbol: str=Query(min_length=1,max_length=30), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), current_user: User=Depends(get_current_user)):
    del current_user
    dataset, rows = _dataset_rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Intraday dataset not found: {dataset}")
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **run_research_lab(rows)}

@router.get("/intraday/regime-analysis")
def intraday_regime_analysis(benchmark: str=Query(default="NIFTY", min_length=1, max_length=30), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), lookback: int=Query(default=50, ge=20, le=500), step: int=Query(default=25, ge=1, le=500), current_user: User=Depends(get_current_user)):
    del current_user
    dataset, rows = _dataset_rows(benchmark, interval)
    if not rows: raise HTTPException(status_code=404, detail=f"Benchmark dataset not found: {dataset}")
    return {"benchmark": benchmark.strip().upper(), "interval": interval, **build_benchmark_regime_analysis(rows, lookback=lookback, step=step)}

@router.get("/intraday/regime-report")
def intraday_regime_report(symbol: str=Query(min_length=1,max_length=30), benchmark: str=Query(default="NIFTY", min_length=1,max_length=30), sector: str | None=Query(default=None,max_length=30), interval: str=Query(default="5",pattern="^(1|5|15|25|60)$"), current_user: User=Depends(get_current_user)):
    del current_user
    _, rows = _dataset_rows(symbol, interval)
    if not rows: raise HTTPException(status_code=404,detail=f"Intraday dataset not found: {symbol.strip().upper()}")
    _, benchmark_rows = _dataset_rows(benchmark, interval)
    if not benchmark_rows: raise HTTPException(status_code=404,detail=f"Benchmark dataset not found: {benchmark.strip().upper()}")
    sector_rows = None
    if sector:
        _, sector_rows = _dataset_rows(sector, interval)
        if not sector_rows: raise HTTPException(status_code=404,detail=f"Sector dataset not found: {sector.strip().upper()}")
    return {"symbol":symbol.strip().upper(),"benchmark":benchmark.strip().upper(),"sector":sector.strip().upper() if sector else None,"interval":interval,**build_intraday_regime_report(rows, benchmark_rows, sector_rows)}

@router.get("/analyze")
def analyze_research_dataset(symbol: str=Query(min_length=1,max_length=30), current_user: User=Depends(get_current_user)):
    del current_user
    try: return analyze_dataset(symbol)
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
