from app.providers.market_data import (
    HistoricalData,
    MarketDataNotFoundError,
    MarketDataProviderError,
    QuoteData,
    YahooFinanceProvider,
)
from app.providers.market_search import (
    MarketSearchProviderError,
    SearchInstrument,
    get_search_provider,
)
from app.services.instrument_service import IndianSymbolError, canonical_indian_symbol

_provider = YahooFinanceProvider()
_search_provider = get_search_provider()


def get_quote(symbol: str) -> QuoteData:
    return _provider.get_quote(canonical_indian_symbol(symbol))


def get_history(
    symbol: str,
    range_: str = "1mo",
    interval: str = "1d",
) -> HistoricalData:
    return _provider.get_history(
        symbol=canonical_indian_symbol(symbol),
        range_=range_,
        interval=interval,
    )


def search_instruments(query: str) -> list[SearchInstrument]:
    return _search_provider.search(query)


__all__ = [
    "get_quote",
    "get_history",
    "search_instruments",
    "IndianSymbolError",
    "MarketDataProviderError",
    "MarketDataNotFoundError",
    "MarketSearchProviderError",
]
