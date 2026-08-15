from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.pnl_service import calculate_fifo_realized_pnl


def _ordered_transactions(db: Session, user_id: int) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
        .all()
    )


def rebuild_holdings(db: Session, user_id: int) -> None:
    transactions = _ordered_transactions(db, user_id)
    db.query(Holding).filter(Holding.user_id == user_id).delete(synchronize_session=False)
    lots: dict[str, list[list[float]]] = {}

    for transaction in transactions:
        symbol = transaction.symbol.strip().upper()
        quantity = float(transaction.quantity)
        price = float(transaction.price)
        tx_type = transaction.transaction_type.strip().upper()

        if tx_type == "BUY":
            lots.setdefault(symbol, []).append([quantity, price])
            continue
        if tx_type != "SELL":
            raise ValueError("transaction_type must be BUY or SELL")

        remaining = quantity
        symbol_lots = lots.setdefault(symbol, [])
        while remaining > 1e-9 and symbol_lots:
            lot = symbol_lots[0]
            consumed = min(remaining, lot[0])
            lot[0] -= consumed
            remaining -= consumed
            if lot[0] <= 1e-9:
                symbol_lots.pop(0)
        if remaining > 1e-9:
            raise ValueError(
                f"Transaction history is invalid: SELL {quantity:g} {symbol} exceeds shares available on {transaction.transaction_date.isoformat()}."
            )

    for symbol, symbol_lots in lots.items():
        quantity = sum(lot[0] for lot in symbol_lots)
        if quantity <= 1e-9:
            continue
        invested = sum(lot[0] * lot[1] for lot in symbol_lots)
        db.add(Holding(
            user_id=user_id,
            symbol=symbol,
            quantity=quantity,
            average_buy_price=invested / quantity,
        ))


def _validate_transaction_values(symbol: str, transaction_type: str, quantity: float, price: float) -> tuple[str, str]:
    symbol = symbol.strip().upper()
    transaction_type = transaction_type.strip().upper()
    if not symbol:
        raise ValueError("Symbol is required")
    if transaction_type not in {"BUY", "SELL"}:
        raise ValueError("transaction_type must be BUY or SELL")
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if price <= 0:
        raise ValueError("Price must be greater than zero.")
    return symbol, transaction_type


def create_transaction(db: Session, user_id: int, symbol: str, transaction_type: str, quantity: float, price: float, transaction_date: datetime | None = None):
    symbol, transaction_type = _validate_transaction_values(symbol, transaction_type, quantity, price)
    transaction = Transaction(user_id=user_id, symbol=symbol, transaction_type=transaction_type, quantity=quantity, price=price, transaction_date=transaction_date or datetime.now(timezone.utc))
    db.add(transaction)
    try:
        db.flush()
        rebuild_holdings(db, user_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(transaction)
    return transaction


def update_transaction(db: Session, transaction_id: int, user_id: int, symbol: str, transaction_type: str, quantity: float, price: float, transaction_date: datetime | None = None):
    symbol, transaction_type = _validate_transaction_values(symbol, transaction_type, quantity, price)
    transaction = get_transaction(db, transaction_id, user_id)
    if transaction is None:
        return None
    transaction.symbol = symbol
    transaction.transaction_type = transaction_type
    transaction.quantity = quantity
    transaction.price = price
    if transaction_date is not None:
        transaction.transaction_date = transaction_date
    try:
        db.flush()
        rebuild_holdings(db, user_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(transaction)
    return transaction


def delete_transaction(db: Session, transaction_id: int, user_id: int) -> bool | None:
    transaction = get_transaction(db, transaction_id, user_id)
    if transaction is None:
        return None
    db.delete(transaction)
    try:
        db.flush()
        rebuild_holdings(db, user_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def get_user_transactions(db: Session, user_id: int):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .all()
    )


def get_transaction(db: Session, transaction_id: int, user_id: int):
    return db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).first()


def get_transaction_summary(db: Session, user_id: int):
    transactions = get_user_transactions(db, user_id)
    total_buy_value = sum(float(t.quantity) * float(t.price) for t in transactions if t.transaction_type == "BUY")
    total_sell_value = sum(float(t.quantity) * float(t.price) for t in transactions if t.transaction_type == "SELL")
    realized_profit_loss, _ = calculate_fifo_realized_pnl(transactions)
    return {
        "total_transactions": len(transactions),
        "total_buy_value": round(total_buy_value, 2),
        "total_sell_value": round(total_sell_value, 2),
        "realized_profit_loss": round(realized_profit_loss, 2),
    }
