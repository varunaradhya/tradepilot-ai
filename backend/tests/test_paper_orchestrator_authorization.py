from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def test_paper_signal_fails_closed_before_strategy_authorization():
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig())
    result = orchestrator.on_signal(
        "2026-08-18",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0, "symbol": "RELIANCE"},
    )
    assert result["accepted"] is False
    assert result["reason"] == "STRATEGY_NOT_QUALIFIED"
    assert result["open_position"] is None


def test_paper_signal_can_only_open_after_server_authorization():
    orchestrator = PaperTradingOrchestrator(
        PaperOrchestratorConfig(allocation_pct=0.50, risk_per_trade=0.01)
    )
    orchestrator.authorize_strategy(fingerprint="a1b2c3d4e5f6")
    result = orchestrator.on_signal(
        "2026-08-18",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0, "symbol": "RELIANCE"},
    )
    assert result["accepted"] is True
    assert result["strategy_fingerprint"] == "a1b2c3d4e5f6"
    assert result["open_position"] is not None


def test_revoke_strategy_closes_future_entry_path():
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig(allocation_pct=0.50))
    orchestrator.authorize_strategy(fingerprint="a1b2c3d4e5f6")
    orchestrator.revoke_strategy()
    result = orchestrator.on_signal(
        "2026-08-18",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0},
    )
    assert result["accepted"] is False
    assert result["reason"] == "STRATEGY_NOT_QUALIFIED"
