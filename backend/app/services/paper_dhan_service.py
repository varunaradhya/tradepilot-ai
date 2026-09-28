from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
from typing import Any

from app.brokers.dhan import DhanClient
from app.models.paper_historical_run import PaperHistoricalRun
from app.models.paper_trade import PaperTrade
from app.services.broker_service import get_access_token, get_user_broker
from app.services.dhan_historical_service import HistoricalRequest, fetch_intraday_history
from app.services.instrument_master_service import InstrumentMaster, instrument_master
from app.services.paper_market_service import PaperMarketCoordinator
from app.services.paper_ml_service import record_trade_outcome


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
    if not diagnostics["valid"]:
        raise ValueError(f"Historical dataset failed validation: {diagnostics.get('message', 'invalid dataset')}")

    if not bars:
        return {
            "mode": "SIMULATION_ONLY",
            "symbol": instrument.symbol,
            "interval": interval,
            "processed_bars": 0,
            "buy_entries": 0,
            "persisted_trades": 0,
            "dataset_valid": diagnostics["valid"],
            "diagnostics": diagnostics,
            "last": None,
        }

    runner = coordinator or PaperMarketCoordinator()
    # A Dhan session is a self-contained historical simulation. Resetting here
    # prevents repeated button presses from appending to a previous run.
    runner.reset()
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

    # Intraday positions must not remain open after the historical session.
    last_close = float(bars[-1].close)
    runner.close_session(session, instrument.symbol, last_close)

    marker = f"DHAN:{session}:{interval}"
    strategy_version = "V1"

    try:
        db.add(
            PaperHistoricalRun(
                user_id=user_id,
                symbol=instrument.symbol,
                session=session,
                interval=interval,
                strategy_version=strategy_version,
            )
        )
        db.flush()
    except IntegrityError:
        db.rollback()
        return {
            "mode": "SIMULATION_ONLY",
            "symbol": instrument.symbol,
            "interval": interval,
            "processed_bars": processed,
            "buy_entries": buys,
            "persisted_trades": 0,
            "dataset_valid": diagnostics["valid"],
            "diagnostics": diagnostics,
            "last": last_result,
            "paper": runner.orchestrator.summary(),
            "idempotent_replay": True,
        }

    persisted = 0
    for trade in runner.orchestrator.trades():
        record_trade_outcome(db, user_id, session, trade, strategy_version=strategy_version, model_version=str(trade.get("model_version") or "RULES_V1"))
        record = PaperTrade(
            user_id=user_id,
            symbol=instrument.symbol,
            side="BUY",
            status="CLOSED",
            quantity=int(trade["quantity"]),
            entry_price=float(trade["entry"]),
            stop_price=float(trade["stop"]),
            target_price=float(trade["target"]),
            exit_price=float(trade["exit"]),
            pnl=float(trade["pnl"]),
            reason=marker,
            strategy_version=strategy_version,
        )
        db.add(record)
        persisted += 1

    db.commit()


    return {
        "mode": "SIMULATION_ONLY",
        "symbol": instrument.symbol,
        "interval": interval,
        "processed_bars": processed,
        "buy_entries": buys,
        "persisted_trades": persisted,
        "dataset_valid": diagnostics["valid"],
        "diagnostics": diagnostics,
        "last": last_result,
        "paper": runner.orchestrator.summary(),
    }
