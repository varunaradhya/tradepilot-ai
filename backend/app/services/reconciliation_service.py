from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable

from app.brokers.base import BrokerHolding
from app.models.holding import Holding


ACTIVE_ORDER_STATES = {"OPEN", "PENDING", "TRIGGER_PENDING", "PARTIALLY_FILLED", "TRANSIT"}
TERMINAL_ORDER_STATES = {"FILLED", "CANCELLED", "REJECTED", "EXPIRED", "COMPLETED"}


def _symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _order_id(order: dict[str, Any]) -> str | None:
    value = (
        order.get("clientOrderId")
        or order.get("client_order_id")
        or order.get("orderId")
        or order.get("order_id")
    )
    return str(value).strip() if value is not None and str(value).strip() else None


def _status(order: dict[str, Any]) -> str:
    return str(order.get("orderStatus") or order.get("status") or "UNKNOWN").strip().upper()


def reconcile_holdings(
    holdings: Iterable[Holding],
    broker_holdings: Iterable[BrokerHolding],
    broker_name: str,
    *,
    quantity_tolerance: Decimal = Decimal("0.0001"),
    average_price_tolerance: Decimal = Decimal("0.01"),
) -> dict:
    """Compare TradePilot holdings with the broker's authoritative holdings.

    The function is deliberately read-only: mismatches are surfaced and never
    silently repaired. Critical quantity/missing-position mismatches should
    block execution until a fresh broker sync establishes the truth.
    """
    if quantity_tolerance < 0 or average_price_tolerance < 0:
        raise ValueError("reconciliation tolerances must be non-negative")

    tp = {_symbol(h.symbol): h for h in holdings}
    br = {_symbol(h.symbol): h for h in broker_holdings}
    symbols = sorted(set(tp) | set(br))
    items = []
    matched = quantity_mismatches = average_mismatches = 0
    missing_tp = missing_br = 0

    for symbol in symbols:
        t = tp.get(symbol)
        b = br.get(symbol)
        tq = Decimal(str(t.quantity)) if t else Decimal("0")
        bq = Decimal(str(b.quantity)) if b else Decimal("0")
        tap = Decimal(str(t.average_buy_price)) if t else Decimal("0")
        bap = Decimal(str(b.average_price)) if b else Decimal("0")
        qdiff = tq - bq
        pdiff = tap - bap

        if t is None:
            status = "MISSING_FROM_TRADEPILOT"
            missing_tp += 1
        elif b is None:
            status = "MISSING_FROM_BROKER"
            missing_br += 1
        elif abs(qdiff) > quantity_tolerance:
            status = "QUANTITY_MISMATCH"
            quantity_mismatches += 1
        elif abs(pdiff) > average_price_tolerance:
            status = "AVERAGE_PRICE_MISMATCH"
            average_mismatches += 1
        else:
            status = "MATCHED"
            matched += 1

        items.append({
            "symbol": symbol,
            "tradepilot_quantity": float(tq),
            "broker_quantity": float(bq),
            "quantity_difference": float(qdiff),
            "tradepilot_average_price": float(tap),
            "broker_average_price": float(bap),
            "average_price_difference": float(pdiff),
            "status": status,
        })

    critical = quantity_mismatches + missing_tp + missing_br
    return {
        "broker": broker_name,
        "healthy": critical == 0,
        "requires_execution_block": critical > 0,
        "summary": {
            "matched": matched,
            "quantity_mismatches": quantity_mismatches,
            "average_price_mismatches": average_mismatches,
            "missing_from_tradepilot": missing_tp,
            "missing_from_broker": missing_br,
        },
        "items": items,
    }


