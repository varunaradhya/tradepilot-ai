from __future__ import annotations

from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.market_session_scheduler import scheduler_status
from app.core.production_safety import build_operational_snapshot

router = APIRouter(prefix="/operations", tags=["Operations"])


@router.get("/safety")
def safety_status(current_user: User = Depends(get_current_user)) -> dict:
    """Read-only production safety status; it cannot enable execution."""
    session = scheduler_status()
    snapshot = build_operational_snapshot(
        market_data_fresh=False,
        reconciliation_healthy=False,
        strategy_ready=False,
        risk_limits_healthy=False,
        broker_connected=False,
        kill_switch_active=True,
    )
    return {
        **snapshot.as_dict(),
        "market_session": session,
        "manual_unlock_required": True,
        "live_execution_enabled": False,
    }
