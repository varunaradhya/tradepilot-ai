from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerCapabilities:
    """Declared broker features; live execution is never implied by a capability."""

    profile: bool = False
    holdings: bool = False
    positions: bool = False
    orders: bool = False
    trades: bool = False
    historical_data: bool = False
    streaming_data: bool = False
    paper_execution: bool = True
    live_execution: bool = False


def capabilities_for(names: frozenset[str]) -> BrokerCapabilities:
    return BrokerCapabilities(
        profile="profile" in names,
        holdings="holdings" in names,
        positions="positions" in names,
        orders="orders" in names,
        trades="trades" in names,
        historical_data="historical_data" in names,
        streaming_data="streaming_data" in names,
        paper_execution=True,
        live_execution=False,
    )
