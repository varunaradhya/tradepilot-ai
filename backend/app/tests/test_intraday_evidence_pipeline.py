from unittest.mock import patch

import pytest

from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_evidence_pipeline import EvidencePipelineConfig, run_multi_year_evidence


def _rows(years=(2021, 2022, 2023, 2024, 2025), sessions_per_year=20):
    rows = []
    for year in years:
        for day in range(1, sessions_per_year + 1):
            session = f"{year}-01-{day:02d}"
            for minute in ("09:15:00", "09:20:00"):
                rows.append({"session": session, "timestamp": f"{session}T{minute}", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 10000})
    return rows


def test_multi_year_evidence_fails_closed_when_a_required_year_is_missing():
    rows = _rows(years=(2021, 2022, 2023, 2024))
    with pytest.raises(ValueError, match="INSUFFICIENT_MULTI_YEAR_EVIDENCE"):
        run_multi_year_evidence(rows, "nse/test", pipeline=EvidencePipelineConfig())


def test_multi_year_evidence_rejects_duplicate_timestamp():
    rows = _rows()
    rows.insert(1, dict(rows[0]))
    with pytest.raises(ValueError, match="duplicate research timestamp"):
        run_multi_year_evidence(rows, "nse/test")


def test_multi_year_evidence_rejects_out_of_order_rows():
    rows = _rows()
    rows[0], rows[1] = rows[1], rows[0]
    with pytest.raises(ValueError, match="chronological"):
        run_multi_year_evidence(rows, "nse/test")


def test_multi_year_evidence_is_reproducible_and_keeps_latest_year_oos():
    rows = _rows()
    result = {"return_percent": 8.0, "trades": 40, "win_rate_percent": 60.0, "profit_factor": 1.5, "expectancy": 200.0, "max_drawdown_percent": 5.0, "total_costs": 1000.0}
    with patch("app.services.intraday_evidence_pipeline.run_intraday_backtest", return_value=result):
        first = run_multi_year_evidence(rows, "nse/test", IntradayBacktestConfig(strategy_version="V1"))
        second = run_multi_year_evidence(rows, "nse/test", IntradayBacktestConfig(strategy_version="V1"))
    assert first["status"] == "EVIDENCE_READY"
    assert first["untouched_oos"]["year"] == 2025
    assert first["strategy_fingerprint"] == second["strategy_fingerprint"]
    assert first["yearly"][-1]["year"] == 2025
    assert first["optimization"] is False
