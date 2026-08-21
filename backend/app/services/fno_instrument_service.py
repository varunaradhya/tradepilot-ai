from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass

import httpx

from app.services.instrument_master_service import INSTRUMENT_MASTER_URL

DETAILED_INSTRUMENT_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"


@dataclass(frozen=True)
class FNOUnderlying:
    security_id: str
    exchange_segment: str
    symbol: str
    name: str


class FNOInstrumentMaster:
    def __init__(self, url=INSTRUMENT_MASTER_URL, ttl_seconds=86400):
        self.url = url
        self.ttl_seconds = ttl_seconds
        self.loaded_at = 0.0
        self.items = []
        self.option_loaded_at = 0.0
        self.option_rows: list[dict[str, str]] = []

    def load(self, force=False):
        if self.items and not force and time.time() - self.loaded_at < self.ttl_seconds:
            return self.items
        r = httpx.get(self.url, timeout=30)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        out = []
        seen = set()
        for row in reader:
            exchange = (row.get("SEM_EXM_EXCH_ID") or row.get("EXCH_ID") or "").strip().upper()
            segment = (row.get("SEM_SEGMENT") or row.get("SEGMENT") or "").strip().upper()
            instrument = (row.get("SEM_INSTRUMENT_NAME") or row.get("INSTRUMENT") or "").strip().upper()
            sid = (row.get("SEM_SMST_SECURITY_ID") or row.get("SEM_SECURITY_ID") or row.get("SECURITY_ID") or "").strip()
            symbol = (row.get("SEM_TRADING_SYMBOL") or row.get("SYMBOL_NAME") or "").strip().upper()
            name = (row.get("SEM_CUSTOM_SYMBOL") or row.get("DISPLAY_NAME") or symbol).strip()
            if exchange != "NSE" or segment != "I" or not sid or not symbol or symbol in seen:
                continue
            if "INDEX" not in instrument:
                continue
            seen.add(symbol)
            out.append(FNOUnderlying(sid, "IDX_I", symbol, name or symbol))
        self.items = out
        self.loaded_at = time.time()
        return out

    def _load_options(self, force=False) -> list[dict[str, str]]:
        if self.option_rows and not force and time.time() - self.option_loaded_at < self.ttl_seconds:
            return self.option_rows
        r = httpx.get(DETAILED_INSTRUMENT_MASTER_URL, timeout=30)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        rows = []
        for row in reader:
            exchange = (row.get("EXCH_ID") or row.get("SEM_EXM_EXCH_ID") or "").strip().upper()
            segment = (row.get("SEGMENT") or row.get("SEM_SEGMENT") or "").strip().upper()
            instrument = (row.get("INSTRUMENT") or row.get("SEM_INSTRUMENT_NAME") or "").strip().upper()
            if exchange == "NSE" and segment == "D" and instrument in {"OPTIDX", "OPTSTK"}:
                rows.append(row)
        if not rows:
            raise RuntimeError("Dhan instrument master returned no NSE option contracts")
        self.option_rows = rows
        self.option_loaded_at = time.time()
        return rows

    def option_lot_size(self, underlying: str, expiry: str, strike: float, option_type: str, security_id: str | int | None = None) -> int:
        target_underlying = underlying.strip().upper()
        target_expiry = expiry.strip()[:10]
        target_type = option_type.strip().upper()
        target_strike = float(strike)
        for row in self._load_options():
            row_underlying = (row.get("UNDERLYING_SYMBOL") or row.get("SYMBOL_NAME") or row.get("SM_SYMBOL_NAME") or "").strip().upper()
            row_expiry = (row.get("SM_EXPIRY_DATE") or row.get("SEM_EXPIRY_DATE") or row.get("EXPIRY_DATE") or "").strip()[:10]
            row_type = (row.get("OPTION_TYPE") or row.get("SEM_OPTION_TYPE") or "").strip().upper()
            row_sid = (row.get("SECURITY_ID") or row.get("SEM_SMST_SECURITY_ID") or "").strip()
            try:
                row_strike = float(row.get("STRIKE_PRICE") or row.get("SEM_STRIKE_PRICE") or 0)
                lot = int(float(row.get("LOT_SIZE") or row.get("SEM_LOT_UNITS") or 0))
            except (TypeError, ValueError):
                continue
            if security_id is not None and row_sid == str(security_id) and lot > 0:
                return lot
            if row_underlying == target_underlying and row_expiry == target_expiry and row_type == target_type and abs(row_strike - target_strike) < 1e-6 and lot > 0:
                return lot
        return 0

    def search(self, q, limit=20):
        q = q.strip().upper()
        if not q:
            return []
        items = self.load()
        exact = [x for x in items if x.symbol == q]
        rest = [x for x in items if x.symbol != q and (q in x.symbol or q in x.name.upper())]
        return (exact + rest)[: max(1, min(limit, 50))]


fno_instrument_master = FNOInstrumentMaster()
