from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.pnl_service import calculate_fifo_realized_pnl


def create_transaction(
    db: Session,
    user_id: int,
    symbol: str,
    transaction_type: str,
    quantity: float,
    price: float,
    transaction_date: datetime | None = None,
):
    symbol = symbol.strip().upper()
    transaction_type = transaction_type.strip().upper()

    if transaction_type not in {"BUY", "SELL"}:
        raise ValueError("transaction_type must be BUY or SELL")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if price <= 0:
        raise ValueError("Price must be greater than zero.")

    holding = (
        db.query(Holding)
        .filter(
            Holding.user_id == user_id,
            Holding.symbol == symbol,
        )
        .first()
    )

    if transaction_type == "BUY":
        if holding is None:
            holding = Holding(
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                average_buy_price=price,
            )
            db.add(holding)
        else:
            old_quantity = float(holding.quantity)
            old_average = float(holding.average_buy_price)
            new_quantity = old_quantity + quantity
            new_average = (
                (old_quantity * old_average) + (quantity * price)
            ) / new_quantity
            holding.quantity = new_quantity
            holding.average_buy_price = new_average
    else:
        if holding is None:
            raise ValueError("Cannot sell a stock that is not in the portfolio.")

        current_quantity = float(holding.quantity)
        if quantity > current_quantity:
            raise ValueError("Sell quantity cannot exceed current holding quantity.")

        holding.quantity = current_quantity - quantity
        if holding.quantity == 0:
            db.delete(holding)

    transaction = Transaction(
        user_id=user_id,
        symbol=symbol,
        transaction_type=transaction_type,
        quantity=quantity,
        price=price,
        transaction_date=transaction_date or datetime.now(timezone.utc),
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_user_transactions(db: Session, user_id: int):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )


def get_transaction(db: Session, transaction_id: int, user_id: int):
    return (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        .first()
    )


def get_transaction_summary(db: Session, user_id: int):
    transactions = get_user_transactions(db, user_id)
    total_buy_value = 0.0
    total_sell_value = 0.0

    for transaction in transactions:
        value = float(transaction.quantity) * float(transaction.price)
        if transaction.transaction_type == "BUY":
            total_buy_value += value
        elif transaction.transaction_type == "SELL":
            total_sell_value += value

    realized_profit_loss, _ = calculate_fifo_realized_pnl(transactions)

    return {
        "total_transactions": len(transactions),
        "total_buy_value": round(total_buy_value, 2),
        "total_sell_value": round(total_sell_value, 2),
        "realized_profit_loss": round(realized_profit_loss, 2),
    }
