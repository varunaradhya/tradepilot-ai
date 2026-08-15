from datetime import date

from app.services.paper_risk_guard import PaperRiskState
from app.services.position_risk import PositionRiskConfig
from app.services.trade_decision_service import build_paper_trade_decision


def _series():
    closes = [100 + i * 0.35 for i in range(30)]
    highs = [x + 0.5 for x in closes]
    lows = [x - 0.5 for x in closes]
    volumes = [1000.0] * 29 + [1500.0]
    return closes, highs, lows, volumes


def _kwargs(**extra):
    closes, highs, lows, volumes = _series()
    base = dict(
        symbol="TCS", session="2026-08-15", closes=closes, highs=highs, lows=lows,
        volumes=volumes, equity=100000, broker="Dhan", opening_high=108,
    )
    base.update(extra)
    return base


def test_complete_signal_risk_execution_decision_is_paper_ready():
    result = build_paper_trade_decision(**_kwargs())
    assert result.action == "BUY"
    assert result.status == "PAPER_READY"
    assert result.reason == "PAPER_ORDER_AUTHORIZED"
    assert result.quantity > 0
    assert result.max_loss > 0
    assert result.risk_reward == 2.0


def test_neutral_signal_stops_before_risk_engine():
    result = build_paper_trade_decision(**_kwargs(opening_high=1000))
    assert result.status == "NO_TRADE"
    assert result.reason == "SIGNAL_NOT_BUY"
    assert result.quantity == 0


def test_strategy_readiness_blocks_before_execution():
    result = build_paper_trade_decision(**_kwargs(strategy_ready=False))
    assert result.status == "BLOCKED"
    assert result.reason == "STRATEGY_NOT_READY"


def test_market_data_health_blocks_at_execution_gate():
    result = build_paper_trade_decision(**_kwargs(market_data_healthy=False))
    assert result.status == "BLOCKED"
    assert result.reason == "MARKET_DATA_UNSAFE"


def test_risk_approval_blocks_at_execution_gate():
    result = build_paper_trade_decision(**_kwargs(risk_approved=False))
    assert result.status == "BLOCKED"
    assert result.reason == "RISK_NOT_APPROVED"


def test_paper_session_blocks_duplicate_signal():
    closes, highs, lows, volumes = _series()
    state = PaperRiskState(trading_date=date(2026, 8, 15))
    first = build_paper_trade_decision(**_kwargs(paper_state=state))
    state.accepted_signal_ids.add(first.signal_id)
    second = build_paper_trade_decision(**_kwargs(paper_state=state))
    assert first.status == "PAPER_READY"
    assert second.reason == "DUPLICATE_SIGNAL"


def test_daily_risk_budget_can_block_position_sizing():
    result = build_paper_trade_decision(
        **_kwargs(daily_risk_used=2000),
    )
    assert result.status == "BLOCKED"
    assert result.reason == "DAILY_RISK_LIMIT"


def test_position_risk_cap_can_reduce_quantity_without_blocking():
    result = build_paper_trade_decision(
        **_kwargs(position_config=PositionRiskConfig(max_quantity=2, max_order_value=100000)),
    )
    assert result.status == "PAPER_READY"
    assert result.quantity == 2


def test_unknown_broker_is_rejected():
    result = build_paper_trade_decision(**_kwargs(broker="UNKNOWN"))
    assert result.status == "BLOCKED"
    assert result.reason == "BROKER_UNSUPPORTED"


def test_paper_decision_never_authorizes_live_mode():
    # The public composer intentionally hard-codes PAPER mode; there is no
    # parameter that can turn this function into a live-order path.
    result = build_paper_trade_decision(**_kwargs())
    assert result.mode == "PAPER"
