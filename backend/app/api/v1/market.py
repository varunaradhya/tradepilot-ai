from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.market import HistoryResponse, QuoteResponse
from app.services.market_service import (
    MarketDataProviderError,
    get_history,
    get_quote,
)

router = APIRouter(
    prefix="/market",
    tags=["Market Data"],
)


@router.get(
    "/quote/{symbol}",
    response_model=QuoteResponse,
)
def market_quote(symbol: str):
    try:
        quote = get_quote(symbol)

    except MarketDataProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return QuoteResponse(
        symbol=quote.symbol,
        name=quote.name,
        currency=quote.currency,
        exchange=quote.exchange,
        price=quote.price,
        previous_close=quote.previous_close,
        change=quote.change,
        change_percent=quote.change_percent,
        market_time=quote.market_time,
    )


@router.get(
    "/history/{symbol}",
    response_model=HistoryResponse,
)
def market_history(
    symbol: str,
    range_: str = Query(
        default="1mo",
        alias="range",
    ),
    interval: str = Query(
        default="1d",
    ),
):
    allowed_ranges = {
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    }

    allowed_intervals = {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }

    if range_ not in allowed_ranges:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid range",
        )

    if interval not in allowed_intervals:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid interval",
        )

    try:
        history = get_history(
            symbol=symbol,
            range_=range_,
            interval=interval,
        )

    except MarketDataProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return HistoryResponse(
        symbol=history.symbol,
        currency=history.currency,
        interval=history.interval,
        range=history.range,
        data=history.data,
    )
