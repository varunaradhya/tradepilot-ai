from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.production_safety import build_operational_snapshot
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.broker_connection import BrokerConnection
from app.models.paper_trade import PaperTrade
from app.models.user import User
from app.services.broker_sandbox import certify_broker_adapter
from app.services.kill_switch_service import activate_kill_switch, kill_switch_status
from app.services.market_data_health import evaluate_market_data_freshness
from app.services.market_session_scheduler import scheduler_status
from app.services.operational_audit import list_recent_events, record_event
from app.services.paper_monitoring import PaperMonitoringThresholds, build_paper_monitoring_snapshot
from app.services.paper_session_state_service import load_paper_session_state

router = APIRouter(prefix="/operations", tags=["Operations"])


class KillSwitchRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


def _last_bar_timestamp(state: dict[str, Any] | None) -> datetime | None:
    value = (state or {}).get("last_bar_timestamp")
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


@router.get("/safety")
def safety_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Read-only production safety status; it cannot enable execution."""
    state = load_paper_session_state(db, current_user.id)
    trades = db.query(PaperTrade).filter(PaperTrade.user_id == current_user.id).all()
    monitoring = build_paper_monitoring_snapshot(trades, state, PaperMonitoringThresholds())
    market_data = evaluate_market_data_freshness(_last_bar_timestamp(state))
    switch = kill_switch_status(db)
    broker_connected = db.query(BrokerConnection).filter(
        BrokerConnection.user_id == current_user.id,
        BrokerConnection.status == "CONNECTED",
    ).count() > 0
    snapshot = build_operational_snapshot(
        market_data_fresh=market_data.fresh,
        reconciliation_healthy=not bool(monitoring["safety"]["halt_required"]),
        strategy_ready=False,
        risk_limits_healthy=False,
        broker_connected=broker_connected,
        kill_switch_active=switch["active"],
    )
    return {
        **snapshot.as_dict(),
        "market_session": scheduler_status(),
        "market_data": market_data.as_dict(),
        "paper_monitoring": {
            "status": monitoring["status"],
            "mismatch_count": monitoring["safety"]["mismatch_count"],
        },
        "kill_switch": switch,
        "manual_unlock_required": True,
        "live_execution_enabled": False,
    }


@router.get("/kill-switch")
def get_kill_switch(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return kill_switch_status(db)


@router.post("/kill-switch/activate")
def activate_kill_switch_endpoint(
    data: KillSwitchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    switch = activate_kill_switch(db, reason=data.reason, user_id=current_user.id)
    record_event(db, "KILL_SWITCH_ACTIVATED", severity="CRITICAL", user_id=current_user.id, payload={"reason": switch.reason})
    return kill_switch_status(db)


@router.get("/audit-events")
def audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"events": list_recent_events(db, limit=limit)}


@router.get("/broker-sandbox/{broker_name}")
def broker_sandbox_certification(
    broker_name: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    result = certify_broker_adapter(broker_name)
    if result.get("reason") == "UNSUPPORTED_BROKER":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result)
    return result
