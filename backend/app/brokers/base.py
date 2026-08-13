from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class BrokerHolding:
    symbol: str
    quantity: Decimal
    average_price: Decimal


@dataclass
class BrokerTransaction:
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    transaction_id: str | None = None


class BrokerAdapter(ABC):
    """Common interface implemented by all broker integrations."""

    name: str = "unknown"

    @abstractmethod
    def get_profile(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_holdings(self) -> list[BrokerHolding]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_orders(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_trades(self) -> list[BrokerTransaction]:
        raise NotImplementedError