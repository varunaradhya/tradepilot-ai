from __future__ import annotations

from datetime import date
from typing import Any

from app.brokers.dhan import DhanClient
from app.services.broker_service import get_access_token, get_user_broker
from app.services.instrument_master_service import instrument_master, InstrumentMaster


def mark_dhan_paper_position(db, user_id: int, orchestrator, master: InstrumentMaster = instrument_master) -> dict[str, Any]:
    """Fetch one real-time Dhan LTP and mark the simulation position.

    This endpoint is read-only with respect to Dhan: it calls Market Quote LTP
    only and never calls an order API.
    """
    snapshot = orchestrator.summary()
    position = snapshot.get("open_position")
    if not position:
        return {"mode": "SIMULATION_ONLY", "market_connected": False, "reason": "NO_OPEN_PAPER_POSITION", "paper": snapshot}
    symbol = str(position.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("Open paper position has no symbol")
    matches = [x for x in master.load() if x.symbol.upper() == symbol and x.exchange_segment == "NSE_EQ"]
    if not matches:
        raise ValueError(f"NSE equity symbol not found: {symbol}")
    instrument = matches[0]
    connection = get_user_broker(db, user_id, "DHAN")
    if connection is None:
        raise ValueError("Dhan is not connected")
    client = DhanClient(connection.client_id, get_access_token(connection), max_retries=2)
    payload = client.market_ltp("NSE_EQ", [instrument.security_id])
    data = payload.get("data", {}).get("NSE_EQ", {})
    quote = data.get(str(instrument.security_id)) or data.get(instrument.security_id)
    if not quote or float(quote.get("last_price") or 0) <= 0:
        raise ValueError(f"Dhan returned no valid LTP for {symbol}")
    ltp = float(quote["last_price"])
    result = orchestrator.on_tick(date.today().isoformat(), ltp)
    return {
        "mode": "SIMULATION_ONLY",
        "market_connected": True,
        "source": "DHAN_MARKETFEED_LTP",
        "symbol": symbol,
        "security_id": instrument.security_id,
        "ltp": ltp,
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "execution": result,
        "paper": orchestrator.summary(),
        "real_orders_enabled": False,
    }
