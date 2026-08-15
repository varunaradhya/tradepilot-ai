from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.brokers.dhan import DhanClient
from app.services.dhan_historical_service import HistoricalRequest, fetch_intraday_history
from app.services.instrument_master_service import InstrumentMaster, instrument_master
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.research_store import ResearchStore, research_store


@dataclass(frozen=True)
class IntradayDatasetResult:
    symbol: str
    interval: str
    dataset: str
    bars: int
    start: str | None
    end: str | None
    valid: bool


def download_intraday_dataset(
    client: DhanClient,
    symbol: str,
    start: date,
    end: date,
    interval: str = "5",
    master: InstrumentMaster = instrument_master,
    store: ResearchStore = research_store,
) -> IntradayDatasetResult:
    if start >= end:
        raise ValueError("start must be before end")
    if interval not in {"1", "5", "15", "25", "60"}:
        raise ValueError("interval must be 1, 5, 15, 25, or 60 minutes")
    needle = symbol.strip().upper()
    matches = [item for item in master.load() if item.symbol.upper() == needle]
    if not matches:
        raise ValueError(f"NSE equity symbol not found: {needle}")
    instrument = matches[0]
    bars, diagnostics = fetch_intraday_history(
        client,
        HistoricalRequest(
            security_id=instrument.security_id,
            exchange_segment=instrument.exchange_segment,
            instrument="EQUITY",
            interval=interval,
        ),
        start,
        end,
    )
    dataset = f"nse/{instrument.symbol}_intraday_{interval}m"
    store.save(dataset, bars)
    return IntradayDatasetResult(
        symbol=instrument.symbol,
        interval=interval,
        dataset=dataset,
        bars=diagnostics["bars"],
        start=diagnostics.get("start"),
        end=diagnostics.get("end"),
        valid=diagnostics["valid"],
    )


def backtest_intraday_dataset(
    symbol: str,
    interval: str = "5",
    store: ResearchStore = research_store,
    config: IntradayBacktestConfig = IntradayBacktestConfig(),
) -> dict:
    dataset = f"nse/{symbol.strip().upper()}_intraday_{interval}m"
    bars = store.load(dataset)
    if not bars:
        raise ValueError(f"Intraday dataset not found: {dataset}")
    rows = []
    for bar in bars:
        row = bar.as_row()
        timestamp = row["timestamp"]
        row["session"] = timestamp.date().isoformat()
        rows.append(row)
    result = run_intraday_backtest(rows, config)
    return {"symbol": symbol.strip().upper(), "interval": interval, "dataset": dataset, **result}
