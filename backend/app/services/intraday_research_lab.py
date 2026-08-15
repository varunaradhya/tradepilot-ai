from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


@dataclass(frozen=True)
class ResearchLabConfig:
    initial_capital: float = 100000.0
    slippage_rates: tuple[float, ...] = (0.0, 0.0005, 0.001, 0.0015, 0.002)
    entry_windows: tuple[str, ...] = (
        "09:15-10:00", "10:00-11:00", "11:00-12:30", "12:30-14:00", "14:00-15:15"
    )


def _time_key(row: dict) -> tuple[int, int]:
    ts = row.get("timestamp") or row.get("datetime") or row.get("date")
    if hasattr(ts, "hour"):
        return int(ts.hour), int(ts.minute)
    text = str(ts).replace("T", " ").split()[-1]
    parts = text.split(":")
    return int(parts[0]), int(parts[1])


def _bucket(row: dict) -> str:
    hour, minute = _time_key(row)
    total = hour * 60 + minute
    if total < 600: return "09:15-10:00"
    if total < 660: return "10:00-11:00"
    if total < 750: return "11:00-12:30"
    if total < 840: return "12:30-14:00"
    return "14:00-15:15"


def _summary(rows: Sequence[dict], config: IntradayBacktestConfig) -> dict:
    return {k: v for k, v in run_intraday_backtest(rows, config).items() if k != "trades_detail"}


def run_research_lab(rows: Sequence[dict], config: ResearchLabConfig = ResearchLabConfig()) -> dict:
    """Diagnostic research only; never selects parameters from the observed results."""
    ordered = sorted(rows, key=lambda r: str(r.get("timestamp") or r.get("datetime") or r.get("date")))
    if not ordered:
        return {"status": "NO_DATA"}
    baseline = _summary(ordered, IntradayBacktestConfig(initial_capital=config.initial_capital))
    slippage = []
    for rate in config.slippage_rates:
        result = _summary(ordered, IntradayBacktestConfig(initial_capital=config.initial_capital, slippage_rate=rate))
        slippage.append({"slippage_rate": rate, **result})
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for row in ordered:
        by_bucket[_bucket(row)].append(row)
    time_of_day = [
        {"window": name, **_summary(by_bucket[name], IntradayBacktestConfig(initial_capital=config.initial_capital))}
        for name in config.entry_windows if by_bucket.get(name)
    ]
    return {"status": "OK", "baseline": baseline, "slippage_sensitivity": slippage,
            "time_of_day": time_of_day, "method": "diagnostic_only_no_parameter_selection"}
