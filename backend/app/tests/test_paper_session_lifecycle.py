from app.services.paper_market_service import PaperMarketCoordinator
from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine
from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def test_engine_rejects_target_at_or_below_entry():
    engine = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=0.01))
    engine.new_session("2026-01-02")
    assert engine.enter(100, 98, 100) is False
    assert engine.enter(100, 98, 99) is False


def test_closed_trade_preserves_stop_and_target():
    engine = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=0.01))
    engine.new_session("2026-01-02")
    assert engine.enter(100, 98, 104)
    trade = engine.on_bar("2026-01-02", 101, 97, 99)
    assert trade["reason"] == "STOP"
    assert trade["stop"] == 98
    assert trade["target"] == 104


def test_market_coordinator_routes_existing_position_to_bar_exit():
    coordinator = PaperMarketCoordinator()
    opened = coordinator.orchestrator.on_signal(
        "2026-01-02",
        {"action": "BUY", "entry": 100, "stop": 98, "target": 104, "symbol": "TCS"},
    )
    assert opened["accepted"] is True
    result = coordinator.on_bar("2026-01-02", "TCS", 99, 101, 97, 99, 1000)
    assert result["execution"]["last_event"] == "EXIT"
    assert result["execution"]["trade"]["reason"] == "STOP"


def test_orchestrator_close_session_forces_end_of_day_exit():
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig())
    opened = orchestrator.on_signal(
        "2026-01-02",
        {"action": "BUY", "entry": 100, "stop": 98, "target": 104, "symbol": "TCS"},
    )
    assert opened["accepted"] is True
    result = orchestrator.close_session("2026-01-02", 101)
    assert result["trade"]["reason"] == "SESSION_CLOSE"
    assert result["open_position"] is None
