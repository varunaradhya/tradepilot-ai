from app.services.paper_pnl import calculate_mark_to_market, calculate_trade_net_pnl


def test_closed_trade_net_pnl_is_gross_less_total_costs():
    result = calculate_trade_net_pnl(100.0, 110.0, 10, {"total": 1.25}, {"total": 1.75})
    assert result == {"gross_pnl": 100.0, "total_charges": 3.0, "net_pnl": 97.0}


def test_unrealized_net_pnl_includes_entry_and_projected_exit_costs():
    result = calculate_mark_to_market(100.0, 105.0, 10, {"total": 1.25}, {"total": 1.75})
    assert result == {"unrealized_gross_pnl": 50.0, "projected_exit_charges": 1.75, "unrealized_net_pnl": 47.0}
