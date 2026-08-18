from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.paper_trade import PaperTrade
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_evidence_aggregation import aggregate_paper_performance, aggregate_scorecards
from app.services.intraday_scorecard import ScorecardConfig, build_intraday_scorecard
from app.services.intraday_strategy import IntradayConfig
from app.services.paper_backtest_divergence import compare_backtest_to_paper
from app.services.research_store import research_store
from app.services.strategy_paper_authorization import get_active_authorization
from app.services.strategy_qualification import QualificationPolicy, qualify_strategy
from app.services.strategy_readiness_gate import StrategyReadinessPolicy, evaluate_strategy_readiness
from app.services.intraday_robustness import run_robustness_analysis
from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward

router = APIRouter(prefix="/paper-trading/evidence", tags=["Paper Trading Evidence"])


def _research_rows(symbol: str, interval: str) -> list[dict]:
    bars = research_store.load(f"nse/{symbol}_intraday_{interval}m")
    rows = []
    for bar in bars:
        row = bar.as_row()
        row["session"] = row["timestamp"].date().isoformat()
        rows.append(row)
    return rows


def _research_evidence(symbol: str, interval: str, strategy_version: str) -> tuple[dict, dict, dict]:
    rows = _research_rows(symbol, interval)
    if not rows:
        raise HTTPException(status_code=404, detail="No research data available for the requested Indian-market symbol")
    config = IntradayBacktestConfig(strategy=IntradayConfig(), strategy_version=strategy_version)
    backtest = run_intraday_backtest(rows, config)
    robustness = run_robustness_analysis(rows, config, stress_costs=True)
    try:
        walk_forward = run_fixed_parameter_walk_forward(rows, 60, 20, None, config)
    except ValueError:
        walk_forward = {"windows": 0, "v2": {"windows": [], "summary": {}}}
    qualification = qualify_strategy(backtest, robustness, walk_forward, QualificationPolicy())
    return backtest, qualification, rows


@router.get("/divergence")
def paper_backtest_divergence(
    symbol: str = Query(min_length=1, max_length=30),
    interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"),
    strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized = symbol.strip().upper()
    backtest, _, _ = _research_evidence(normalized, interval, strategy_version)
    trades = db.query(PaperTrade).filter(PaperTrade.user_id == current_user.id, PaperTrade.strategy_version == strategy_version, PaperTrade.symbol == normalized).all()
    paper = aggregate_paper_performance(trades)
    return {
        "mode": "SIMULATION_ONLY",
        "symbol": normalized,
        "interval": interval,
        "strategy_version": strategy_version,
        "backtest": backtest,
        "paper": paper,
        "divergence": compare_backtest_to_paper(backtest, paper),
    }


@router.get("/readiness")
def strategy_readiness_review(
    symbol: str = Query(min_length=1, max_length=30),
    symbols: str = Query(default="", max_length=2000),
    interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"),
    strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized = symbol.strip().upper()
    backtest, qualification, rows = _research_evidence(normalized, interval, strategy_version)
    requested = list(dict.fromkeys(item.strip().upper() for item in (symbols or normalized).split(",") if item.strip()))
    if normalized not in requested:
        requested.insert(0, normalized)
    datasets = {item: _research_rows(item, interval) for item in requested}
    available = {item: data for item, data in datasets.items() if data}
    missing = [item for item in requested if item not in available]
    scorecard = build_intraday_scorecard(available, ScorecardConfig(minimum_trades=30, slippage_rate=backtest.get("execution_model", {}).get("slippage_rate", 0.0005)))
    cross_stock = aggregate_scorecards(scorecard.get("ranked", []), interval=interval, requested_symbols=requested, missing_symbols=missing)
    authorization = get_active_authorization(db, current_user.id, symbol=normalized, interval=interval, strategy_version=strategy_version)
    trades = db.query(PaperTrade).filter(
        PaperTrade.user_id == current_user.id,
        PaperTrade.strategy_version == strategy_version,
        PaperTrade.symbol == normalized,
    ).all()
    result = evaluate_strategy_readiness(
        backtest=backtest,
        research_qualification=qualification,
        cross_stock_evidence=cross_stock,
        paper_trades=trades,
        authorized_fingerprint=authorization.fingerprint if authorization else None,
        reference_now=datetime.now(timezone.utc),
        policy=StrategyReadinessPolicy(),
    )
    return {
        "symbol": normalized,
        "interval": interval,
        "strategy_version": strategy_version,
        **result,
    }
