from decimal import Decimal

from app.brokers.base import BrokerHolding
from app.services.reconciliation_service import reconcile_holdings


class Holding:
    def __init__(self, symbol, quantity, average_buy_price):
        self.symbol = symbol
        self.quantity = quantity
        self.average_buy_price = average_buy_price


def test_reconciliation_matches():
    result = reconcile_holdings(
        [Holding("TCS", 10, 3000)],
        [BrokerHolding("TCS", Decimal("10"), Decimal("3000"))],
        "dhan",
    )

    assert result["summary"]["matched"] == 1
    assert result["items"][0]["status"] == "MATCHED"


def test_reconciliation_detects_quantity_difference():
    result = reconcile_holdings(
        [Holding("TCS", 10, 3000)],
        [BrokerHolding("TCS", Decimal("8"), Decimal("3000"))],
        "dhan",
    )

    assert result["summary"]["quantity_mismatches"] == 1
    assert result["items"][0]["status"] == "QUANTITY_MISMATCH"