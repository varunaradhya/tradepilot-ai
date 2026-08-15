from dataclasses import dataclass
from datetime import datetime
import time

import httpx


class MarketDataProviderError(Exception):
    """Raised when a market-data provider cannot return valid data."""


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


@dataclass
class HistoricalData:
    symbol: str
    currency: str | None
    interval: str
    range: str
    data: list[dict]


class YahooFinanceProvider:
    """Yahoo Finance chart-data provider for NSE-listed Indian stocks.

    Plain user-facing symbols such as TCS are translated to TCS.NS. The
    provider uses a small in-process TTL cache and a second Yahoo chart host
    as a fallback so browser refreshes do not immediately turn into 429s.
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
    def _provider_symbol(cls, symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized:
            raise MarketDataProviderError("Symbol is required")
        if "." in normalized:
            return normalized
        return f"{normalized}{cls.NSE_SUFFIX}"

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

    def _get_chart(self, symbol: str, range_: str, interval: str) -> dict:
        provider_symbol = self._provider_symbol(symbol)
        key = (provider_symbol, range_, interval)
        cached = self._cached(key)
        if cached is not None:
            return cached

        last_error: Exception | None = None
        for base_url in self.BASE_URLS:
            url = f"{base_url}/{provider_symbol}"
            try:
                response = httpx.get(
                    url,
                    params={
                        "range": range_,
                        "interval": interval,
                        "includePrePost": "false",
                        "events": "div,splits",
                    },
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 TradePilotAI/0.1"},
                )
                if response.status_code == 429:
                    last_error = httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=response.request,
                        response=response,
                    )
                    continue
                response.raise_for_status()
                payload = response.json()
                chart = payload.get("chart", {})
                error = chart.get("error")
                if error:
                    description = error.get("description") or "Unknown provider error"
                    raise MarketDataProviderError(description)
                results = chart.get("result") or []
                if not results:
                    raise MarketDataProviderError(
                        f"No market data found for symbol {symbol.strip().upper()}"
                    )
                return self._store_cache(key, results[0])
            except MarketDataProviderError:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                continue

        if last_error is not None:
            if isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code == 429:
                raise MarketDataProviderError(
                    "Market data provider is temporarily rate-limiting requests. Please try again in a few seconds."
                ) from last_error
            if isinstance(last_error, ValueError):
                raise MarketDataProviderError("Market data provider returned invalid JSON") from last_error
            raise MarketDataProviderError(f"Market data provider request failed: {last_error}") from last_error
        raise MarketDataProviderError("Market data provider request failed")

    def get_quote(self, symbol: str) -> QuoteData:
        requested_symbol = symbol.strip().upper()
        result = self._get_chart(requested_symbol, "1d", "1d")
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        if price is None:
            raise MarketDataProviderError(f"Current price unavailable for {requested_symbol}")

        previous_close = meta.get("previousClose")
        change = None
        change_percent = None
        if previous_close is not None:
            change = price - previous_close
            if previous_close != 0:
                change_percent = (change / previous_close) * 100

        market_time = None
        if meta.get("regularMarketTime"):
            market_time = datetime.fromtimestamp(meta["regularMarketTime"])

        return QuoteData(
            symbol=requested_symbol,
            name=meta.get("shortName") or meta.get("longName"),
            currency=meta.get("currency"),
            exchange=meta.get("exchangeName"),
            price=float(price),
            previous_close=float(previous_close) if previous_close is not None else None,
            change=change,
            change_percent=change_percent,
            market_time=market_time,
        )

    def get_history(self, symbol: str, range_: str = "1mo", interval: str = "1d") -> HistoricalData:
        requested_symbol = symbol.strip().upper()
        result = self._get_chart(requested_symbol, range_, interval)
        meta = result.get("meta", {})
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators", {})
        quotes = indicators.get("quote") or [{}]
        quote = quotes[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        data = []

        for index, timestamp in enumerate(timestamps):
            def value(values):
                return values[index] if index < len(values) else None
            data.append({
                "timestamp": datetime.fromtimestamp(timestamp),
                "open": value(opens),
                "high": value(highs),
                "low": value(lows),
                "close": value(closes),
                "volume": value(volumes),
            })

        return HistoricalData(
            symbol=requested_symbol,
            currency=meta.get("currency"),
            interval=interval,
            range=range_,
            data=data,
        )
