from app.providers.market_data import (
    HistoricalData,
    MarketDataProviderError,
    QuoteData,
    YahooFinanceProvider,
)

_provider = YahooFinanceProvider()


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


__all__ = [
    "get_quote",
    "get_history",
    "MarketDataProviderError",
]
