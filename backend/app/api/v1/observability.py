from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import TRADEPILOT_LIVE_EXECUTION_ENABLED
from app.db.database import engine, get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.kill_switch_service import kill_switch_status
from app.services.market_data_health import evaluate_market_data_freshness
from app.services.observability import OBSERVABILITY, slo_snapshot
from app.services.paper_session_state_service import load_paper_session_state

router = APIRouter(prefix="/observability", tags=["Observability"])


def _market_timestamp(state: dict | None):
    from datetime import datetime
    value = (state or {}).get("last_bar_timestamp")
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


@router.get("/metrics")
def metrics(current_user: User = Depends(get_current_user)) -> dict:
    """Read-only application telemetry suitable for a metrics scraper."""
    return {"status": "ok", "metrics": OBSERVABILITY.snapshot()}


@router.get("/slo")
def slo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    state = load_paper_session_state(db, current_user.id)
    market = evaluate_market_data_freshness(_market_timestamp(state))
    switch = kill_switch_status(db)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_available = True
    except Exception:
        database_available = False
    result = slo_snapshot(
        database_available=database_available,
        market_data_fresh=market.fresh,
        kill_switch_active=switch["active"],
    )
    result["live_execution_config"] = bool(TRADEPILOT_LIVE_EXECUTION_ENABLED)
    # A configuration flag can never unlock live execution in P6.
    result["live_execution_enabled"] = False
    return result
