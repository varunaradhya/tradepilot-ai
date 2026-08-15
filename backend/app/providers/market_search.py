from dataclasses import dataclass
import time

import httpx


class MarketSearchProviderError(Exception):
    """Raised when stock symbol search cannot be completed."""


@dataclass(frozen=True)
class SearchInstrument:
    symbol: str
    name: str
    exchange: str


class YahooFinanceSearchProvider:
    """India-first symbol search backed by Yahoo Finance autocomplete.

    Yahoo's search endpoint is used only for discovery; returned instruments
    are filtered to Indian equity tickers (.NS/.BO). Results are cached briefly
    so typing in the search box does not create one upstream request per key.
    """

    BASE_URLS = (
        "https://query1.finance.yahoo.com/v1/finance/search",
        "https://query2.finance.yahoo.com/v1/finance/search",
    )
    CACHE_TTL_SECONDS = 300
    _cache: dict[str, tuple[float, list[SearchInstrument]]] = {}

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    @classmethod
    def _cached(cls, query: str) -> list[SearchInstrument] | None:
        item = cls._cache.get(query)
        if item is None:
            return None
        created_at, results = item
        if time.monotonic() - created_at >= cls.CACHE_TTL_SECONDS:
            cls._cache.pop(query, None)
            return None
        return results

    @classmethod
    def _store(cls, query: str, results: list[SearchInstrument]) -> list[SearchInstrument]:
        cls._cache[query] = (time.monotonic(), results)
        return results

    @staticmethod
    def _is_indian_equity(item: dict) -> bool:
        symbol = str(item.get("symbol") or "").upper()
        quote_type = str(item.get("quoteType") or "").upper()
        return quote_type == "EQUITY" and (symbol.endswith(".NS") or symbol.endswith(".BO"))

    @classmethod
    def _parse(cls, payload: dict) -> list[SearchInstrument]:
        results: list[SearchInstrument] = []
        seen: set[tuple[str, str]] = set()
        for item in payload.get("quotes") or []:
            if not cls._is_indian_equity(item):
                continue
            provider_symbol = str(item.get("symbol") or "").upper()
            exchange = "NSE" if provider_symbol.endswith(".NS") else "BSE"
            symbol = provider_symbol.rsplit(".", 1)[0]
            name = str(item.get("longname") or item.get("shortname") or symbol).strip()
            key = (symbol, exchange)
            if key in seen:
                continue
            seen.add(key)
            results.append(SearchInstrument(symbol=symbol, name=name, exchange=exchange))
        results.sort(key=lambda item: (0 if item.exchange == "NSE" else 1, item.symbol))
        return results[:12]

    def search(self, query: str) -> list[SearchInstrument]:
        normalized = " ".join(query.strip().split()).lower()
        if len(normalized) < 2:
            return []
        cached = self._cached(normalized)
        if cached is not None:
            return cached

        last_error: Exception | None = None
        for base_url in self.BASE_URLS:
            try:
                response = httpx.get(
                    base_url,
                    params={"q": normalized, "quotesCount": "20", "newsCount": "0"},
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 TradePilotAI/0.1"},
                )
                if response.status_code == 429:
                    last_error = httpx.HTTPStatusError(
                        "429 Too Many Requests", request=response.request, response=response
                    )
                    continue
                response.raise_for_status()
                return self._store(normalized, self._parse(response.json()))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise MarketSearchProviderError(
                "Stock search is temporarily unavailable. You can still enter an exact NSE symbol."
            ) from last_error
        return []
