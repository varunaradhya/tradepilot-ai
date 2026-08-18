from typing import Any

from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.market_session_scheduler import scheduler_status

router = APIRouter(prefix="/market-scheduler", tags=["Market Scheduler"])


@router.get("/status")
def market_scheduler_status(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return scheduler_status()
