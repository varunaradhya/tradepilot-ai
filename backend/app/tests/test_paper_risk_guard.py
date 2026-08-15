from datetime import date

from app.services.paper_risk_guard import (
    PaperRiskConfig,
    PaperRiskState,
    evaluate_paper_entry,
    open_position,
    record_accepted_signal,
    record_closed_trade,
)


def make_state(**kwargs):
    return PaperRiskState(trading_date=date(2026, 8, 15), **kwargs)


def test_long_first_entry_is_approved():
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=True,
        state=make_state(), config=PaperRiskConfig()
    )
    assert result == type(result)(True, "APPROVED")


def test_short_entry_is_blocked_by_long_only_policy():
    result = evaluate_paper_entry(
        side="SELL", symbol="TCS", signal_id="s1", in_market_session=True,
        state=make_state(), config=PaperRiskConfig()
    )
    assert result.reason == "LONG_ONLY"


def test_signal_is_idempotent():
    state = make_state(accepted_signal_ids={"s1"})
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=True,
        state=state, config=PaperRiskConfig()
    )
    assert result.reason == "DUPLICATE_SIGNAL"


def test_daily_loss_limit_blocks_new_entries():
    state = make_state(realized_pnl=-1000)
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=True,
        state=state, config=PaperRiskConfig(max_daily_loss=1000)
    )
    assert result.reason == "DAILY_LOSS_LIMIT"


def test_daily_trade_limit_blocks_new_entries():
    state = make_state(trades_today=5)
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=True,
        state=state, config=PaperRiskConfig(max_daily_trades=5)
    )
    assert result.reason == "DAILY_TRADE_LIMIT"


def test_loss_streak_limit_blocks_new_entries():
    state = make_state(consecutive_losses=3)
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=True,
        state=state, config=PaperRiskConfig(max_consecutive_losses=3)
    )
    assert result.reason == "LOSS_STREAK_LIMIT"


def test_open_position_limits_are_enforced():
    state = make_state(open_symbols={"INFY"})
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=True,
        state=state, config=PaperRiskConfig(max_open_positions=1)
    )
    assert result.reason == "OPEN_POSITION_LIMIT"


def test_same_symbol_cannot_be_reentered_while_open():
    state = make_state(open_symbols={"TCS"})
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s2", in_market_session=True,
        state=state, config=PaperRiskConfig(max_open_positions=2)
    )
    assert result.reason == "POSITION_ALREADY_OPEN"


def test_market_session_gate_is_fail_closed():
    result = evaluate_paper_entry(
        side="BUY", symbol="TCS", signal_id="s1", in_market_session=False,
        state=make_state(), config=PaperRiskConfig()
    )
    assert result.reason == "OUTSIDE_MARKET_SESSION"


def test_trade_lifecycle_updates_risk_state():
    state = make_state()
    open_position(state, "TCS")
    record_accepted_signal(state, "s1")
    record_closed_trade(state, -100, "TCS")
    record_closed_trade(state, 150, "TCS")
    assert state.realized_pnl == 50
    assert state.trades_today == 2
    assert state.consecutive_losses == 0
    assert state.open_symbols == set()
