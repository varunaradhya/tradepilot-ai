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
    YahooFinanceSearchProvider,
)

_provider = YahooFinanceProvider()
_search_provider = YahooFinanceSearchProvider()


def get_quote(symbol: str) -> QuoteData:
    return _provider.get_quote(symbol)


def get_history(
    symbol: str,
    range_: str = "1mo",
    interval: str = "1d",
) -> HistoricalData:
    return _provider.get_history(
        symbol=symbol,
        range_=range_,
        interval=interval,
    )


def search_instruments(query: str) -> list[SearchInstrument]:
    return _search_provider.search(query)


__all__ = [
    "get_quote",
    "get_history",
    "search_instruments",
    "MarketDataProviderError",
    "MarketDataNotFoundError",
    "MarketSearchProviderError",
]
