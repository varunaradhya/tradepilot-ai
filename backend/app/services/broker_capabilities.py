from dataclasses import dataclass
from enum import Enum
import re


class BrokerCapability(str, Enum):
    HISTORICAL_DATA = "historical_data"
    MARKET_DATA = "market_data"
    PORTFOLIO = "portfolio"
    PAPER_ORDERS = "paper_orders"
    LIVE_ORDERS = "live_orders"


@dataclass(frozen=True)
class BrokerCapabilities:
    historical_data: bool = False
    market_data: bool = False
    portfolio: bool = False
    paper_orders: bool = True
    live_orders: bool = False
    integration_status: str = "UNSUPPORTED"


# Capabilities describe the intended provider surface; integration_status says
# whether TradePilot has actually implemented and verified that provider path.
BROKER_CAPABILITIES = {
    "DHAN": BrokerCapabilities(
        historical_data=True,
        market_data=True,
        portfolio=True,
        integration_status="FOUNDATION",
    ),
    "GROWW": BrokerCapabilities(
        historical_data=True,
        market_data=True,
        portfolio=True,
        integration_status="FOUNDATION_ONLY",
    ),
    "ANGELONE": BrokerCapabilities(
        historical_data=True,
        market_data=True,
        portfolio=True,
        integration_status="FOUNDATION_ONLY",
    ),
}


def normalize_broker_name(name: str) -> str:
    """Normalize common broker display names and provider aliases."""
    value = re.sub(r"[^A-Z0-9]", "", name.strip().upper())
    aliases = {
        "DHAN": "DHAN",
        "GROWW": "GROWW",
        "ANGELONE": "ANGELONE",
        "ANGELONESMARTAPI": "ANGELONE",
        "SMARTAPI": "ANGELONE",
    }
    return aliases.get(value, value)


def get_broker_capabilities(name: str) -> BrokerCapabilities:
    return BROKER_CAPABILITIES.get(normalize_broker_name(name), BrokerCapabilities())


def live_execution_enabled(name: str) -> bool:
    # Explicitly false until TradePilot's production/live-order safety gates are completed.
    return False


def broker_integration_status(name: str) -> str:
    return get_broker_capabilities(name).integration_status
