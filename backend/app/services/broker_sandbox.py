from __future__ import annotations

from app.brokers.registry import registry


READ_ONLY_REQUIRED = frozenset({"profile", "holdings", "positions", "orders", "trades"})
FORBIDDEN_LIVE_CAPABILITIES = frozenset({"place_order", "modify_order", "cancel_order", "live_order"})


def certify_broker_adapter(name: str) -> dict:
    """Certify the adapter contract without connecting to a broker or placing orders."""
    try:
        adapter_cls = registry.get(name)
    except KeyError:
        return {
            "broker": name.strip().lower(),
            "certified": False,
            "reason": "UNSUPPORTED_BROKER",
            "live_execution_allowed": False,
        }

    adapter = object.__new__(adapter_cls)
    capabilities = frozenset(getattr(adapter, "capabilities", frozenset()))
    missing = sorted(READ_ONLY_REQUIRED - capabilities)
    forbidden = sorted(FORBIDDEN_LIVE_CAPABILITIES & capabilities)
    certified = not missing and not forbidden
    return {
        "broker": name.strip().lower(),
        "certified": certified,
        "read_only_capabilities": sorted(capabilities & READ_ONLY_REQUIRED),
        "missing_capabilities": missing,
        "forbidden_live_capabilities": forbidden,
        "live_execution_allowed": False,
        "mode": "SANDBOX_READ_ONLY",
    }
