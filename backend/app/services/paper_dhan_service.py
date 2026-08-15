from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.brokers.dhan import DhanClient
from app.services.broker_service import get_access_token, get_user_broker
from app.services.dhan_historical_service import HistoricalRequest, fetch_intraday_history
from app.services.instrument_master_service import InstrumentMaster, instrument_master
from app.services.paper_market_service import PaperMarketCoordinator


def run_dhan_paper_session(
    db,
    user_id: int,
    symbol: str,
    session: str,
    interval: str = "5",
    master: InstrumentMaster = instrument_master,
    coordinator: PaperMarketCoordinator | None = None,
) -> dict[str, Any]:
    connection = get_user_broker(db, user_id, "DHAN")
    if connection is None:
        raise ValueError("Dhan is not connected")
    if interval not in {"1", "5", "15", "25", "60"}:
        raise ValueError("interval must be 1, 5, 15, 25, or 60 minutes")

    try:
        trading_day = date.fromisoformat(session)
    except ValueError as exc:
        raise ValueError("session must be YYYY-MM-DD") from exc

    needle = symbol.strip().upper()
    matches = [item for item in master.load() if item.symbol.upper() == needle and item.exchange_segment == "NSE_EQ"]
    if not matches:
        raise ValueError(f"NSE equity symbol not found: {needle}")
    instrument = matches[0]

    client = DhanClient(connection.client_id, get_access_token(connection))
    bars, diagnostics = fetch_intraday_history(
        client,
        HistoricalRequest(
            security_id=instrument.security_id,
            exchange_segment=instrument.exchange_segment,
            instrument="EQUITY",
            interval=interval,
        ),
        trading_day,
        trading_day + timedelta(days=1),
    )

    runner = coordinator or PaperMarketCoordinator()
    processed = 0
    buys = 0
    last_result: dict[str, Any] | None = None
    for bar in bars:
        last_result = runner.on_bar(
            session=session,
            symbol=instrument.symbol,
            open_price=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=float(bar.volume or 0),
        )
        processed += 1
        if last_result.get("execution", {}).get("accepted"):
            buys += 1

    return {
        "mode": "SIMULATION_ONLY",
        "symbol": instrument.symbol,
        "interval": interval,
        "processed_bars": processed,
        "buy_entries": buys,
        "dataset_valid": diagnostics["valid"],
        "diagnostics": diagnostics,
        "last": last_result,
    }
