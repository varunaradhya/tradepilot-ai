from app.services.intraday_trade_analytics import analyze_intraday_trades


def test_trade_analytics_groups_time_and_exit_reason():
    result = analyze_intraday_trades([
        {"pnl": 100, "entry_time": "2026-01-02T09:35:00", "reason": "TARGET"},
        {"pnl": -50, "entry_time": "2026-01-02T09:40:00", "reason": "STOP"},
        {"pnl": 80, "entry_time": "2026-01-02T09:35:00", "reason": "TARGET"},
    ])
    assert result["trades"] == 3
    assert result["max_consecutive_wins"] == 1
    assert result["max_consecutive_losses"] == 1
    assert result["by_entry_time"]["09:35"]["trades"] == 2
    assert result["by_exit_reason"]["TARGET"]["net_pnl"] == 180


def test_trade_analytics_empty_is_safe():
    result = analyze_intraday_trades([])
    assert result["trades"] == 0
    assert result["max_consecutive_losses"] == 0
    assert result["by_entry_time"] == {}
