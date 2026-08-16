from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist
from app.services.instrument_service import IndianSymbolError, canonical_indian_symbol


class WatchlistSymbolError(ValueError):
    """Raised when a watchlist symbol is not an Indian listed equity."""


def add_watchlist_symbol(
    db: Session,
    user_id: int,
    symbol: str,
):
    try:
        symbol = canonical_indian_symbol(symbol)
    except IndianSymbolError as exc:
        raise WatchlistSymbolError(str(exc)) from exc

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

    item = Watchlist(user_id=user_id, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_watchlist(db: Session, user_id: int):
    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id)
        .order_by(Watchlist.symbol.asc())
        .all()
    )


def get_watchlist_item(db: Session, user_id: int, item_id: int):
    return (
        db.query(Watchlist)
        .filter(Watchlist.id == item_id, Watchlist.user_id == user_id)
        .first()
    )


def delete_watchlist_symbol(db: Session, user_id: int, item_id: int):
    item = get_watchlist_item(db, user_id, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
