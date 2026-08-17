from __future__ import annotations

from dataclasses import dataclass

from app.services.instrument_master_service import InstrumentMasterError, instrument_master


class MarketSearchProviderError(Exception):
    """Raised when the authoritative Indian stock universe cannot be loaded."""


class IndianInstrumentNotFoundError(ValueError):
    """Raised when a requested symbol is not an NSE cash-equity instrument."""


@dataclass(frozen=True)
class SearchInstrument:
    symbol: str
    name: str
    exchange: str
    security_id: str
    exchange_segment: str


class DhanInstrumentSearchProvider:
    """Search only instruments that exist in Dhan's NSE equity master.

    This is deliberately authoritative: provider autocomplete is never used to
    invent a symbol and arbitrary user-entered names are never accepted as a
    valid instrument. The master is refreshed by the backend cache once per day.
    """

    def search(self, query: str, limit: int = 20) -> list[SearchInstrument]:
        normalized = " ".join(query.strip().split())
        if len(normalized) < 2:
            return []
        try:
            items = instrument_master.search(normalized, limit=limit)
        except InstrumentMasterError as exc:
            raise MarketSearchProviderError(
                "The Indian stock universe is temporarily unavailable. Please try again shortly."
            ) from exc
        return [
            SearchInstrument(
                symbol=item.symbol,
                name=item.name,
                exchange="NSE",
                security_id=item.security_id,
                exchange_segment=item.exchange_segment,
            )
            for item in items
        ]

    def resolve_exact(self, symbol: str) -> SearchInstrument:
        normalized = symbol.strip().upper()
        if normalized.endswith(".NS"):
            normalized = normalized[:-3]
        if normalized.endswith(".BO"):
            raise IndianInstrumentNotFoundError(
                "TradePilot currently supports NSE cash equities only. Select an NSE stock from the suggestions."
            )
        if not normalized:
            raise IndianInstrumentNotFoundError("Select an NSE stock from the suggestions.")
        try:
            items = instrument_master.search(normalized, limit=100)
        except InstrumentMasterError as exc:
            raise MarketSearchProviderError(
                "The Indian stock universe is temporarily unavailable. Please try again shortly."
            ) from exc
        exact = next((item for item in items if item.symbol.upper() == normalized), None)
        if exact is None:
            raise IndianInstrumentNotFoundError(
                f"{normalized} is not an active NSE equity instrument. Select a stock from the suggestions."
            )
        return SearchInstrument(
            symbol=exact.symbol,
            name=exact.name,
            exchange="NSE",
            security_id=exact.security_id,
            exchange_segment=exact.exchange_segment,
        )


_search_provider = DhanInstrumentSearchProvider()


def get_search_provider() -> DhanInstrumentSearchProvider:
    return _search_provider
