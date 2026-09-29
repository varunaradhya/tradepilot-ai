from __future__ import annotations

from typing import Any

from app.brokers.dhan import DhanClient


def validate_fno_order(decision: dict[str, Any]) -> dict[str, Any]:
    if decision.get("decision") != "QUALIFIED":
        raise ValueError("Only QUALIFIED decisions can reach execution.")
    contract = decision.get("contract") or {}
    security_id = contract.get("security_id")
    quantity = int(decision.get("quantity") or 0)
    lot_size = max(1, int(decision.get("lot_size") or 1))
    if not security_id or quantity <= 0:
        raise ValueError("Qualified decision has invalid contract or quantity.")
    if quantity % lot_size:
        raise ValueError("Quantity must be lot-size aligned.")
    return {
        "security_id": str(security_id),
        "quantity": quantity,
        "entry": float(decision["entry"]),
        "stop": float(decision["stop"]),
        "target": float(decision["target"]),
        "side": "BUY",
    }


def execute_fno_decision(
    client: DhanClient | None,
    decision: dict[str, Any],
    correlation_id: str,
) -> dict[str, Any]:
    """Fail closed: TradePilot remains paper-only.

    The broker adapter is intentionally retained for future integration work,
    but this service must never submit an order while live execution is locked.
    The safety boundary is enforced here as well as at the API route so a
    configuration flag cannot accidentally enable broker execution.
    """
    order = validate_fno_order(decision)
    del client, correlation_id
    return {
        "mode": "PAPER_ONLY",
        "submitted": False,
        "reason": "LIVE_EXECUTION_DISABLED",
        "order": order,
    }
