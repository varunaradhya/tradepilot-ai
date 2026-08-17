from dataclasses import dataclass
from datetime import datetime
import time

import httpx


class MarketDataProviderError(Exception):
    """Raised when a market-data provider cannot return valid data."""


class MarketDataNotFoundError(MarketDataProviderError):
    """Raised when the provider is reachable but the symbol has no data."""


@dataclass
class QuoteData:
    symbol: str
    name: str | None
    currency: str | None
    exchange: str | None
    price: float
    previous_close: float | None
    change: float | None
    change_percent: float | None
    market_time: datetime | None
    data_status: str = "LIVE"


@dataclass
class HistoricalData:
    symbol: str
    currency: str | None
    interval: str
    range: str
    data: list[dict]
    data_status: str = "LIVE"


class YahooFinanceProvider:
    """Market-data adapter for validated NSE cash-equity symbols.

    Instrument identity is validated before this adapter is called. The data
    provider therefore never decides whether a symbol is Indian, NSE or BSE.
    Only the NSE Yahoo suffix is used, with query1/query2 as transport fallbacks.
    """

    BASE_URLS = (
        "https://query1.finance.yahoo.com/v8/finance/chart",
        "https://query2.finance.yahoo.com/v8/finance/chart",
    )
    NSE_SUFFIX = ".NS"
    CACHE_TTL_SECONDS = 30
    HISTORY_CACHE_TTL_SECONDS = 180
    _cache: dict[tuple[str, str, str], tuple[float, dict]] = {}

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    @classmethod
    def _candidate_provider_symbols(cls, symbol: str) -> list[str]:
        normalized = symbol.strip().upper()
        if not normalized:
            raise MarketDataProviderError("Symbol is required")
        if "." in normalized:
            if normalized.endswith(cls.NSE_SUFFIX):
                return [normalized]
            raise MarketDataProviderError("Only NSE symbols are supported")
        return [f"{normalized}{cls.NSE_SUFFIX}"]

    @classmethod
    def _provider_symbol(cls, symbol: str) -> str:
        return cls._candidate_provider_symbols(symbol)[0]

    @classmethod
    def _cached(cls, key: tuple[str, str, str]) -> dict | None:
        cached = cls._cache.get(key)
        if cached is None:
            return None
        created_at, payload = cached
        ttl = cls.HISTORY_CACHE_TTL_SECONDS if key[1] != "1d" or key[2] != "1d" else cls.CACHE_TTL_SECONDS
        if time.monotonic() - created_at >= ttl:
            cls._cache.pop(key, None)
            return None
        return payload

    @classmethod
    def _store_cache(cls, key: tuple[str, str, str], payload: dict) -> dict:
        cls._cache[key] = (time.monotonic(), payload)
        return payload

    def _get_chart(self, symbol: str, range_: str, interval: str) -> tuple[dict, str]:
        last_error: Exception | None = None
        symbol_not_found = True
        for provider_symbol in self._candidate_provider_symbols(symbol):
            key = (provider_symbol, range_, interval)
            cached = self._cached(key)
            if cached is not None:
                return cached, "CACHED"
            for base_url in self.BASE_URLS:
                url = f"{base_url}/{provider_symbol}"
                try:
                    response = httpx.get(url, params={"range": range_, "interval": interval, "includePrePost": "false", "events": "div,splits"}, timeout=self.timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 TradePilotAI/1.0"})
                    if response.status_code == 429:
                        symbol_not_found = False
                        last_error = httpx.HTTPStatusError("429 Too Many Requests", request=response.request, response=response)
                        continue
                    response.raise_for_status()
                    payload = response.json(); chart = payload.get("chart", {}); error = chart.get("error")
                    if error:
                        last_error = MarketDataProviderError(error.get("description") or "Unknown provider error"); continue
                    results = chart.get("result") or []
                    if not results:
                        last_error = MarketDataNotFoundError(f"No market data found for symbol {symbol.strip().upper()}"); continue
                    symbol_not_found = False
                    return self._store_cache(key, results[0]), "LIVE"
                except (httpx.HTTPError, ValueError) as exc:
                    symbol_not_found = False; last_error = exc; continue
        if isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code == 429:
            raise MarketDataProviderError("Market data provider is temporarily rate-limiting requests. Please try again in a few seconds.") from last_error
        if symbol_not_found and isinstance(last_error, MarketDataNotFoundError): raise last_error
        if isinstance(last_error, ValueError): raise MarketDataProviderError("Market data provider returned invalid JSON") from last_error
        if last_error is not None: raise MarketDataProviderError(str(last_error)) from last_error
        raise MarketDataProviderError("Market data provider request failed")

    def get_quote(self, symbol: str) -> QuoteData:
        requested_symbol = symbol.strip().upper(); result, data_status = self._get_chart(requested_symbol, "1d", "1d"); meta = result.get("meta", {}); price = meta.get("regularMarketPrice")
        if price is None: raise MarketDataNotFoundError(f"Current price unavailable for {requested_symbol}")
        previous_close = meta.get("previousClose"); change = None; change_percent = None
        if previous_close is not None:
            change = price - previous_close
            if previous_close != 0: change_percent = (change / previous_close) * 100
        market_time = datetime.fromtimestamp(meta["regularMarketTime"]) if meta.get("regularMarketTime") else None
        return QuoteData(requested_symbol, meta.get("shortName") or meta.get("longName"), meta.get("currency"), "NSE", float(price), float(previous_close) if previous_close is not None else None, change, change_percent, market_time, data_status)

    def get_history(self, symbol: str, range_: str = "1mo", interval: str = "1d") -> HistoricalData:
        requested_symbol = symbol.strip().upper(); result, data_status = self._get_chart(requested_symbol, range_, interval); meta = result.get("meta", {}); timestamps = result.get("timestamp") or []; quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []; highs = quote.get("high") or []; lows = quote.get("low") or []; closes = quote.get("close") or []; volumes = quote.get("volume") or []; data = []
        for index, timestamp in enumerate(timestamps):
            def value(values): return values[index] if index < len(values) else None
            data.append({"timestamp": datetime.fromtimestamp(timestamp), "open": value(opens), "high": value(highs), "low": value(lows), "close": value(closes), "volume": value(volumes)})
        return HistoricalData(requested_symbol, meta.get("currency"), interval, range_, data, data_status)
