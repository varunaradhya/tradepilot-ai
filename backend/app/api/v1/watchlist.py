from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistQuote,
    WatchlistResponse,
)
from app.services.market_service import (
    MarketDataProviderError,
    get_quote,
)
from app.services.watchlist_service import (
    add_watchlist_symbol,
    delete_watchlist_symbol,
    get_watchlist,
)


router = APIRouter(
    prefix="/watchlist",
    tags=["Watchlist"],
)


@router.post(
    "",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_symbol(
    data: WatchlistCreate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    return add_watchlist_symbol(
        db=db,
        user_id=current_user.id,
        symbol=data.symbol,
    )


@router.get(
    "",
    response_model=list[WatchlistResponse],
)
def list_symbols(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    return get_watchlist(
        db,
        current_user.id,
    )


@router.get(
    "/quotes",
    response_model=list[WatchlistQuote],
)
def watchlist_quotes(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    items = get_watchlist(
        db,
        current_user.id,
    )

    results = []

    for item in items:

        try:

            quote = get_quote(
                item.symbol
            )

            results.append(
                {
                    "id": item.id,
                    "symbol": item.symbol,
                    "price": float(
                        quote.price
                    ),
                    "change": float(
                        getattr(
                            quote,
                            "change",
                            0,
                        )
                    ),
                    "change_percent": float(
                        getattr(
                            quote,
                            "change_percent",
                            0,
                        )
                    ),
                }
            )

        except MarketDataProviderError:

            results.append(
                {
                    "id": item.id,
                    "symbol": item.symbol,
                    "price": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                }
            )

    return results


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_symbol(
    item_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    deleted = delete_watchlist_symbol(
        db,
        current_user.id,
        item_id,
    )

    if not deleted:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        )

    return None
