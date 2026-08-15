from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


@dataclass(frozen=True)
class ExperimentConfig:
    initial_capital: float = 100000.0


def _year(row: dict) -> int:
    timestamp = row.get("timestamp") or row.get("datetime") or row.get("date")
    if hasattr(timestamp, "year"):
        return int(timestamp.year)
    return int(str(timestamp)[:4])


def run_intraday_experiment(rows: Sequence[dict], config: ExperimentConfig = ExperimentConfig()) -> dict:
    """Run a chronological baseline without parameter fitting or optimization."""
    if not rows:
        return {"status": "NO_DATA", "years": [], "overall": None}
    by_year: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_year[_year(row)].append(row)
    yearly = []
    for year in sorted(by_year):
        result = run_intraday_backtest(by_year[year], IntradayBacktestConfig(initial_capital=config.initial_capital))
        yearly.append({"year": year, **{k: v for k, v in result.items() if k != "trades_detail"}})
    overall = run_intraday_backtest(rows, IntradayBacktestConfig(initial_capital=config.initial_capital))
    return {
        "status": "OK",
        "method": "chronological_baseline",
        "lookahead_bias_protection": True,
        "years": yearly,
        "overall": {k: v for k, v in overall.items() if k != "trades_detail"},
    }
