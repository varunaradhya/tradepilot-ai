from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.intraday_strategy import IntradayConfig
from app.services.intraday_strategy_v2 import IntradayV2Config


def compare_intraday_strategies(rows: Sequence[dict], config: IntradayBacktestConfig = IntradayBacktestConfig()) -> dict:
    """Run V1 and V2 under identical assumptions; never optimize from observed results."""
    base = config.strategy
    v1_strategy = base if isinstance(base, IntradayConfig) else IntradayConfig()
    v2_strategy = base if isinstance(base, IntradayV2Config) else IntradayV2Config(**v1_strategy.__dict__)
    v1 = run_intraday_backtest(rows, replace(config, strategy=v1_strategy, strategy_version="V1"))
    v2 = run_intraday_backtest(rows, replace(config, strategy=v2_strategy, strategy_version="V2"))
    return {
        "assumptions": {"initial_capital": config.initial_capital, "brokerage_rate": config.brokerage_rate,
                        "slippage_rate": config.slippage_rate, "max_daily_loss_percent": config.max_daily_loss_percent,
                        "max_trades_per_session": config.max_trades_per_session, "parameter_selection": False},
        "v1": {k: v for k, v in v1.items() if k != "trades_detail"},
        "v2": {k: v for k, v in v2.items() if k != "trades_detail"},
        "delta": {
            "return_percent": round(v2["return_percent"] - v1["return_percent"], 4),
            "profit_factor": None if v1["profit_factor"] is None or v2["profit_factor"] is None else round(v2["profit_factor"] - v1["profit_factor"], 4),
            "win_rate_percent": round(v2["win_rate_percent"] - v1["win_rate_percent"], 4),
            "max_drawdown_percent": round(v2["max_drawdown_percent"] - v1["max_drawdown_percent"], 4),
            "expectancy": round(v2["expectancy"] - v1["expectancy"], 4),
        },
    }
