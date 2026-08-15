from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass

import httpx

INSTRUMENT_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
CACHE_TTL_SECONDS = 24 * 60 * 60

class InstrumentMasterError(RuntimeError):
    pass

@dataclass(frozen=True)
class IndianInstrument:
    security_id: str
    exchange_segment: str
    symbol: str
    name: str
    series: str | None = None
    isin: str | None = None

def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""

def parse_instrument_csv(text: str) -> list[IndianInstrument]:
    reader = csv.DictReader(io.StringIO(text))
    instruments: list[IndianInstrument] = []
    seen_symbols: set[str] = set()
    for row in reader:
        exchange = _first(row, "SEM_EXM_EXCH_ID", "EXCH_ID").upper()
        segment = _first(row, "SEM_SEGMENT", "SEGMENT").upper()
        security_id = _first(row, "SEM_SMST_SECURITY_ID", "SEM_SECURITY_ID", "SECURITY_ID")
        symbol = _first(row, "SEM_TRADING_SYMBOL", "SYMBOL_NAME", "SM_SYMBOL_NAME").upper()
        name = _first(row, "SEM_CUSTOM_SYMBOL", "DISPLAY_NAME", "SYMBOL_NAME", "SM_SYMBOL_NAME")
        instrument = _first(row, "SEM_INSTRUMENT_NAME", "INSTRUMENT").upper()
        series = _first(row, "SEM_SERIES", "SERIES").upper() or None
        isin = _first(row, "ISIN") or None
        if exchange != "NSE" or segment != "E" or instrument not in {"EQUITY", "EQ"}:
            continue
        if series is not None and series != "EQ":
            continue
        if not security_id or not symbol or symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        instruments.append(IndianInstrument(security_id, "NSE_EQ", symbol, name or symbol, series, isin))
    return instruments

class InstrumentMaster:
    def __init__(self, url: str = INSTRUMENT_MASTER_URL, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.url = url
        self.ttl_seconds = ttl_seconds
        self._loaded_at = 0.0
        self._items: list[IndianInstrument] = []

    def load(self, force: bool = False) -> list[IndianInstrument]:
        if self._items and not force:
            if self._loaded_at == 0.0 or time.time() - self._loaded_at < self.ttl_seconds:
                return self._items
        try:
            response = httpx.get(self.url, timeout=30.0)
            response.raise_for_status()
            items = parse_instrument_csv(response.text)
        except (httpx.HTTPError, csv.Error, UnicodeError) as exc:
            raise InstrumentMasterError(f"Unable to load Dhan instrument master: {exc}") from exc
        if not items:
            raise InstrumentMasterError("Dhan instrument master returned no NSE equity instruments")
        self._items = items
        self._loaded_at = time.time()
        return self._items

    def search(self, query: str, limit: int = 20) -> list[IndianInstrument]:
        query = query.strip().upper()
        if len(query) < 2:
            return []
        items = self.load()
        exact = [item for item in items if item.symbol.upper() == query]
        starts = [item for item in items if item.symbol.upper() != query and (item.symbol.upper().startswith(query) or item.name.upper().startswith(query))]
        contains = [item for item in items if item.symbol.upper() != query and item not in starts and (query in item.symbol.upper() or query in item.name.upper())]
        return (exact + starts + contains)[: max(1, min(limit, 100))]

instrument_master = InstrumentMaster()
