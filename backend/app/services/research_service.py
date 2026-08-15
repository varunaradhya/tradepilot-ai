from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.brokers.dhan import DhanClient
from app.services.dhan_historical_service import HistoricalRequest, fetch_daily_history
from app.services.instrument_master_service import IndianInstrument, InstrumentMaster, instrument_master
from app.services.research_store import ResearchStore, research_store


@dataclass(frozen=True)
class ResearchDatasetResult:
    symbol: str
    dataset: str
    bars: int
    start: str | None
    end: str | None
    valid: bool


def resolve_indian_symbol(symbol: str, master: InstrumentMaster = instrument_master) -> IndianInstrument:
    needle = symbol.strip().upper()
    if not needle:
        raise ValueError("Symbol is required")
    matches = [item for item in master.load() if item.symbol.upper() == needle]
    if not matches:
        raise ValueError(f"NSE equity symbol not found: {needle}")
    return matches[0]


def download_daily_dataset(
    client: DhanClient,
    symbol: str,
    start: date,
    end: date,
    master: InstrumentMaster = instrument_master,
    store: ResearchStore = research_store,
) -> ResearchDatasetResult:
    if start >= end:
        raise ValueError("start must be before end")
    instrument = resolve_indian_symbol(symbol, master)
    bars, diagnostics = fetch_daily_history(
        client,
        HistoricalRequest(
            security_id=instrument.security_id,
            exchange_segment=instrument.exchange_segment,
            instrument="EQUITY",
        ),
        start,
        end,
    )
    dataset = f"nse/{instrument.symbol}_daily"
    store.save(dataset, bars)
    return ResearchDatasetResult(
        symbol=instrument.symbol,
        dataset=dataset,
        bars=diagnostics["bars"],
        start=diagnostics.get("start"),
        end=diagnostics.get("end"),
        valid=diagnostics["valid"],
    )
