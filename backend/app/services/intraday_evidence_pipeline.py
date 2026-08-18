from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest


@dataclass(frozen=True)
class EvidencePipelineConfig:
    required_years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025)
    min_sessions_per_year: int = 20
    min_total_sessions: int = 100
    min_oos_sessions: int = 20


def _session(row: dict) -> str:
    value = row.get("session") or row.get("timestamp") or row.get("time") or row.get("date")
    return str(value)[:10]


def _timestamp(row: dict) -> str:
    value = row.get("timestamp") or row.get("time") or row.get("date")
    return str(value)


def _validate_rows(rows: Sequence[dict]) -> None:
    previous_session = None
    previous_timestamp = None
    seen: set[str] = set()
    for row in rows:
        session = _session(row)
        timestamp = _timestamp(row)
        if previous_session is not None and session < previous_session:
            raise ValueError("research rows must be chronological by session")
        if previous_session == session and previous_timestamp and timestamp < previous_timestamp:
            raise ValueError("research rows must be chronological within a session")
        if timestamp in seen:
            raise ValueError("duplicate research timestamp detected")
        seen.add(timestamp)
        for field in ("open", "high", "low", "close"):
            value = float(row[field])
            if value <= 0:
                raise ValueError(f"invalid non-positive {field}")
        if float(row["low"]) > float(row["high"]):
            raise ValueError("invalid OHLC range")
        if not float(row["low"]) <= float(row["close"]) <= float(row["high"]):
            raise ValueError("close must be inside OHLC range")
        previous_session = session
        previous_timestamp = timestamp


def _fingerprint(config: IntradayBacktestConfig, dataset_name: str, rows: Sequence[dict]) -> str:
    payload = {
        "dataset": dataset_name,
        "first_timestamp": _timestamp(rows[0]) if rows else None,
        "last_timestamp": _timestamp(rows[-1]) if rows else None,
        "rows": len(rows),
        "strategy_version": config.strategy_version,
        "strategy": config.strategy.__dict__,
        "execution": {
            "brokerage_rate": config.brokerage_rate,
            "slippage_rate": config.slippage_rate,
            "spread_bps": config.spread_bps,
            "market_impact_bps": config.market_impact_bps,
            "impact_reference_value": config.impact_reference_value,
            "max_volume_participation": config.max_volume_participation,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return sha256(encoded).hexdigest()


def run_multi_year_evidence(
    rows: Sequence[dict],
    dataset_name: str,
    config: IntradayBacktestConfig = IntradayBacktestConfig(),
    pipeline: EvidencePipelineConfig = EvidencePipelineConfig(),
) -> dict:
    """Produce reproducible baseline evidence without optimizing parameters.

    Missing years, insufficient sessions, malformed data and empty OOS samples
    fail closed. The function reports evidence; it never promotes a strategy.
    """
    rows = list(rows)
    if not rows:
        raise ValueError("research dataset is empty")
    _validate_rows(rows)
    years = sorted({int(_session(row)[:4]) for row in rows})
    sessions = sorted({_session(row) for row in rows})
    counts = {year: sum(1 for session in sessions if int(session[:4]) == year) for year in years}
    missing_years = [year for year in pipeline.required_years if year not in counts]
    insufficient_years = [year for year in pipeline.required_years if counts.get(year, 0) < pipeline.min_sessions_per_year]
    if missing_years or insufficient_years or len(sessions) < pipeline.min_total_sessions:
        raise ValueError(
            "INSUFFICIENT_MULTI_YEAR_EVIDENCE: "
            f"missing_years={missing_years}; insufficient_years={insufficient_years}; "
            f"total_sessions={len(sessions)}"
        )

    yearly: list[dict] = []
    for year in pipeline.required_years:
        year_rows = [row for row in rows if int(_session(row)[:4]) == year]
        result = run_intraday_backtest(year_rows, config)
        yearly.append({
            "year": year,
            "sessions": counts[year],
            "bars": len(year_rows),
            "return_percent": result["return_percent"],
            "trades": result["trades"],
            "win_rate_percent": result["win_rate_percent"],
            "profit_factor": result["profit_factor"],
            "expectancy": result["expectancy"],
            "max_drawdown_percent": result["max_drawdown_percent"],
            "total_costs": result["total_costs"],
        })

    # Untouched final OOS block: the latest required year is never used for
    # parameter selection and is reported independently from the earlier years.
    oos_year = pipeline.required_years[-1]
    oos_rows = [row for row in rows if int(_session(row)[:4]) == oos_year]
    if len({_session(row) for row in oos_rows}) < pipeline.min_oos_sessions:
        raise ValueError("INSUFFICIENT_OOS_SESSIONS")
    oos = run_intraday_backtest(oos_rows, config)
    fingerprint = _fingerprint(config, dataset_name, rows)
    return {
        "status": "EVIDENCE_READY",
        "dataset": dataset_name,
        "strategy_fingerprint": fingerprint,
        "strategy_version": config.strategy_version,
        "period": {"start_year": pipeline.required_years[0], "end_year": pipeline.required_years[-1]},
        "rows": len(rows),
        "sessions": len(sessions),
        "years": years,
        "parameter_selection": "FIXED_BEFORE_RUN",
        "optimization": False,
        "yearly": yearly,
        "untouched_oos": {
            "year": oos_year,
            "sessions": len({_session(row) for row in oos_rows}),
            "bars": len(oos_rows),
            "return_percent": oos["return_percent"],
            "trades": oos["trades"],
            "win_rate_percent": oos["win_rate_percent"],
            "profit_factor": oos["profit_factor"],
            "expectancy": oos["expectancy"],
            "max_drawdown_percent": oos["max_drawdown_percent"],
        },
        "execution_assumptions": {
            "brokerage_rate": config.brokerage_rate,
            "slippage_rate": config.slippage_rate,
            "spread_bps": config.spread_bps,
            "market_impact_bps": config.market_impact_bps,
            "max_volume_participation": config.max_volume_participation,
        },
    }
