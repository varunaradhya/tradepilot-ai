from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.intraday_strategy import generate_intraday_signal

router = APIRouter(prefix="/intraday", tags=["Intraday Research"])


@router.post("/signal")
def intraday_signal(payload: dict, current_user: User = Depends(get_current_user)):
    del current_user
    try:
        return generate_intraday_signal(
            payload["opens"], payload["highs"], payload["lows"], payload["closes"], payload["volumes"],
            payload.get("opening_high"), payload.get("opening_low"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
