from __future__ import annotations

from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_v2_backtest import run_intraday_v2_backtest
from app.services.market_regime import classify_market_regime


def build_intraday_regime_report(rows: Sequence[dict], benchmark_rows: Sequence[dict] | None = None, sector_rows: Sequence[dict] | None = None) -> dict:
    if not rows:
        return {"status": "NO_DATA", "comparison": None}
    benchmark = benchmark_rows or rows
    regime = classify_market_regime([float(r["close"]) for r in benchmark])
    v1 = run_intraday_backtest(rows, IntradayBacktestConfig())
    v2 = run_intraday_v2_backtest(rows, benchmark_rows, sector_rows)
    return {
        "status": "OK",
        "benchmark_regime": {"label": regime.label, "trend_score": regime.trend_score, "momentum_percent": regime.momentum_percent, "volatility_percent": regime.volatility_percent, "confidence": regime.confidence},
        "comparison": {
            "v1": {k: v for k, v in v1.items() if k != "trades_detail"},
            "v2": {k: v for k, v in v2.items() if k != "trades_detail"},
            "return_delta_percent": round(v2["return_percent"] - v1["return_percent"], 2),
            "profit_factor_delta": None if v1["profit_factor"] is None or v2["profit_factor"] is None else round(v2["profit_factor"] - v1["profit_factor"], 4),
        },
        "method": "benchmark_regime_descriptive_comparison",
        "optimization_performed": False,
    }
