from app.providers.market_search import MarketSearchProviderError, YahooFinanceSearchProvider


class IndianSymbolError(ValueError):
    """Raised when a symbol is not available in the Indian equity universe."""


_search_provider = YahooFinanceSearchProvider()


def canonical_indian_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise IndianSymbolError("Enter an Indian NSE/BSE equity symbol.")

    if normalized.endswith(".NS") or normalized.endswith(".BO"):
        normalized = normalized.rsplit(".", 1)[0]

    try:
        results = _search_provider.search(normalized)
    except MarketSearchProviderError:
        # Exact symbols are valid user input even when the external search
        # provider is temporarily unavailable. This keeps watchlist creation
        # independent of a transient Yahoo/NSE lookup outage; quote retrieval
        # can still report market_data_available=False when data is unavailable.
        return normalized

    exact = [item for item in results if item.symbol.upper() == normalized]
    if not exact:
        raise IndianSymbolError(
            f"{normalized} is not available in the Indian NSE/BSE equity universe."
        )

    exact.sort(key=lambda item: 0 if item.exchange == "NSE" else 1)
    return exact[0].symbol.upper()
