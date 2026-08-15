from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.brokers.base import BrokerAdapter, BrokerHolding, BrokerTransaction
from app.brokers.dhan import DhanClient


class DhanBrokerAdapter(BrokerAdapter):
    """Adapter that maps the existing Dhan client to TradePilot's broker API."""

    name = "dhan"

    def __init__(self, client: DhanClient) -> None:
        self.client = client

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"profile", "holdings", "positions", "orders", "trades", "historical_data"})

    def get_profile(self) -> dict[str, Any]:
        return self.client.profile()

    def get_holdings(self) -> list[BrokerHolding]:
        return [
            BrokerHolding(
                symbol=str(item.get("tradingSymbol") or item.get("symbol") or "").strip().upper(),
                quantity=Decimal(str(item.get("totalQty", 0))),
                average_price=Decimal(str(item.get("avgCostPrice", 0))),
            )
            for item in self.client.holdings()
            if item.get("tradingSymbol") or item.get("symbol")
        ]

    def get_positions(self) -> list[dict[str, Any]]:
        return self.client.positions()

    def get_orders(self) -> list[dict[str, Any]]:
        return self.client.orders()

    def get_trades(self) -> list[BrokerTransaction]:
        return [
            BrokerTransaction(
                symbol=str(item.get("tradingSymbol") or item.get("symbol") or "").strip().upper(),
                side=str(item.get("transactionType") or "").upper(),
                quantity=Decimal(str(item.get("tradedQuantity", 0))),
                price=Decimal(str(item.get("tradedPrice", 0))),
                transaction_id=item.get("exchangeTradeId") or item.get("tradeId"),
            )
            for item in self.client.trades()
            if item.get("tradingSymbol") or item.get("symbol")
        ]


class UnsupportedBrokerAdapter(BrokerAdapter):
    """Placeholder adapter for brokers not yet connected."""

    def __init__(self, *args: Any, broker_name: str = "unknown", **kwargs: Any) -> None:
        self.name = broker_name

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    def _unsupported(self) -> None:
        raise NotImplementedError(
            f"{self.name} adapter is reserved for a future integration."
        )

    def get_profile(self) -> dict[str, Any]:
        self._unsupported()

    def get_holdings(self) -> list[BrokerHolding]:
        self._unsupported()

    def get_positions(self) -> list[dict[str, Any]]:
        self._unsupported()

    def get_orders(self) -> list[dict[str, Any]]:
        self._unsupported()

    def get_trades(self) -> list[BrokerTransaction]:
        self._unsupported()


class GrowwAdapter(UnsupportedBrokerAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, broker_name="groww", **kwargs)


class AngelOneAdapter(UnsupportedBrokerAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, broker_name="angelone", **kwargs)
