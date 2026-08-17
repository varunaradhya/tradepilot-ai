from dataclasses import dataclass, field
from uuid import uuid4

from app.services.broker_adapters import CanonicalOrder, get_broker_adapter
from app.services.broker_capabilities import get_broker_capabilities, normalize_broker_name


@dataclass
class ExecutionSafetyState:
    """Process-local emergency/idempotency state for paper execution.

    Phase 1 deliberately keeps this dependency-free. A multi-worker live
    deployment must move the state to a durable shared store before live orders
    are ever enabled. Callers should supply an explicit idempotency key; the
    UUID fallback preserves compatibility for older internal paper paths.
    """

    kill_switch_active: bool = False
    accepted_idempotency_keys: set[str] = field(default_factory=set)

    def activate_kill_switch(self) -> None:
        self.kill_switch_active = True

    def deactivate_kill_switch(self) -> None:
        self.kill_switch_active = False

    def authorize_idempotency_key(self, key: str) -> bool:
        normalized = key.strip()
        if not normalized or normalized in self.accepted_idempotency_keys:
            return False
        self.accepted_idempotency_keys.add(normalized)
        return True


_DEFAULT_SAFETY_STATE = ExecutionSafetyState()


@dataclass(frozen=True)
class ExecutionContext:
    broker: str
    mode: str = "PAPER"
    market_data_healthy: bool = True
    strategy_ready: bool = False
    risk_approved: bool = False
    long_only: bool = True
    max_quantity: int | None = None
    max_order_value: float | None = None
    kill_switch_active: bool = False
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ExecutionDecision:
    allowed: bool
    reason: str
    normalized_broker: str
    mode: str


def authorize_order(
    context: ExecutionContext,
    order: CanonicalOrder,
    safety_state: ExecutionSafetyState | None = None,
) -> ExecutionDecision:
    """Central fail-closed safety gate before any broker-order path."""
    broker = normalize_broker_name(context.broker)
    mode = context.mode.strip().upper()
    state = safety_state or _DEFAULT_SAFETY_STATE

    if context.kill_switch_active or state.kill_switch_active:
        return ExecutionDecision(False, "KILL_SWITCH_ACTIVE", broker, mode)

    # Explicit keys are idempotent. Legacy internal callers get a one-shot UUID
    # so adding the safety gate does not silently break existing paper workflows.
    idempotency_key = context.idempotency_key or uuid4().hex
    if not state.authorize_idempotency_key(idempotency_key):
        return ExecutionDecision(False, "DUPLICATE_ORDER_INTENT", broker, mode)

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
    if context.max_quantity is not None and order.quantity > context.max_quantity:
        return ExecutionDecision(False, "QUANTITY_LIMIT_EXCEEDED", broker, mode)
    if context.max_order_value is not None:
        if order.price is None:
            return ExecutionDecision(False, "ORDER_VALUE_UNVERIFIABLE", broker, mode)
        if order.quantity * order.price > context.max_order_value:
            return ExecutionDecision(False, "ORDER_VALUE_LIMIT_EXCEEDED", broker, mode)
    capabilities = get_broker_capabilities(broker)
    if capabilities.integration_status == "UNSUPPORTED":
        return ExecutionDecision(False, "BROKER_UNSUPPORTED", broker, mode)
    if not capabilities.paper_orders:
        return ExecutionDecision(False, "PAPER_ORDERS_UNSUPPORTED", broker, mode)
    return ExecutionDecision(True, "PAPER_ORDER_AUTHORIZED", broker, mode)
