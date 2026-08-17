from datetime import date, datetime

from app.services.broker_adapters import CanonicalOrder
from app.services.execution_guard import ExecutionContext, authorize_order
from app.services.market_execution_guard import MarketExecutionContext, is_cash_market_open


def _paper_context(**kwargs):
    return ExecutionContext(
        "Dhan",
        strategy_ready=True,
        risk_approved=True,
        idempotency_key=kwargs.pop("idempotency_key", "market-guard-1"),
        **kwargs,
    )


def test_market_execution_allows_open_cash_session():
    context = MarketExecutionContext(datetime(2026, 8, 17, 10, 0))
    assert is_cash_market_open(context.observed_at) is True


def test_market_execution_blocks_weekend():
    context = MarketExecutionContext(datetime(2026, 8, 15, 10, 0))
    assert is_cash_market_open(context.observed_at) is False


def test_market_execution_blocks_configured_exchange_holiday():
    holiday = date(2026, 8, 17)
    context = MarketExecutionContext(datetime(2026, 8, 17, 10, 0), holiday_dates=frozenset({holiday}))
    assert is_cash_market_open(context.observed_at, context.holiday_dates) is False


def test_execution_guard_blocks_closed_market_when_context_is_supplied():
    context = MarketExecutionContext(datetime(2026, 8, 17, 8, 59))
    result = authorize_order(
        _paper_context(market_execution=context),
        CanonicalOrder(symbol="RELIANCE", side="BUY", quantity=1, price=100.0),
    )
    assert result.allowed is False
    assert result.reason == "MARKET_SESSION_CLOSED"


def test_execution_guard_blocks_price_above_upper_band():
    context = MarketExecutionContext(
        datetime(2026, 8, 17, 10, 0),
        upper_price_band=105.0,
    )
    result = authorize_order(
        _paper_context(market_execution=context, idempotency_key="band-upper"),
        CanonicalOrder(symbol="RELIANCE", side="BUY", quantity=1, price=105.01),
    )
    assert result.allowed is False
    assert result.reason == "ABOVE_PRICE_BAND"


def test_execution_guard_blocks_price_below_lower_band():
    context = MarketExecutionContext(
        datetime(2026, 8, 17, 10, 0),
        lower_price_band=95.0,
    )
    result = authorize_order(
        _paper_context(market_execution=context, idempotency_key="band-lower"),
        CanonicalOrder(symbol="RELIANCE", side="BUY", quantity=1, price=94.99),
    )
    assert result.allowed is False
    assert result.reason == "BELOW_PRICE_BAND"


def test_execution_guard_allows_price_inside_band():
    context = MarketExecutionContext(
        datetime(2026, 8, 17, 10, 0),
        lower_price_band=95.0,
        upper_price_band=105.0,
    )
    result = authorize_order(
        _paper_context(market_execution=context, idempotency_key="band-ok"),
        CanonicalOrder(symbol="RELIANCE", side="BUY", quantity=1, price=100.0),
    )
    assert result.allowed is True


def test_execution_guard_rejects_invalid_execution_price():
    context = MarketExecutionContext(datetime(2026, 8, 17, 10, 0))
    result = authorize_order(
        _paper_context(market_execution=context, idempotency_key="invalid-price"),
        CanonicalOrder(symbol="RELIANCE", side="BUY", quantity=1, price=0.0),
    )
    assert result.allowed is False
    assert result.reason == "INVALID_EXECUTION_PRICE"
