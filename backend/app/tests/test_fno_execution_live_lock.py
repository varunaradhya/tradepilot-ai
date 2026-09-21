import importlib

from app.core import config
from app.services.fno_execution import execute_fno_decision


def test_live_execution_cannot_be_enabled_by_environment(monkeypatch):
    monkeypatch.setenv("TRADEPILOT_LIVE_EXECUTION_ENABLED", "true")
    importlib.reload(config)
    assert config.TRADEPILOT_LIVE_EXECUTION_ENABLED is False


def test_fno_execution_remains_paper_only():
    class NeverCalledClient:
        client_id = "dummy"

        def place_order(self, payload):
            raise AssertionError("real order path must remain unreachable")

    decision = {
        "decision": "QUALIFIED",
        "contract": {"security_id": "123"},
        "quantity": 75,
        "lot_size": 75,
        "entry": 100,
        "stop": 90,
        "target": 120,
    }
    result = execute_fno_decision(NeverCalledClient(), decision, "qa-lock")
    assert result["mode"] == "PAPER_ONLY"
    assert result["submitted"] is False
