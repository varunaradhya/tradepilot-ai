from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.paper_trade import PaperTrade
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_evidence_aggregation import aggregate_paper_performance
from app.services.intraday_strategy import IntradayConfig
from app.services.paper_backtest_divergence import compare_backtest_to_paper
from app.services.research_store import research_store

router = APIRouter(prefix="/paper-trading/evidence", tags=["Paper Trading Evidence"])


@router.get("/divergence")
def paper_backtest_divergence(
    symbol: str = Query(min_length=1, max_length=30),
    interval: str = Query(default="5", pattern="^(1|5|15|25|60)$"),
    strategy_version: str = Query(default="V1", pattern="^(V1|V2)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized = symbol.strip().upper()
    bars = research_store.load(f"nse/{normalized}_intraday_{interval}m")
    if not bars:
        raise HTTPException(status_code=404, detail="No research data available for the requested Indian-market symbol")
    rows = []
    for bar in bars:
        row = bar.as_row()
        row["session"] = row["timestamp"].date().isoformat()
        rows.append(row)
    backtest = run_intraday_backtest(rows, IntradayBacktestConfig(strategy=IntradayConfig(), strategy_version=strategy_version))
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
