from dataclasses import dataclass

from app.services.broker_adapters import CanonicalOrder, get_broker_adapter
from app.services.broker_capabilities import get_broker_capabilities, normalize_broker_name


@dataclass(frozen=True)
class ExecutionContext:
    broker: str
    mode: str = "PAPER"
    market_data_healthy: bool = True
    strategy_ready: bool = False
    risk_approved: bool = False
    long_only: bool = True


@dataclass(frozen=True)
class ExecutionDecision:
    allowed: bool
    reason: str
    normalized_broker: str
    mode: str


def authorize_order(context: ExecutionContext, order: CanonicalOrder) -> ExecutionDecision:
    """Central safety gate before any broker-order path."""
    broker = normalize_broker_name(context.broker)
    mode = context.mode.strip().upper()
    try:
        adapter = get_broker_adapter(broker)
    except ValueError:
        return ExecutionDecision(False, "BROKER_UNSUPPORTED", broker, mode)
    try:
        adapter.validate_order(order)
    except ValueError as exc:
        return ExecutionDecision(False, str(exc), broker, mode)
    if context.long_only and order.side.strip().upper() != "BUY":
        return ExecutionDecision(False, "LONG_ONLY_POLICY", broker, mode)
    if not context.market_data_healthy:
        return ExecutionDecision(False, "MARKET_DATA_UNSAFE", broker, mode)
    if mode == "LIVE":
        return ExecutionDecision(False, "LIVE_ORDER_EXECUTION_DISABLED", broker, mode)
    if mode != "PAPER":
        return ExecutionDecision(False, "UNSUPPORTED_EXECUTION_MODE", broker, mode)
    if not context.strategy_ready:
        return ExecutionDecision(False, "STRATEGY_NOT_READY", broker, mode)
    if not context.risk_approved:
        return ExecutionDecision(False, "RISK_NOT_APPROVED", broker, mode)
    capabilities = get_broker_capabilities(broker)
    if capabilities.integration_status == "UNSUPPORTED":
        return ExecutionDecision(False, "BROKER_UNSUPPORTED", broker, mode)
    if not capabilities.paper_orders:
        return ExecutionDecision(False, "PAPER_ORDERS_UNSUPPORTED", broker, mode)
    return ExecutionDecision(True, "PAPER_ORDER_AUTHORIZED", broker, mode)
