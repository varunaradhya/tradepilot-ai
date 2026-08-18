from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.paper_trade import PaperTrade
from app.services.paper_monitoring import PaperMonitoringThresholds, build_paper_monitoring_snapshot
from app.services.paper_session_state_service import load_paper_session_state

router = APIRouter(prefix="/paper-monitoring", tags=["Paper Monitoring"])


@router.get("/health")
def paper_monitoring_health(
    strategy_version: str | None = Query(default=None, pattern="^(V1|V2)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(PaperTrade).filter(PaperTrade.user_id == current_user.id)
    trades = query.all()
    if strategy_version:
        trades = [trade for trade in trades if trade.strategy_version == strategy_version]
    state = load_paper_session_state(db, current_user.id)
    return build_paper_monitoring_snapshot(
        trades,
        state,
        PaperMonitoringThresholds(),
    )
