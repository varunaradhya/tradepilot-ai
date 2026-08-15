from dataclasses import dataclass
from typing import Protocol

from app.services.broker_capabilities import get_broker_capabilities, normalize_broker_name


@dataclass(frozen=True)
class CanonicalOrder:
    symbol: str
    side: str
    quantity: int
    order_type: str = "MARKET"
    product: str = "INTRADAY"
    price: float | None = None
    stop_loss: float | None = None
    target: float | None = None


class BrokerAdapter(Protocol):
    name: str

    def capabilities(self): ...

    def place_order(self, order: CanonicalOrder): ...


class BaseBrokerAdapter:
    name = "UNKNOWN"

    def capabilities(self):
        return get_broker_capabilities(self.name)

    def place_order(self, order: CanonicalOrder):
        raise RuntimeError("LIVE_ORDER_EXECUTION_DISABLED")


class DhanBrokerAdapter(BaseBrokerAdapter):
    name = "DHAN"


class GrowwBrokerAdapter(BaseBrokerAdapter):
    name = "GROWW"


class AngelOneBrokerAdapter(BaseBrokerAdapter):
    name = "ANGELONE"


_ADAPTERS = {
    "DHAN": DhanBrokerAdapter,
    "GROWW": GrowwBrokerAdapter,
    "ANGELONE": AngelOneBrokerAdapter,
}


def get_broker_adapter(name: str) -> BaseBrokerAdapter:
    key = normalize_broker_name(name)
    adapter = _ADAPTERS.get(key)
    if adapter is None:
        raise ValueError(f"Unsupported broker: {name}")
    return adapter()
