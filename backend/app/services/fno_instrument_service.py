from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass
from datetime import date, datetime

import httpx


FNO_INSTRUMENT_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
ACTIVE_INSTRUMENTS = {"OPTIDX", "OPTSTK"}
INDEX_NAMES = {
    "NIFTY": "Nifty 50",
    "BANKNIFTY": "Nifty Bank",
    "FINNIFTY": "Nifty Financial Services",
    "MIDCPNIFTY": "Nifty Midcap Select",
    "NIFTYNXT50": "Nifty Next 50",
}


class FNOInstrumentMasterError(RuntimeError):
    """Raised when the Dhan derivative instrument universe cannot be loaded."""


@dataclass(frozen=True)
class FNOUnderlying:
    security_id: str
    exchange_segment: str
    symbol: str
    name: str


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def _expiry_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_fno_instrument_csv(text: str, today: date | None = None) -> list[FNOUnderlying]:
    """Build underlyings from active NSE option contracts, not every NSE index.

    Dhan's detailed master exposes UNDERLYING_SECURITY_ID and UNDERLYING_SYMBOL
    on derivative rows. Using those fields prevents us from accidentally sending
    an index security id that has no option contracts (for example Nifty Midcap
    150) to the option-chain API.
    """
    today = today or date.today()
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    found: dict[tuple[str, str], FNOUnderlying] = {}

    for row in reader:
        exchange = _first(row, "EXCH_ID", "SEM_EXM_EXCH_ID").upper()
        segment = _first(row, "SEGMENT", "SEM_SEGMENT").upper()
        instrument = _first(row, "INSTRUMENT", "SEM_INSTRUMENT_NAME").upper()
        if exchange != "NSE" or segment != "D" or instrument not in ACTIVE_INSTRUMENTS:
            continue

        expiry = _expiry_date(_first(row, "EXPIRY_DATE", "SEM_EXPIRY_DATE"))
        if expiry is not None and expiry < today:
            continue

        security_id = _first(
            row,
            "UNDERLYING_SECURITY_ID",
            "SEM_UNDERLYING_SECURITY_ID",
            "UNDERLYING_SECURITYID",
        )
        symbol = _first(
            row,
            "UNDERLYING_SYMBOL",
            "SEM_UNDERLYING_SYMBOL",
        ).upper()
        if not security_id or not symbol:
            continue

        exchange_segment = "IDX_I" if instrument == "OPTIDX" else "NSE_EQ"
        name = INDEX_NAMES.get(symbol, symbol)
        key = (exchange_segment, security_id)
        found[key] = FNOUnderlying(
            security_id=security_id,
            exchange_segment=exchange_segment,
            symbol=symbol,
            name=name,
        )

    return sorted(found.values(), key=lambda item: (item.symbol, item.exchange_segment))


class FNOInstrumentMaster:
    def __init__(self, url: str = FNO_INSTRUMENT_MASTER_URL, ttl_seconds: int = 86400):
        self.url = url
        self.ttl_seconds = ttl_seconds
        self.loaded_at = 0.0
        self.items: list[FNOUnderlying] = []

    def load(self, force: bool = False) -> list[FNOUnderlying]:
        if self.items and not force and time.time() - self.loaded_at < self.ttl_seconds:
            return self.items
        try:
            response = httpx.get(self.url, timeout=30, follow_redirects=True)
            response.raise_for_status()
            items = parse_fno_instrument_csv(response.text)
        except (httpx.HTTPError, csv.Error, UnicodeError) as exc:
            raise FNOInstrumentMasterError(f"Unable to load Dhan F&O instrument master: {exc}") from exc
        if not items:
            raise FNOInstrumentMasterError("Dhan F&O instrument master returned no active NSE option underlyings")
        self.items = items
        self.loaded_at = time.time()
        return self.items

    def search(self, q: str, limit: int = 20) -> list[FNOUnderlying]:
        query = " ".join(q.strip().upper().split())
        if len(query) < 2:
            return []
        items = self.load()
        exact = [item for item in items if item.symbol == query]
        starts = [
            item
            for item in items
            if item.symbol != query and (item.symbol.startswith(query) or item.name.upper().startswith(query))
        ]
        contains = [
            item
            for item in items
            if item.symbol != query and item not in starts and (query in item.symbol or query in item.name.upper())
        ]
        return (exact + starts + contains)[: max(1, min(limit, 50))]


fno_instrument_master = FNOInstrumentMaster()
