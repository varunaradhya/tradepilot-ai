from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def test_long_signal_opens_virtual_position():
    engine = PaperTradingOrchestrator(PaperOrchestratorConfig(initial_capital=100000, max_trades_per_session=3))
    result = engine.on_signal("2026-08-15", {"action": "BUY", "entry": 100, "stop": 98, "target": 104})
    assert result["accepted"] is True
    assert result["open_position"]["direction"] == "LONG"


def test_non_buy_signal_is_rejected_without_position():
    engine = PaperTradingOrchestrator()
    result = engine.on_signal("2026-08-15", {"action": "SELL", "entry": 100, "stop": 102, "target": 96})
    assert result["accepted"] is False
    assert result["reason"] == "SIGNAL_NOT_BUY"
    assert result["open_position"] is None


def test_max_trades_gate_blocks_additional_entries_after_session_limit():
    engine = PaperTradingOrchestrator(PaperOrchestratorConfig(max_trades_per_session=1))
    first = engine.on_signal("2026-08-15", {"action": "BUY", "entry": 100, "stop": 98, "target": 104})
    assert first["accepted"] is True
    engine.on_bar("2026-08-15", 104, 99, 104)
    second = engine.on_signal("2026-08-15", {"action": "BUY", "entry": 100, "stop": 98, "target": 104})
    assert second["accepted"] is False
    assert second["reason"] == "MAX_TRADES_REACHED"


def test_bar_closes_position_at_stop_before_target():
    engine = PaperTradingOrchestrator()
    engine.on_signal("2026-08-15", {"action": "BUY", "entry": 100, "stop": 98, "target": 104})
    result = engine.on_bar("2026-08-15", 105, 97, 101)
    assert result["last_event"] == "EXIT"
    assert result["realized_pnl"] < 0
