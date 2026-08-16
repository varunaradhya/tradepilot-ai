from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist
from app.services.market_service import search_instruments
from app.providers.market_search import MarketSearchProviderError


class WatchlistSymbolError(ValueError):
    """Raised when a watchlist symbol is not an Indian listed equity."""


def _canonical_indian_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise WatchlistSymbolError("Enter an Indian NSE/BSE equity symbol.")

    if normalized.endswith(".NS") or normalized.endswith(".BO"):
        normalized = normalized.rsplit(".", 1)[0]

    try:
        results = search_instruments(normalized)
    except MarketSearchProviderError as exc:
        raise WatchlistSymbolError(
            "Indian stock validation is temporarily unavailable. Please try again shortly."
        ) from exc

    exact = [item for item in results if item.symbol.upper() == normalized]
    if not exact:
        raise WatchlistSymbolError(
            f"{normalized} is not available in the Indian NSE/BSE equity universe."
        )

    # Prefer NSE when a symbol is listed on both exchanges.
    exact.sort(key=lambda item: 0 if item.exchange == "NSE" else 1)
    return exact[0].symbol.upper()


def add_watchlist_symbol(
    db: Session,
    user_id: int,
    symbol: str,
):
    symbol = _canonical_indian_symbol(symbol)

    existing = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == user_id,
            Watchlist.symbol == symbol,
        )
        .first()
    )

    if existing:
        return existing

    item = Watchlist(
        user_id=user_id,
        symbol=symbol,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def get_watchlist(
    db: Session,
    user_id: int,
):
    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id)
        .order_by(Watchlist.symbol.asc())
        .all()
    )


def get_watchlist_item(
    db: Session,
    user_id: int,
    item_id: int,
):
    return (
        db.query(Watchlist)
        .filter(
            Watchlist.id == item_id,
            Watchlist.user_id == user_id,
        )
        .first()
    )


def delete_watchlist_symbol(
    db: Session,
    user_id: int,
    item_id: int,
):
    item = get_watchlist_item(db, user_id, item_id)
    if item is None:
        return False

    db.delete(item)
    db.commit()
    return True
