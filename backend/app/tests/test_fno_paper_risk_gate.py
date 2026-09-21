from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.api.v1 import fno


IST = ZoneInfo("Asia/Kolkata")


class FakeQuery:
    def __init__(self, trades):
        self.trades = trades

    def filter(self, *args):
        return self

    def all(self):
        return list(self.trades)


class FakeDB:
    def __init__(self, trades):
        self.trades = trades

    def query(self, model):
        return FakeQuery(self.trades)


def _trade(status, pnl, closed_at=None, underlying="NIFTY"):
    return SimpleNamespace(
        status=status,
        pnl=pnl,
        closed_at=closed_at,
        underlying=underlying,
        symbol=underlying,
    )


def test_fno_risk_gate_blocks_after_daily_loss(monkeypatch):
    monkeypatch.setattr(fno, "scheduler_status", lambda: {"session_active": True})
    today = datetime.now(IST)
    trades = [
        _trade("CLOSED", -1100.0, today),
    ]
    reason = fno._fno_paper_risk_gate(FakeDB(trades), 1, "NIFTY", "signal-001")
    assert reason == "DAILY_LOSS_LIMIT"


def test_fno_risk_gate_blocks_when_position_is_already_open(monkeypatch):
    monkeypatch.setattr(fno, "scheduler_status", lambda: {"session_active": True})
    reason = fno._fno_paper_risk_gate(
        FakeDB([_trade("OPEN", 0.0)]), 1, "NIFTY", "signal-002"
    )
    assert reason == "POSITION_ALREADY_OPEN"


def test_fno_risk_gate_allows_clean_session(monkeypatch):
    monkeypatch.setattr(fno, "scheduler_status", lambda: {"session_active": True})
    reason = fno._fno_paper_risk_gate(FakeDB([]), 1, "NIFTY", "signal-003")
    assert reason is None

def test_fno_kill_switch_gate_blocks_when_active(monkeypatch):
    monkeypatch.setattr(fno, "kill_switch_status", lambda db: {"active": True, "reason": "MANUAL_HALT"})
    assert fno._fno_kill_switch_gate(object()) == "KILL_SWITCH_ACTIVE:MANUAL_HALT"


def test_fno_kill_switch_gate_allows_when_inactive(monkeypatch):
    monkeypatch.setattr(fno, "kill_switch_status", lambda db: {"active": False, "reason": "CLEARED"})
    assert fno._fno_kill_switch_gate(object()) is None


def test_fno_risk_gate_ignores_future_closed_trade_for_daily_loss(monkeypatch):
    monkeypatch.setattr(fno, "scheduler_status", lambda: {"session_active": True})
    from datetime import timedelta
    future = datetime.now(IST) + timedelta(days=1)
    reason = fno._fno_paper_risk_gate(FakeDB([_trade("CLOSED", -5000.0, future)]), 1, "NIFTY", "signal-future")
    assert reason is None
