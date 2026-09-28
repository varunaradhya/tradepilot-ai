from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.brokers.dhan import DhanClient
from app.services.dhan_historical_service import HistoricalRequest, fetch_intraday_history
from app.services.instrument_master_service import InstrumentMaster, InstrumentMasterError, instrument_master
from app.services.research_store import ResearchStore, research_store


@dataclass(frozen=True)
class BenchmarkDatasetResult:
    benchmark: str
    interval: str
    dataset: str
    security_id: str
    bars: int
    start: str | None
    end: str | None
    valid: bool


def download_intraday_benchmark_dataset(
    client: DhanClient,
    benchmark: str,
    start: date,
    end: date,
    interval: str = "5",
    master: InstrumentMaster = instrument_master,
    store: ResearchStore = research_store,
) -> BenchmarkDatasetResult:
    if start >= end:
        raise ValueError("start must be before end")
    if interval not in {"1", "5", "15", "25", "60"}:
        raise ValueError("interval must be 1, 5, 15, 25, or 60 minutes")

    needle = benchmark.strip().upper()
    matches = master.index_lookup(needle)
    if not matches:
        raise InstrumentMasterError(f"NSE index not found: {needle}")
    if len(matches) > 1:
        exact = [item for item in matches if item.symbol.upper() == needle]
        if len(exact) == 1:
            instrument = exact[0]
        else:
            raise ValueError(f"Multiple NSE index matches found for: {needle}")
    else:
        instrument = matches[0]

    bars, diagnostics = fetch_intraday_history(
        client,
        HistoricalRequest(
            security_id=instrument.security_id,
            exchange_segment="IDX_I",
            instrument="INDEX",
            interval=interval,
        ),
        start,
        end,
    )

    dataset = f"benchmark/{instrument.symbol}_intraday_{interval}m"
    store.merge(dataset, bars)
    return BenchmarkDatasetResult(
        benchmark=instrument.symbol,
        interval=interval,
        dataset=dataset,
        security_id=instrument.security_id,
        bars=diagnostics["bars"],
        start=diagnostics.get("start"),
        end=diagnostics.get("end"),
        valid=diagnostics["valid"],
    )
