from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services import backtest_service
from app.services.algo_strategy import Signal
from app.services.india_equity_fee_service import IndiaEquityIntradayFeeSchedule


def _rows(count: int = 62) -> list[dict]:
    start = datetime(2026, 9, 1, 9, 15)
    return [
        {
            "timestamp": (start + timedelta(minutes=5 * i)).isoformat(),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
        }
        for i in range(count)
    ]


def test_backtest_rejects_duplicate_timestamps() -> None:
    rows = _rows()
    rows[10]["timestamp"] = rows[9]["timestamp"]
    with pytest.raises(ValueError, match="strictly increasing"):
        backtest_service.run_daily_backtest(rows)


def test_backtest_rejects_backward_timestamps() -> None:
    rows = _rows()
    rows[10]["timestamp"] = rows[8]["timestamp"]
    with pytest.raises(ValueError, match="strictly increasing"):
        backtest_service.run_daily_backtest(rows)


def test_backtest_rejects_mixed_symbols() -> None:
    rows = _rows()
    rows[0]["symbol"] = "TCS"
    rows[1]["symbol"] = "INFY"
    with pytest.raises(ValueError, match="exactly one symbol"):
        backtest_service.run_daily_backtest(rows)


def test_backtest_rejects_missing_symbol_when_symbol_contract_is_started() -> None:
    rows = _rows()
    rows[0]["symbol"] = "TCS"
    with pytest.raises(ValueError, match="all rows must provide symbol"):
        backtest_service.run_daily_backtest(rows)


def test_backtest_rejects_malformed_ohlc() -> None:
    rows = _rows()
    rows[5]["low"] = 105.0
    with pytest.raises(ValueError, match="low above high"):
        backtest_service.run_daily_backtest(rows)


def test_backtest_integrates_explicit_fee_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _rows()
    monkeypatch.setattr(
        backtest_service,
        "generate_regime_momentum_signal",
        lambda *args, **kwargs: Signal(
            action="BUY",
            score=100.0,
            entry=100.0,
            stop=95.0,
            target=110.0,
            reason=("TEST_SIGNAL",),
        ),
    )
    schedule = IndiaEquityIntradayFeeSchedule(
        version="TEST_FEE_V1",
        effective_from="2026-01-01",
        brokerage_rate=0.001,
        exchange_and_ipft_rate=0.0,
        sebi_turnover_rate=0.0,
        stt_sell_rate=0.0,
        stamp_buy_rate=0.0,
    )
    result = backtest_service.run_daily_backtest(
        rows,
        backtest_service.BacktestConfig(fee_schedule=schedule),
    )
    assert result["trades"] >= 1
    assert result["fee_schedule_version"] == "TEST_FEE_V1"
    assert result["total_fees"] > 0
    assert result["trades_detail"][0]["total_fees"] > 0
