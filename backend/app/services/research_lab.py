from __future__ import annotations

from dataclasses import asdict

from app.services.backtest_service import BacktestConfig, run_daily_backtest
from app.services.market_regime import classify_market_regime
from app.services.research_metrics import summarize_equity_curve, summarize_trades
from app.services.research_store import ResearchStore, research_store


def analyze_dataset(symbol: str, dataset: str | None = None, store: ResearchStore = research_store) -> dict:
    normalized = symbol.strip().upper()
    dataset_name = dataset or f"nse/{normalized}_daily"
    bars = store.load(dataset_name)
    if len(bars) < 80:
        raise ValueError("At least 80 validated daily bars are required for research")
    rows = [bar.as_row() for bar in bars]
    result = run_daily_backtest(rows, BacktestConfig())
    regime = classify_market_regime([float(row["close"]) for row in rows])
    equity = result.pop("equity_curve", [])
    result["symbol"] = normalized
    result["dataset"] = dataset_name
    result["regime"] = asdict(regime)
    result["equity_metrics"] = summarize_equity_curve(equity)
    result["trade_metrics"] = summarize_trades(result["trades_detail"])
    return result
