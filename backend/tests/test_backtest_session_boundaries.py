from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services import backtest_service
from app.services.algo_strategy import Signal


def _rows(count: int, start: datetime, close: float = 100.0) -> list[dict]:
    rows = []
    for index in range(count):
        timestamp = start + timedelta(minutes=5 * index)
        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
            }
        )
    return rows


def _buy_signal() -> Signal:
    return Signal(
        action="BUY",
        score=100.0,
        entry=100.0,
        stop=95.0,
        target=110.0,
        reason=("TEST_SIGNAL",),
    )


def test_pending_signal_cannot_cross_nse_session_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _rows(61, datetime(2026, 9, 1, 9, 15))
    rows.append(
        {
            "timestamp": datetime(2026, 9, 2, 9, 15).isoformat(),
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.0,
        }
    )
    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", lambda *args, **kwargs: _buy_signal())

    result = backtest_service.run_daily_backtest(rows)

    assert result["trades"] == 0


def test_intraday_position_is_flattened_at_session_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _rows(62, datetime(2026, 9, 1, 9, 15))
    rows.append(
        {
            "timestamp": datetime(2026, 9, 2, 9, 15).isoformat(),
            "open": 102.0,
            "high": 102.5,
            "low": 101.5,
            "close": 102.0,
        }
    )
    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", lambda *args, **kwargs: _buy_signal())

    result = backtest_service.run_daily_backtest(rows)

    assert result["session_policy"] == "FLAT_AT_SESSION_END"
    assert result["trades"] == 1
    assert result["trades_detail"][0]["reason"] == "SESSION_END"


def test_overnight_mode_is_explicit_opt_out(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _rows(62, datetime(2026, 9, 1, 9, 15))
    rows.append(
        {
            "timestamp": datetime(2026, 9, 2, 9, 15).isoformat(),
            "open": 102.0,
            "high": 102.5,
            "low": 101.5,
            "close": 102.0,
        }
    )
    monkeypatch.setattr(backtest_service, "generate_regime_momentum_signal", lambda *args, **kwargs: _buy_signal())

    result = backtest_service.run_daily_backtest(
        rows,
        backtest_service.BacktestConfig(force_flat_at_session_end=False),
    )

    assert result["session_policy"] == "ALLOW_OVERNIGHT"
    assert result["trades"] == 1
    assert result["trades_detail"][0]["reason"] == "END_OF_TEST"
