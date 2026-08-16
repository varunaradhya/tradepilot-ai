from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.watchlist import WatchlistCreate, WatchlistQuote, WatchlistResponse
from app.services.market_service import MarketDataProviderError, get_quote
from app.services.watchlist_service import (
    WatchlistSymbolError,
    add_watchlist_symbol,
    delete_watchlist_symbol,
    get_watchlist,
)

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def add_symbol(
    data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return add_watchlist_symbol(db=db, user_id=current_user.id, symbol=data.symbol)
    except WatchlistSymbolError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[WatchlistResponse])
def list_symbols(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_watchlist(db, current_user.id)


@router.get("/quotes", response_model=list[WatchlistQuote])
def watchlist_quotes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = []
    for item in get_watchlist(db, current_user.id):
        try:
            quote = get_quote(item.symbol)
            results.append(
                {
                    "id": item.id,
                    "symbol": item.symbol,
                    "price": float(quote.price),
                    "change": float(quote.change) if quote.change is not None else None,
                    "change_percent": float(quote.change_percent) if quote.change_percent is not None else None,
                    "market_data_available": True,
                }
            )
        except MarketDataProviderError:
            results.append(
                {
                    "id": item.id,
                    "symbol": item.symbol,
                    "price": None,
                    "change": None,
                    "change_percent": None,
                    "market_data_available": False,
                }
            )
    return results


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_symbol(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = delete_watchlist_symbol(db, current_user.id, item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")
    return None
