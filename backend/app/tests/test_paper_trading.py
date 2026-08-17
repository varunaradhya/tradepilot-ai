from app.services.indian_costs import IndianEquityCostModel, IndianFnoOptionCostModel
from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine
from app.services.paper_trading_service import paper_summary


def test_paper_trade_hits_stop():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, max_daily_loss=.02, allocation_pct=.20, lot_size=1))
    e.new_session('2026-01-02')
    assert e.enter(100, 98, 104)
    trade = e.on_bar('2026-01-02', 101, 97, 99)
    assert trade['reason'] == 'STOP'
    assert trade['exit_reason'] == 'STOP_LOSS'
    assert trade['net_pnl'] < 0
    assert trade['total_charges'] > 0


def test_daily_loss_halts_engine():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, max_daily_loss=.01, allocation_pct=.20, lot_size=1))
    e.new_session('2026-01-02')
    assert e.enter(100, 90, 120)
    e.on_bar('2026-01-02', 101, 89, 90)
    assert e.halted


def test_lot_size_and_allocation_reject_partial_lot():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, allocation_pct=.02, lot_size=65))
    e.new_session('2026-01-02')
    # One NIFTY option lot at ₹141.45 costs more than the ₹2,000 allocation.
    assert not e.enter(141.45, 138.0, 150.0)
    assert e.position is None


def test_lot_size_is_always_a_multiple():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.05, allocation_pct=.20, lot_size=65))
    e.new_session('2026-01-02')
    assert e.enter(100, 95, 120)
    assert e.position['quantity'] % 65 == 0
    assert e.position['lots'] >= 1


def test_target_is_primary_and_timeout_is_fallback():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1, max_holding_bars=3, trailing_activation_pct=.50))
    e.new_session('2026-01-02')
    assert e.enter(100, 95, 110)
    assert e.on_bar('2026-01-02', 105, 99, 104) is None
    trade = e.on_bar('2026-01-02', 111, 103, 109)
    assert trade['reason'] == 'TARGET'


def test_trailing_stop_moves_up_after_activation():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1, trailing_stop_pct=.10, trailing_activation_pct=.01))
    e.new_session('2026-01-02')
    assert e.enter(100, 95, 150)
    assert e.on_bar('2026-01-02', 115, 105, 110) is None
    assert e.position['trailing_stop'] == 103.5
    trade = e.on_bar('2026-01-02', 110, 103, 105)
    assert trade['reason'] == 'TRAILING_STOP'


def test_timeout_only_closes_after_other_exits_are_not_hit():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1, max_holding_bars=2, trailing_activation_pct=.50))
    e.new_session('2026-01-02')
    assert e.enter(100, 90, 130)
    assert e.on_bar('2026-01-02', 104, 98, 102) is None
    trade = e.on_bar('2026-01-02', 105, 99, 103)
    assert trade['reason'] == 'TIMEOUT'


def test_live_snapshot_reports_net_unrealized_pnl():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1))
    e.new_session('2026-01-02')
    assert e.enter(100, 95, 130)
    e.on_bar('2026-01-02', 103, 101, 102)
    snapshot = e.snapshot()
    assert snapshot['unrealized_net_pnl'] != 0
    assert snapshot['total_pnl'] == snapshot['unrealized_net_pnl']


def test_equity_is_the_safe_default_cost_model_for_generic_paper_engine():
    e = PaperTradingEngine(PaperRiskConfig())
    assert isinstance(e.cost_model, IndianEquityCostModel)
    assert not isinstance(e.cost_model, IndianFnoOptionCostModel)


def test_fno_cost_model_can_be_explicitly_selected():
    e = PaperTradingEngine(PaperRiskConfig(cost_model=IndianFnoOptionCostModel()))
    assert isinstance(e.cost_model, IndianFnoOptionCostModel)


def test_fno_cost_model_has_brokerage_and_statutory_components():
    model = IndianFnoOptionCostModel()
    costs = model.estimate_round_trip(10000, 11000)
    assert costs['brokerage'] == 40.0
    assert costs['stt'] > 0
    assert costs['gst'] > 0
    assert costs['total'] > costs['brokerage']


def test_paper_summary_separates_open_and_realized_pnl():
    class Trade:
        status = "CLOSED"; pnl = 150.0
    class OpenTrade:
        status = "OPEN"; pnl = 25.0
    result = paper_summary([Trade(), OpenTrade()])
    assert result["trades"] == 2
    assert result["closed_trades"] == 1
    assert result["open_trades"] == 1
    assert result["realized_pnl"] == 150.0
    assert result["pnl"] == 175.0
