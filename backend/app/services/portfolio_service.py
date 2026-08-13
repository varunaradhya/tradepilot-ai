from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.holding import Holding


def get_user_holdings(
    db: Session,
    user_id: int,
) -> list[Holding]:
    statement = (
        select(Holding)
        .where(Holding.user_id == user_id)
        .order_by(Holding.id)
    )

    return list(
        db.execute(statement).scalars().all()
    )


def get_holding(
    db: Session,
    holding_id: int,
    user_id: int,
) -> Holding | None:
    statement = select(Holding).where(
        Holding.id == holding_id,
        Holding.user_id == user_id,
    )

    return db.execute(
        statement
    ).scalar_one_or_none()


def create_holding(
    db: Session,
    user_id: int,
    symbol: str,
    quantity: Decimal,
    average_buy_price: Decimal,
) -> Holding:

    holding = Holding(
        user_id=user_id,
        symbol=symbol.strip().upper(),
        quantity=quantity,
        average_buy_price=average_buy_price,
    )

    db.add(holding)
    db.commit()
    db.refresh(holding)

    return holding


def update_holding(
    db: Session,
    holding: Holding,
    symbol: str | None = None,
    quantity: Decimal | None = None,
    average_buy_price: Decimal | None = None,
) -> Holding:

    if symbol is not None:
        holding.symbol = symbol.strip().upper()

    if quantity is not None:
        holding.quantity = quantity

    if average_buy_price is not None:
        holding.average_buy_price = average_buy_price

    db.commit()
    db.refresh(holding)

    return holding


def delete_holding(
    db: Session,
    holding: Holding,
) -> None:

    db.delete(holding)
    db.commit()
