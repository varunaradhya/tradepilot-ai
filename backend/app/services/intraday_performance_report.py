from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def build_intraday_performance_report(
    rows: Sequence[dict],
    config: IntradayBacktestConfig = IntradayBacktestConfig(),
) -> dict:
    """Produce descriptive out-of-sample-style diagnostics without optimizing parameters."""
    baseline = run_intraday_backtest(rows, config)
    trades = baseline.get("trades_detail", [])
    daily: dict[str, float] = defaultdict(float)
    time_buckets: dict[str, list[float]] = defaultdict(list)

    for trade in trades:
        exit_time = _as_datetime(trade.get("exit_time"))
        entry_time = _as_datetime(trade.get("entry_time"))
        day = (exit_time or entry_time).date().isoformat() if (exit_time or entry_time) else "UNKNOWN"
        daily[day] += float(trade.get("pnl", 0.0))
        if entry_time:
            hour = entry_time.hour
            bucket = "09:15-10:30" if hour < 11 else "10:30-12:30" if hour < 13 else "12:30-14:30" if hour < 15 else "14:30-15:30"
            time_buckets[bucket].append(float(trade.get("pnl", 0.0)))

    ordered_days = sorted(daily)
    daily_values = [daily[d] for d in ordered_days]
    stress = run_intraday_backtest(
        rows,
        IntradayBacktestConfig(
            initial_capital=config.initial_capital,
            brokerage_rate=config.brokerage_rate * 1.25,
            slippage_rate=config.slippage_rate * 2,
            max_daily_loss_percent=config.max_daily_loss_percent,
            max_trades_per_session=config.max_trades_per_session,
            strategy=config.strategy,
            strategy_version=config.strategy_version,
        ),
    )
    buckets = {
        key: {
            "trades": len(values),
            "pnl": round(sum(values), 2),
            "win_rate_percent": round(sum(1 for value in values if value > 0) / len(values) * 100, 2) if values else 0.0,
        }
        for key, values in sorted(time_buckets.items())
    }
    return {
        "method": "descriptive performance diagnostics; no parameter optimization",
        "baseline": {key: value for key, value in baseline.items() if key != "trades_detail"},
        "cost_stress": {key: value for key, value in stress.items() if key != "trades_detail"},
        "cost_stress_return_delta_percent": round(stress["return_percent"] - baseline["return_percent"], 2),
        "daily": {day: round(value, 2) for day, value in zip(ordered_days, daily_values)},
        "profitable_days_percent": round(sum(1 for value in daily_values if value > 0) / len(daily_values) * 100, 2) if daily_values else 0.0,
        "time_of_day": buckets,
        "warnings": [
            "Daily and time-of-day diagnostics are descriptive and do not prove future profitability.",
            "Cost stress is a sensitivity diagnostic, not a parameter optimization.",
        ],
    }
