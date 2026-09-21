from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.api.v1.fno import _fno_session_data_gate


IST = ZoneInfo("Asia/Kolkata")


def _bar_at(hour: int, minute: int, second: int = 0) -> dict:
    dt = datetime(2026, 9, 21, hour, minute, second, tzinfo=IST)
    return {"timestamp": dt.timestamp()}


def test_fno_gate_rejects_inactive_market_session(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.fno.scheduler_status",
        lambda: {
            "session_active": False,
            "timezone": "Asia/Kolkata",
            "market": "NSE_EQ",
            "mode": "SIMULATION_ONLY",
            "broker_orders_enabled": False,
        },
    )
    result = _fno_session_data_gate([_bar_at(15, 25)], "5")
    assert result["ready"] is False
    assert result["reason"] == "MARKET_SESSION_INACTIVE"


def test_fno_gate_rejects_missing_completed_bars(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.fno.scheduler_status",
        lambda: {"session_active": True},
    )
    result = _fno_session_data_gate([], "5")
    assert result["ready"] is False
    assert result["reason"] == "NO_COMPLETED_BARS"


def test_fno_gate_accepts_fresh_completed_bar(monkeypatch):
    now = datetime(2026, 9, 21, 10, 0, tzinfo=IST)
    monkeypatch.setattr(
        "app.api.v1.fno.scheduler_status",
        lambda: {"session_active": True},
    )
    monkeypatch.setattr("app.api.v1.fno.datetime", __import__("datetime").datetime)
    result = _fno_session_data_gate([{"timestamp": datetime(2026, 9, 21, 9, 55, tzinfo=IST).timestamp()}], "5")
    assert result["ready"] is True
    assert result["reason"] == "FRESH"


def test_fno_gate_rejects_future_completed_bar(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.fno.scheduler_status",
        lambda: {"session_active": True},
    )
    future = datetime.now(ZoneInfo("UTC")).timestamp() + 600
    result = _fno_session_data_gate([{"timestamp": future}], "5")
    assert result["ready"] is False
    assert result["reason"] == "FUTURE_TIMESTAMP_REJECTED"


def test_fno_gate_uses_interval_aware_freshness_window(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.fno.scheduler_status",
        lambda: {"session_active": True},
    )
    recent = datetime.now(ZoneInfo("UTC")).timestamp() - 330
    result = _fno_session_data_gate([{"timestamp": recent}], "5")
    assert result["ready"] is True
