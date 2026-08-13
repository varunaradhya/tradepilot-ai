from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.signals import SignalResponse
from app.services.market_service import MarketDataProviderError, get_history
from app.services.signal_service import generate_signal

router = APIRouter(prefix="/signals", tags=["TradePilot Signals"])


def _normalize_history(history) -> list[dict]:
    return [
        {
            "close": float(row["close"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "volume": float(row["volume"]) if row.get("volume") is not None else None,
        }
        for row in history.data
        if row.get("close") is not None and row.get("high") is not None and row.get("low") is not None
    ]


@router.get("/technical", response_model=SignalResponse)
def technical_signal(
    symbol: str = Query(min_length=1, max_length=30),
    current_user: User = Depends(get_current_user),
):
    del current_user

    try:
        history = get_history(symbol.upper(), range_="6mo", interval="1d")
    except MarketDataProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Market data provider error: {exc}",
        ) from exc

    rows = _normalize_history(history)

    closes = [row["close"] for row in rows]
    highs = [row["high"] for row in rows]
    lows = [row["low"] for row in rows]
    volumes = [row["volume"] for row in rows]

    return generate_signal(
        symbol.upper(),
        closes,
        highs,
        lows,
        volumes if all(volume is not None for volume in volumes) else None,
    )
