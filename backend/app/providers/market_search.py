from dataclasses import dataclass
import csv
import io
import time

import httpx


class MarketSearchProviderError(Exception):
    """Raised when stock symbol search cannot be completed."""


class IndianInstrumentNotFoundError(ValueError):
    """Raised when a requested symbol is not an Indian listed equity."""


@dataclass(frozen=True)
class SearchInstrument:
    symbol: str
    name: str
    exchange: str


class YahooFinanceSearchProvider:
    """India-first stock search using the NSE equity master plus Yahoo fallback.

    The NSE equity master is the authoritative symbol universe for NSE-listed
    equities. It is refreshed once per day. Yahoo autocomplete remains useful
    for company-name discovery and BSE results, but it no longer determines
    whether an NSE stock appears in suggestions.
    """

    BASE_URLS = (
        "https://query1.finance.yahoo.com/v1/finance/search",
        "https://query2.finance.yahoo.com/v1/finance/search",
    )
    NSE_MASTER_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    CACHE_TTL_SECONDS = 300
    NSE_MASTER_TTL_SECONDS = 86400
    _cache: dict[str, tuple[float, list[SearchInstrument]]] = {}
    _nse_master: tuple[float, list[SearchInstrument]] | None = None

    def __init__(self, timeout: float = 8.0):
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

    @classmethod
    def _load_nse_master(cls, timeout: float = 8.0) -> list[SearchInstrument]:
        cached = cls._nse_master
        if cached is not None and time.monotonic() - cached[0] < cls.NSE_MASTER_TTL_SECONDS:
            return cached[1]

        response = httpx.get(
            cls.NSE_MASTER_URL,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 TradePilotAI/0.1",
                "Referer": "https://www.nseindia.com/",
                "Accept": "text/csv,text/plain,*/*",
            },
        )
        response.raise_for_status()

        instruments: list[SearchInstrument] = []
        reader = csv.DictReader(io.StringIO(response.text.lstrip("\ufeff")))
        for row in reader:
            symbol = str(row.get("SYMBOL") or "").strip().upper()
            series = str(row.get(" SERIES") or row.get("SERIES") or "").strip().upper()
            name = str(row.get("NAME OF COMPANY") or "").strip()
            if symbol and name and (not series or series == "EQ"):
                instruments.append(SearchInstrument(symbol=symbol, name=name, exchange="NSE"))

        instruments.sort(key=lambda item: item.symbol)
        cls._nse_master = (time.monotonic(), instruments)
        return instruments

    @classmethod
    def _search_nse_master(cls, query: str) -> list[SearchInstrument]:
        instruments = cls._load_nse_master()
        needle = query.casefold()
        matches = [
            item
            for item in instruments
            if needle in item.symbol.casefold() or needle in item.name.casefold()
        ]
        matches.sort(
            key=lambda item: (
                0 if item.symbol.casefold().startswith(needle) else 1,
                0 if item.name.casefold().startswith(needle) else 1,
                item.symbol,
            )
        )
        return matches[:12]

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

    def _search_yahoo(self, query: str) -> list[SearchInstrument]:
        last_error: Exception | None = None
        for base_url in self.BASE_URLS:
            try:
                response = httpx.get(
                    base_url,
                    params={"q": query, "quotesCount": "20", "newsCount": "0"},
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
                return self._parse(response.json())
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise MarketSearchProviderError(
                "Stock search is temporarily unavailable. You can still enter an exact NSE symbol."
            ) from last_error
        return []

    def search(self, query: str) -> list[SearchInstrument]:
        normalized = " ".join(query.strip().split()).lower()
        if len(normalized) < 2:
            return []
        cached = self._cached(normalized)
        if cached is not None:
            return cached

        results: list[SearchInstrument] = []
        errors: list[Exception] = []
        try:
            results.extend(self._search_nse_master(normalized))
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(exc)

        try:
            results.extend(self._search_yahoo(normalized))
        except MarketSearchProviderError as exc:
            errors.append(exc)

        deduped: dict[tuple[str, str], SearchInstrument] = {}
        for item in results:
            deduped[(item.symbol, item.exchange)] = item

        final = list(deduped.values())
        final.sort(
            key=lambda item: (
                0 if item.symbol.casefold().startswith(normalized) else 1,
                0 if item.exchange == "NSE" else 1,
                item.symbol,
            )
        )
        if final:
            return self._store(normalized, final[:12])
        if errors:
            raise MarketSearchProviderError(
                "Indian stock search is temporarily unavailable. You can still enter an exact NSE symbol."
            ) from errors[-1]
        return self._store(normalized, [])

    def resolve_exact(self, symbol: str) -> SearchInstrument:
        """Resolve an exact Indian listed equity and reject non-Indian symbols."""
        normalized = symbol.strip().upper()
        if normalized.endswith(".NS") or normalized.endswith(".BO"):
            normalized = normalized.rsplit(".", 1)[0]
        if not normalized or len(normalized) < 1:
            raise IndianInstrumentNotFoundError("Enter an Indian NSE/BSE equity symbol.")

        results = self.search(normalized)
        exact = [item for item in results if item.symbol.upper() == normalized]
        if not exact:
            raise IndianInstrumentNotFoundError(
                f"{normalized} is not available in the Indian NSE/BSE equity universe."
            )
        exact.sort(key=lambda item: 0 if item.exchange == "NSE" else 1)
        return exact[0]
