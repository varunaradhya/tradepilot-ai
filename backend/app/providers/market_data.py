from dataclasses import dataclass
from datetime import datetime

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

    User-facing symbols such as TCS are translated to Yahoo's TCS.NS
    ticker format. Symbols that already contain an exchange suffix are
    passed through unchanged.
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    NSE_SUFFIX = ".NS"

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

    def _get_chart(self, symbol: str, range_: str, interval: str) -> dict:
        provider_symbol = self._provider_symbol(symbol)
        url = f"{self.BASE_URL}/{provider_symbol}"

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
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPError as exc:
            raise MarketDataProviderError(
                f"Market data provider request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise MarketDataProviderError(
                "Market data provider returned invalid JSON"
            ) from exc

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

        return results[0]

    def get_quote(self, symbol: str) -> QuoteData:
        requested_symbol = symbol.strip().upper()
        result = self._get_chart(requested_symbol, "1d", "1d")

        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")

        if price is None:
            raise MarketDataProviderError(
                f"Current price unavailable for {requested_symbol}"
            )

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
            previous_close=(
                float(previous_close) if previous_close is not None else None
            ),
            change=change,
            change_percent=change_percent,
            market_time=market_time,
        )

    def get_history(
        self,
        symbol: str,
        range_: str = "1mo",
        interval: str = "1d",
    ) -> HistoricalData:
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
                if index >= len(values):
                    return None
                return values[index]

            data.append(
                {
                    "timestamp": datetime.fromtimestamp(timestamp),
                    "open": value(opens),
                    "high": value(highs),
                    "low": value(lows),
                    "close": value(closes),
                    "volume": value(volumes),
                }
            )

        return HistoricalData(
            symbol=requested_symbol,
            currency=meta.get("currency"),
            interval=interval,
            range=range_,
            data=data,
        )