def reconcile_orders(
    internal_orders: Iterable[dict[str, Any]],
    broker_orders: Iterable[dict[str, Any]],
    broker_name: str,
) -> dict:
    """Compare locally tracked order state with broker order state.

    An active local order missing at the broker is CRITICAL: automatically
    retrying it could create a duplicate position. Status/filled-quantity
    disagreements are also surfaced instead of guessed away.
    """
    local = {order_id: order for order in internal_orders if (order_id := _order_id(order))}
    remote = {order_id: order for order in broker_orders if (order_id := _order_id(order))}
    issues = []
    matched = status_mismatches = fill_mismatches = missing_remote = 0

    for order_id, order in local.items():
        broker_order = remote.get(order_id)
        symbol = _symbol(order.get("symbol") or order.get("tradingSymbol"))
        local_status = _status(order)
        if broker_order is None:
            if local_status in ACTIVE_ORDER_STATES:
                severity = "CRITICAL"
                missing_remote += 1
                message = f"Active order {order_id} is missing at {broker_name}; do not retry automatically."
            elif local_status in TERMINAL_ORDER_STATES:
                severity = "WARNING"
                message = f"Terminal order {order_id} is no longer visible at {broker_name}."
            else:
                severity = "CRITICAL"
                missing_remote += 1
                message = f"Order {order_id} has unknown local state and is missing at {broker_name}."
            issues.append({"code": "ORDER_MISSING_AT_BROKER", "severity": severity, "order_id": order_id, "symbol": symbol, "message": message})
            continue

        broker_status = _status(broker_order)
        if local_status != broker_status:
            status_mismatches += 1
            severity = "CRITICAL" if local_status != broker_status and (local_status in ACTIVE_ORDER_STATES or broker_status in ACTIVE_ORDER_STATES) else "WARNING"
            issues.append({"code": "ORDER_STATUS_MISMATCH", "severity": severity, "order_id": order_id, "symbol": symbol, "message": f"TradePilot={local_status}, broker={broker_status}."})

        local_filled = Decimal(str(order.get("filledQuantity") or order.get("filled_quantity") or order.get("filledQty") or 0))
        broker_filled = Decimal(str(broker_order.get("filledQuantity") or broker_order.get("filled_quantity") or broker_order.get("filledQty") or 0))
        if abs(local_filled - broker_filled) > Decimal("0.0001"):
            fill_mismatches += 1
            issues.append({"code": "ORDER_FILLED_QUANTITY_MISMATCH", "severity": "CRITICAL", "order_id": order_id, "symbol": symbol, "message": f"TradePilot filled={local_filled}, broker filled={broker_filled}."})
        if local_status == broker_status and abs(local_filled - broker_filled) <= Decimal("0.0001"):
            matched += 1

    return {
        "broker": broker_name,
        "healthy": not any(i["severity"] == "CRITICAL" for i in issues),
        "requires_execution_block": any(i["severity"] == "CRITICAL" for i in issues),
        "summary": {
            "matched": matched,
            "status_mismatches": status_mismatches,
            "filled_quantity_mismatches": fill_mismatches,
            "missing_at_broker": missing_remote,
        },
        "issues": issues,
    }


def reconcile_account(
    holdings: Iterable[Holding],
    broker_holdings: Iterable[BrokerHolding],
    internal_orders: Iterable[dict[str, Any]],
    broker_orders: Iterable[dict[str, Any]],
    broker_name: str,
) -> dict:
    """Run holdings and order reconciliation and return one fail-closed result."""
    holdings_result = reconcile_holdings(holdings, broker_holdings, broker_name)
    orders_result = reconcile_orders(internal_orders, broker_orders, broker_name)
    critical_issues = (
        [item for item in holdings_result["items"] if item["status"] in {"MISSING_FROM_TRADEPILOT", "MISSING_FROM_BROKER", "QUANTITY_MISMATCH"}]
        + [item for item in orders_result["issues"] if item["severity"] == "CRITICAL"]
    )
    return {
        "broker": broker_name,
        "healthy": not critical_issues,
        "requires_execution_block": bool(critical_issues),
        "holdings": holdings_result,
        "orders": orders_result,
    }
