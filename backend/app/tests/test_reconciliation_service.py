from decimal import Decimal

from app.brokers.base import BrokerHolding
from app.services.reconciliation_service import reconcile_account, reconcile_holdings, reconcile_orders


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

    assert result["healthy"] is True
    assert result["requires_execution_block"] is False
    assert result["summary"]["matched"] == 1
    assert result["items"][0]["status"] == "MATCHED"


def test_reconciliation_detects_quantity_difference_and_blocks_execution():
    result = reconcile_holdings(
        [Holding("TCS", 10, 3000)],
        [BrokerHolding("TCS", Decimal("8"), Decimal("3000"))],
        "dhan",
    )

    assert result["summary"]["quantity_mismatches"] == 1
    assert result["items"][0]["status"] == "QUANTITY_MISMATCH"
    assert result["requires_execution_block"] is True


def test_reconciliation_detects_position_missing_at_broker():
    result = reconcile_holdings(
        [Holding("INFY", 5, 1500)],
        [],
        "dhan",
    )

    assert result["summary"]["missing_from_broker"] == 1
    assert result["requires_execution_block"] is True


def test_active_local_order_missing_at_broker_is_critical():
    result = reconcile_orders(
        [{"clientOrderId": "sig-1", "symbol": "TCS", "status": "OPEN", "filledQuantity": 0}],
        [],
        "dhan",
    )

    assert result["healthy"] is False
    assert result["requires_execution_block"] is True
    assert result["summary"]["missing_at_broker"] == 1
    assert result["issues"][0]["code"] == "ORDER_MISSING_AT_BROKER"
    assert result["issues"][0]["severity"] == "CRITICAL"


def test_order_status_mismatch_is_detected():
    result = reconcile_orders(
        [{"clientOrderId": "sig-2", "symbol": "RELIANCE", "status": "OPEN", "filledQuantity": 0}],
        [{"orderId": "sig-2", "tradingSymbol": "RELIANCE", "status": "FILLED", "filledQuantity": 10}],
        "dhan",
    )

    assert result["requires_execution_block"] is True
    assert result["summary"]["status_mismatches"] == 1
    assert result["summary"]["filled_quantity_mismatches"] == 1


def test_terminal_missing_order_is_warning_not_execution_block():
    result = reconcile_orders(
        [{"clientOrderId": "sig-3", "symbol": "INFY", "status": "CANCELLED", "filledQuantity": 0}],
        [],
        "dhan",
    )

    assert result["healthy"] is True
    assert result["requires_execution_block"] is False
    assert result["issues"][0]["severity"] == "WARNING"


def test_account_reconciliation_combines_holding_and_order_failures():
    result = reconcile_account(
        [Holding("TCS", 10, 3000)],
        [BrokerHolding("TCS", Decimal("9"), Decimal("3000"))],
        [{"clientOrderId": "sig-4", "symbol": "TCS", "status": "OPEN", "filledQuantity": 0}],
        [],
        "dhan",
    )

    assert result["healthy"] is False
    assert result["requires_execution_block"] is True
    assert result["holdings"]["requires_execution_block"] is True
    assert result["orders"]["requires_execution_block"] is True
