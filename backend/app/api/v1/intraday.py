from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.intraday_strategy import generate_intraday_signal
from app.services.intraday_strategy_v2 import generate_intraday_v2_signal

router = APIRouter(prefix="/intraday", tags=["Intraday Research"])


def _series(payload: dict):
    return payload["opens"], payload["highs"], payload["lows"], payload["closes"], payload["volumes"]


@router.post("/signal")
def intraday_signal(payload: dict, current_user: User = Depends(get_current_user)):
    del current_user
    try:
        return generate_intraday_signal(*_series(payload), payload.get("opening_high"), payload.get("opening_low"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/signal/v2")
def intraday_signal_v2(payload: dict, current_user: User = Depends(get_current_user)):
    del current_user
    try:
        return generate_intraday_v2_signal(
            *_series(payload), payload.get("market_closes"), payload.get("sector_closes"),
            payload.get("opening_high"), payload.get("opening_low")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
