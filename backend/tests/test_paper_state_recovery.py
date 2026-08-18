from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def _open_authorized_orchestrator() -> PaperTradingOrchestrator:
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig(allocation_pct=0.50, risk_per_trade=0.01))
    orchestrator.authorize_strategy(fingerprint="a1b2c3d4e5f6")
    result = orchestrator.on_signal(
        "2026-08-18",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0, "symbol": "RELIANCE", "lot_size": 1},
    )
    assert result["accepted"] is True
    return orchestrator


def test_export_restore_preserves_open_position_and_risk_state():
    original = _open_authorized_orchestrator()
    original.on_bar("2026-08-18", high=102.0, low=99.0, close=101.0)
    state = original.export_state()
    restored = PaperTradingOrchestrator(original.config)
    restored.restore_state(state)
    assert restored.summary()["open_position"] == original.summary()["open_position"]
    assert restored.summary()["cash"] == original.summary()["cash"]
    assert restored.summary()["realized_pnl"] == original.summary()["realized_pnl"]
    assert restored.summary()["strategy_fingerprint"] == "a1b2c3d4e5f6"
    assert restored.summary()["session_trades"] == 1


def test_restored_position_still_hits_target_once():
    original = _open_authorized_orchestrator()
    restored = PaperTradingOrchestrator(original.config)
    restored.restore_state(original.export_state())
    result = restored.on_bar("2026-08-18", high=111.0, low=100.0, close=110.5)
    assert result["last_event"] == "EXIT"
    assert result["trade"]["reason"] == "TARGET"
    assert restored.summary()["open_position"] is None
    assert restored.summary()["trades"] == 1


def test_restore_preserves_halted_risk_gate():
    original = _open_authorized_orchestrator()
    original.engine.halted = True
    restored = PaperTradingOrchestrator(original.config)
    restored.restore_state(original.export_state())
    assert restored.summary()["halted"] is True
    result = restored.on_signal("2026-08-18", {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0})
    assert result["accepted"] is False
    assert result["reason"] == "RISK_GATE_BLOCKED"
