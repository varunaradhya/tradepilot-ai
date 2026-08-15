from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def signal(entry=100.0, stop=98.0, target=104.0):
    return {"action": "BUY", "entry": entry, "stop": stop, "target": target}


def test_orchestrator_opens_only_long_buy_signals():
    engine = PaperTradingOrchestrator()
    rejected = engine.on_signal("2026-01-02", {"action": "SELL"})
    assert rejected["accepted"] is False
    opened = engine.on_signal("2026-01-02", signal())
    assert opened["accepted"] is True
    assert opened["mode"] == "SIMULATION_ONLY"
    assert opened["trade_direction"] == "LONG_ONLY"


def test_orchestrator_rejects_invalid_risk_levels():
    engine = PaperTradingOrchestrator()
    result = engine.on_signal("2026-01-02", signal(entry=100, stop=101, target=104))
    assert result["accepted"] is False
    assert result["reason"] == "INVALID_RISK_LEVELS"


def test_orchestrator_enforces_session_trade_limit():
    engine = PaperTradingOrchestrator(PaperOrchestratorConfig(max_trades_per_session=1))
    assert engine.on_signal("2026-01-02", signal())["accepted"] is True
    engine.on_bar("2026-01-02", high=101, low=99, close=100)
    result = engine.on_signal("2026-01-02", signal())["accepted"]
    assert result is False
