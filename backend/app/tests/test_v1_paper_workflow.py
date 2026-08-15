from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def test_v1_paper_workflow_signal_position_exit_is_simulation_only():
    orchestrator = PaperTradingOrchestrator(
        PaperOrchestratorConfig(initial_capital=100_000.0, max_trades_per_session=3)
    )

    opened = orchestrator.on_signal(
        "2026-08-17",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0},
    )
    assert opened["accepted"] is True
    assert opened["reason"] == "PAPER_ORDER_OPENED"
    assert opened["position"] is not None
    assert opened["mode"] == "SIMULATION_ONLY"

    exited = orchestrator.on_bar("2026-08-17", high=111.0, low=99.0, close=110.0)
    assert exited["last_event"] == "EXIT"
    assert exited["trade"]["reason"] == "TARGET"
    assert exited["position"] is None


def test_v1_paper_workflow_rejects_neutral_before_position_creation():
    orchestrator = PaperTradingOrchestrator()
    result = orchestrator.on_signal(
        "2026-08-17",
        {"action": "NEUTRAL", "entry": 100.0, "stop": 95.0, "target": 110.0},
    )
    assert result["accepted"] is False
    assert result["reason"] == "SIGNAL_NOT_BUY"
    assert result["position"] is None


def test_v1_paper_workflow_enforces_long_only_contract():
    orchestrator = PaperTradingOrchestrator(
        PaperOrchestratorConfig(trade_direction="SHORT_ONLY")
    )
    result = orchestrator.on_signal(
        "2026-08-17",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0},
    )
    assert result["accepted"] is False
    assert result["reason"] == "UNSUPPORTED_DIRECTION"


def test_v1_paper_workflow_resets_session_trade_count():
    orchestrator = PaperTradingOrchestrator(
        PaperOrchestratorConfig(max_trades_per_session=1)
    )
    first = orchestrator.on_signal(
        "2026-08-17",
        {"action": "BUY", "entry": 100.0, "stop": 95.0, "target": 110.0},
    )
    assert first["accepted"] is True

    second = orchestrator.on_signal(
        "2026-08-17",
        {"action": "BUY", "entry": 120.0, "stop": 115.0, "target": 130.0},
    )
    assert second["accepted"] is False
    assert second["reason"] == "MAX_TRADES_REACHED"

    next_session = orchestrator.on_signal(
        "2026-08-18",
        {"action": "BUY", "entry": 120.0, "stop": 115.0, "target": 130.0},
    )
    assert next_session["accepted"] is True
