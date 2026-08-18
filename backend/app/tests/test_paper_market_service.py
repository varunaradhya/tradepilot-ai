import pytest

from app.services.intraday_strategy import IntradayConfig
from app.services.paper_market_service import PaperMarketCoordinator
from app.services.paper_trading_orchestrator import PaperOrchestratorConfig, PaperTradingOrchestrator


def _coordinator() -> PaperMarketCoordinator:
    config = IntradayConfig(
        opening_bars=1,
        fast_period=2,
        slow_period=3,
        volume_period=3,
        min_volume_ratio=1.2,
        max_gap_percent=10,
        atr_period=2,
        atr_stop_multiple=1.0,
        reward_multiple=2.0,
    )
    orchestrator = PaperTradingOrchestrator(PaperOrchestratorConfig(qualification_required=False))
    return PaperMarketCoordinator(orchestrator=orchestrator, strategy=config)


def test_market_bar_builds_history_and_returns_neutral_until_ready():
    coordinator = _coordinator()
    result = coordinator.on_bar("2026-08-15", "TCS", 10, 10.2, 9.8, 10, 100)
    assert result["mode"] == "SIMULATION_ONLY"
    assert result["bars"] == 1
    assert result["signal"]["action"] == "NEUTRAL"


def test_market_bar_routes_breakout_buy_into_paper_engine():
    coordinator = _coordinator()
    closes = [10, 11, 12, 13, 14, 15]
    for index, close in enumerate(closes):
        result = coordinator.on_bar("2026-08-15", "TCS", close - 0.1, close + 0.2, close - 0.2, close, 100 if index < 5 else 200)
    assert result["signal"]["action"] == "BUY"
    assert result["execution"]["accepted"] is True
    assert result["execution"]["reason"] == "PAPER_ORDER_OPENED"


def test_market_bar_rejects_invalid_ohlc():
    coordinator = _coordinator()
    with pytest.raises(ValueError, match="OHLC prices"):
        coordinator.on_bar("2026-08-15", "TCS", 10, 9, 9.5, 9.7, 100)


def test_market_bar_reset_clears_symbol_history():
    coordinator = _coordinator()
    coordinator.on_bar("2026-08-15", "TCS", 10, 10.2, 9.8, 10, 100)
    coordinator.reset()
    result = coordinator.on_bar("2026-08-15", "TCS", 10, 10.2, 9.8, 10, 100)
    assert result["bars"] == 1


def test_market_bar_does_not_exit_position_for_different_symbol():
    coordinator = _coordinator()
    opened = coordinator.orchestrator.on_signal(
        "2026-08-15",
        {"action": "BUY", "symbol": "TCS", "entry": 100, "stop": 98, "target": 104},
    )
    assert opened["accepted"] is True

    other = coordinator.on_bar("2026-08-15", "INFY", 100, 110, 90, 105, 1000)
    assert other["execution"] is None
    assert other["paper"]["open_position"]["symbol"] == "TCS"

    same = coordinator.on_bar("2026-08-15", "TCS", 100, 105, 99, 104, 1000)
    assert same["execution"]["last_event"] == "EXIT"
    assert same["execution"]["trade"]["reason"] == "TARGET"


def test_close_session_does_not_close_different_symbol_position():
    coordinator = _coordinator()
    opened = coordinator.orchestrator.on_signal(
        "2026-08-15",
        {"action": "BUY", "symbol": "TCS", "entry": 100, "stop": 98, "target": 104},
    )
    assert opened["accepted"] is True

    result = coordinator.close_session("2026-08-15", "INFY", 105)
    assert result["trade"] is None
    assert result["open_position"]["symbol"] == "TCS"
