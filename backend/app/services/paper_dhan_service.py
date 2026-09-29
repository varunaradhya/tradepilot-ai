from __future__ import annotations

from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError
from typing import Any

from app.brokers.dhan import DhanClient
from app.models.paper_historical_run import PaperHistoricalRun
from app.models.paper_trade import PaperTrade
from app.services.broker_service import get_access_token, get_user_broker
from app.services.dhan_historical_service import HistoricalRequest, fetch_intraday_history
from app.services.instrument_master_service import InstrumentMaster, instrument_master, resolve_nse_equity
from app.services.paper_market_service import PaperMarketCoordinator
from app.services.paper_ml_service import record_trade_outcome
from app.services.paper_validation_service import (
    validation_run_key, record_validation_day, record_validation_symbol,
    complete_validation_day,
)

def run_dhan_paper_session(
    db, user_id: int, symbol: str, session: str, interval: str = "5",
    master: InstrumentMaster = instrument_master,
    coordinator: PaperMarketCoordinator | None = None,
    finalize_validation: bool = True,
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

    instrument = resolve_nse_equity(master, symbol)
    client = DhanClient(connection.client_id, get_access_token(connection))
    run_key = validation_run_key(trading_day)

    try:
        bars, diagnostics = fetch_intraday_history(
            client,
            HistoricalRequest(security_id=instrument.security_id, exchange_segment=instrument.exchange_segment, instrument="EQUITY", interval=interval),
            trading_day, trading_day + timedelta(days=1),
        )
    except Exception as exc:
        db.rollback()
        record_validation_symbol(db, user_id, run_key, trading_day, instrument.symbol, "OPERATIONAL_FAILURE", 0, 0, 0.0, {"valid": False, "provider_errors": 1, "error_type": type(exc).__name__})
        if finalize_validation:
            record_validation_day(db, user_id, run_key, trading_day, "OPERATIONAL_FAILURE", 0, 0.0, {"valid": False, "provider_errors": 1, "symbols": [instrument.symbol]})
        raise

    if not diagnostics["valid"]:
        record_validation_symbol(db, user_id, run_key, trading_day, instrument.symbol, "DATA_QUALITY_FAILED", len(bars), 0, 0.0, diagnostics)
        if finalize_validation:
            record_validation_day(db, user_id, run_key, trading_day, "DATA_QUALITY_FAILED", 0, 0.0, diagnostics)
        raise ValueError(f"Historical dataset failed validation: {diagnostics.get('message', 'invalid dataset')}")

    if not bars:
        record_validation_symbol(db, user_id, run_key, trading_day, instrument.symbol, "NO_DATA", 0, 0, 0.0, diagnostics)
        if finalize_validation:
            record_validation_day(db, user_id, run_key, trading_day, "NO_DATA", 0, 0.0, diagnostics)
        return {"mode": "SIMULATION_ONLY", "symbol": instrument.symbol, "interval": interval, "processed_bars": 0, "buy_entries": 0, "persisted_trades": 0, "dataset_valid": diagnostics["valid"], "diagnostics": diagnostics, "last": None}

    runner = coordinator or PaperMarketCoordinator()
    runner.reset()
    processed = 0
    buys = 0
    last_result: dict[str, Any] | None = None
    for bar in bars:
        last_result = runner.on_bar(session=session, symbol=instrument.symbol, open_price=bar.open, high=bar.high, low=bar.low, close=bar.close, volume=float(bar.volume or 0))
        processed += 1
        if last_result.get("execution", {}).get("accepted"):
            buys += 1
    runner.close_session(session, instrument.symbol, float(bars[-1].close))

    strategy_version = "V1"
    try:
        db.add(PaperHistoricalRun(user_id=user_id, symbol=instrument.symbol, session=session, interval=interval, strategy_version=strategy_version))
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(PaperTrade).filter(PaperTrade.user_id == user_id, PaperTrade.symbol == instrument.symbol, PaperTrade.reason == f"DHAN:{session}:{interval}", PaperTrade.status == "CLOSED").all()
        pnl = sum(float(t.pnl or 0) for t in existing)
        trades = len(existing)
        symbol_row = record_validation_symbol(db, user_id, run_key, trading_day, instrument.symbol, "COMPLETE", len(bars), trades, pnl, diagnostics)
        return {
            "mode": "SIMULATION_ONLY", "symbol": instrument.symbol, "interval": interval, "processed_bars": processed,
            "buy_entries": buys, "persisted_trades": trades, "dataset_valid": diagnostics["valid"], "diagnostics": diagnostics,
            "last": last_result, "idempotent_replay": True,
            "validation": {"run": run_key, "status": symbol_row.status, "trades": symbol_row.trades, "net_pnl": symbol_row.net_pnl},
        }

    persisted = 0
    total_pnl = 0.0
    for trade in runner.orchestrator.trades():
        learning_event = record_trade_outcome(db, user_id, session, trade, strategy_version=strategy_version, model_version=str(trade.get("model_version") or "RULES_V1"), commit=False)
        db.flush()
        db.add(PaperTrade(
            user_id=user_id, symbol=instrument.symbol, side="BUY", status="CLOSED",
            learning_event_id=learning_event.id,
            quantity=int(trade["quantity"]), entry_price=float(trade["entry"]), stop_price=float(trade["stop"]),
            target_price=float(trade["target"]), exit_price=float(trade["exit"]), pnl=float(trade["pnl"]),
            reason=f"DHAN:{session}:{interval}", strategy_version=strategy_version,
        ))
        persisted += 1
        total_pnl += float(trade["pnl"])

    db.commit()
    symbol_row = record_validation_symbol(db, user_id, run_key, trading_day, instrument.symbol, "COMPLETE", len(bars), persisted, total_pnl, diagnostics)
    validation = complete_validation_day(db, user_id, run_key, trading_day, diagnostics) if finalize_validation else symbol_row

    return {
        "mode": "SIMULATION_ONLY", "symbol": instrument.symbol, "interval": interval, "processed_bars": processed,
        "buy_entries": buys, "persisted_trades": persisted, "dataset_valid": diagnostics["valid"], "diagnostics": diagnostics,
        "last": last_result, "paper": runner.orchestrator.summary(),
        "validation": {"run": run_key, "status": validation.status, "trades": validation.trades, "net_pnl": validation.net_pnl},
    }
