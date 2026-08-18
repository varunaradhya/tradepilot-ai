from app.services.indian_costs import IndianEquityCostModel, IndianFnoOptionCostModel
from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine
from app.services.paper_trading_service import paper_summary


def test_paper_trade_hits_stop():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, max_daily_loss=.02, allocation_pct=.20, lot_size=1))
    e.new_session('2026-01-02'); assert e.enter(100, 98, 104)
    trade = e.on_bar('2026-01-02', 101, 97, 99)
    assert trade['reason'] == 'STOP'; assert trade['exit_reason'] == 'STOP_LOSS'; assert trade['net_pnl'] < 0; assert trade['total_charges'] > 0


def test_daily_loss_halts_engine():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, max_daily_loss=.01, allocation_pct=.20, lot_size=1))
    e.new_session('2026-01-02'); assert e.enter(100, 90, 120); e.on_bar('2026-01-02', 101, 89, 90); assert e.halted


def test_daily_risk_baseline_resets_to_realized_session_equity():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, max_daily_loss=.01, allocation_pct=.20, lot_size=1)); e.new_session('2026-01-02'); assert e.enter(100, 90, 120)
    trade = e.on_bar('2026-01-02', 121, 100, 120); assert trade['reason'] == 'TARGET'; profitable_equity = e.cash; assert profitable_equity > 100000
    e.new_session('2026-01-05'); assert e.day_start_equity == profitable_equity; assert e.day_pnl == 0.0; assert e.halted is False


def test_lot_size_and_allocation_reject_partial_lot():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.01, allocation_pct=.02, lot_size=65)); e.new_session('2026-01-02'); assert not e.enter(141.45, 138.0, 150.0); assert e.position is None


def test_lot_size_is_always_a_multiple():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, risk_per_trade=.05, allocation_pct=.20, lot_size=65)); e.new_session('2026-01-02'); assert e.enter(100, 95, 120); assert e.position['quantity'] % 65 == 0; assert e.position['lots'] >= 1


def test_target_is_primary_and_timeout_is_fallback():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1, max_holding_bars=3, trailing_activation_pct=.50)); e.new_session('2026-01-02'); assert e.enter(100, 95, 110); assert e.on_bar('2026-01-02', 105, 99, 104) is None
    trade = e.on_bar('2026-01-02', 111, 103, 109); assert trade['reason'] == 'TARGET'


def test_trailing_stop_moves_up_after_activation():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1, trailing_stop_pct=.10, trailing_activation_pct=.01)); e.new_session('2026-01-02'); assert e.enter(100, 95, 150); assert e.on_bar('2026-01-02', 115, 105, 110) is None; assert e.position['trailing_stop'] == 103.5
    trade = e.on_bar('2026-01-02', 110, 103, 105); assert trade['reason'] == 'TRAILING_STOP'


def test_timeout_only_closes_after_other_exits_are_not_hit():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1, max_holding_bars=2, trailing_activation_pct=.50)); e.new_session('2026-01-02'); assert e.enter(100, 90, 130); assert e.on_bar('2026-01-02', 104, 98, 102) is None
    trade = e.on_bar('2026-01-02', 105, 99, 103); assert trade['reason'] == 'TIMEOUT'


def test_live_snapshot_reports_net_unrealized_pnl():
    e = PaperTradingEngine(PaperRiskConfig(initial_capital=100000, allocation_pct=.20, lot_size=1)); e.new_session('2026-01-02'); assert e.enter(100, 95, 130); e.on_bar('2026-01-02', 103, 101, 102); snapshot = e.snapshot()
    assert snapshot['unrealized_net_pnl'] != 0; assert snapshot['total_pnl'] == snapshot['unrealized_net_pnl']


def test_equity_is_the_safe_default_cost_model_for_generic_paper_engine():
    e = PaperTradingEngine(PaperRiskConfig()); assert isinstance(e.cost_model, IndianEquityCostModel); assert not isinstance(e.cost_model, IndianFnoOptionCostModel)


def test_fno_cost_model_can_be_explicitly_selected():
    e = PaperTradingEngine(PaperRiskConfig(cost_model=IndianFnoOptionCostModel())); assert isinstance(e.cost_model, IndianFnoOptionCostModel)


def test_fno_cost_model_has_brokerage_and_statutory_components():
    model = IndianFnoOptionCostModel(); costs = model.estimate_round_trip(10000, 11000); assert costs['brokerage'] == 40.0; assert costs['stt'] > 0; assert costs['gst'] > 0; assert costs['total'] > costs['brokerage']


def test_paper_summary_separates_open_and_realized_pnl():
    class Trade: status = "CLOSED"; pnl = 150.0
    class OpenTrade: status = "OPEN"; pnl = 25.0
    result = paper_summary([Trade(), OpenTrade()]); assert result["trades"] == 2; assert result["closed_trades"] == 1; assert result["open_trades"] == 1; assert result["realized_pnl"] == 150.0; assert result["pnl"] == 175.0


def test_risk_config_rejects_non_finite_or_invalid_capital_and_risk():
    import math
    for config in (PaperRiskConfig(initial_capital=0), PaperRiskConfig(initial_capital=math.inf), PaperRiskConfig(risk_per_trade=0), PaperRiskConfig(risk_per_trade=1.1), PaperRiskConfig(risk_per_trade=math.nan)):
        try: PaperTradingEngine(config); assert False
        except ValueError: pass


def test_engine_rejects_non_finite_trade_levels_without_mutating_position():
    import math
    e = PaperTradingEngine(); e.new_session('2026-01-02')
    for levels in ((math.nan, 98, 104), (100, math.inf, 104), (100, 98, math.nan)):
        try: e.enter(*levels); assert False
        except ValueError: pass
    assert e.position is None


def test_engine_rejects_invalid_tick_values():
    import math
    e = PaperTradingEngine(); e.new_session('2026-01-02')
    for price in (0, -1, math.inf, math.nan):
        try: e.on_tick('2026-01-02', price); assert False
        except ValueError: pass


def test_engine_rejects_invalid_bars_even_without_an_open_position():
    e = PaperTradingEngine(); invalid_bars = ((10, 9, 11), (10, 11, 10), (10, 9, 0), (10, 9, -1))
    for high, low, close in invalid_bars:
        try: e.on_bar('2026-01-02', high, low, close); assert False
        except ValueError: pass


def test_engine_rejects_invalid_bar_after_position_without_incrementing_bars():
    e = PaperTradingEngine(PaperRiskConfig(allocation_pct=.20)); e.new_session('2026-01-02'); assert e.enter(100, 95, 130); before = e.position['bars_held']
    try: e.on_bar('2026-01-02', 105, 99, 108); assert False
    except ValueError: pass
    assert e.position['bars_held'] == before


def test_session_requires_a_non_empty_identifier():
    e = PaperTradingEngine()
    for session in ('', '   ', None):
        try: e.new_session(session); assert False
        except (ValueError, TypeError): pass


def test_session_cannot_move_backwards_and_close_current_position():
    e = PaperTradingEngine(PaperRiskConfig(allocation_pct=.20)); e.new_session('2026-01-02'); assert e.enter(100, 95, 130)
    try: e.on_bar('2026-01-01', 105, 99, 102); assert False
    except ValueError: pass
    assert e.day == '2026-01-02'; assert e.position is not None; assert e.position['bars_held'] == 0
