from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


@dataclass(frozen=True)
class HistoricalValidationConfig:
    train_fraction: float = 0.70
    min_train_bars: int = 40
    min_test_bars: int = 20


def _session_key(row: dict) -> str:
    session = row.get("session")
    if session is not None:
        return str(session)
    timestamp = row.get("timestamp") or row.get("time")
    return str(timestamp)[:10] if timestamp is not None else "UNKNOWN"


def _split_at_session_boundary(rows: Sequence[dict], train_fraction: float) -> tuple[list[dict], list[dict]]:
    if not rows:
        return [], []
    sessions: list[str] = []
    for row in rows:
        key = _session_key(row)
        if not sessions or sessions[-1] != key:
            sessions.append(key)
    if len(sessions) < 2:
        cut = max(1, min(len(rows) - 1, int(len(rows) * train_fraction)))
        return list(rows[:cut]), list(rows[cut:])
    target = len(sessions) * train_fraction
    train_session_count = max(1, min(len(sessions) - 1, int(target)))
    train_sessions = set(sessions[:train_session_count])
    train = [row for row in rows if _session_key(row) in train_sessions]
    test = [row for row in rows if _session_key(row) not in train_sessions]
    return train, test


def _compact(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "trades_detail"}


def validate_historical_datasets(
    datasets: dict[str, Sequence[dict]],
    backtest_config: IntradayBacktestConfig = IntradayBacktestConfig(),
    config: HistoricalValidationConfig = HistoricalValidationConfig(),
) -> dict:
    if not 0.5 <= config.train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0.5 inclusive and 1.0 exclusive")

    ranked: list[dict] = []
    for raw_symbol, raw_rows in datasets.items():
        symbol = raw_symbol.strip().upper()
        rows = list(raw_rows)
        train, test = _split_at_session_boundary(rows, config.train_fraction)
        reasons: list[str] = []
        if len(train) < config.min_train_bars:
            reasons.append("INSUFFICIENT_TRAIN_BARS")
        if len(test) < config.min_test_bars:
            reasons.append("INSUFFICIENT_OUT_OF_SAMPLE_BARS")

        train_result = run_intraday_backtest(train, backtest_config) if train else _compact(run_intraday_backtest([], backtest_config))
        test_result = run_intraday_backtest(test, backtest_config) if test else _compact(run_intraday_backtest([], backtest_config))
        train_return = float(train_result.get("return_percent") or 0.0)
        test_return = float(test_result.get("return_percent") or 0.0)
        train_pf = float(train_result.get("profit_factor") or 0.0)
        test_pf = float(test_result.get("profit_factor") or 0.0)
        if test_result.get("trades", 0) == 0:
            reasons.append("NO_OUT_OF_SAMPLE_TRADES")
        if test_return <= 0:
            reasons.append("NON_POSITIVE_OUT_OF_SAMPLE_RETURN")
        if test_pf and train_pf and test_pf < train_pf * 0.50:
            reasons.append("PROFIT_FACTOR_DEGRADATION")

        status = "PASS" if not reasons else "REVIEW"
        ranked.append({
            "symbol": symbol,
            "status": status,
            "train": {"bars": len(train), **_compact(train_result)},
            "out_of_sample": {"bars": len(test), **_compact(test_result)},
            "return_degradation_percent": round(test_return - train_return, 2),
            "profit_factor_degradation_percent": round((test_pf - train_pf) / train_pf * 100, 2) if train_pf else None,
            "reasons": reasons,
        })

    passed = sum(1 for item in ranked if item["status"] == "PASS")
    tested = len(ranked)
    return {
        "status": "OK" if ranked else "NO_DATA",
        "method": "session-boundary chronological out-of-sample validation; fixed parameters",
        "assumptions": {
            "train_fraction": config.train_fraction,
            "parameter_selection": False,
            "cross_stock_optimization": False,
        },
        "summary": {
            "symbols_tested": tested,
            "passed_symbols": passed,
            "pass_percent": round(passed / tested * 100, 2) if tested else 0.0,
        },
        "ranked": ranked,
    }
