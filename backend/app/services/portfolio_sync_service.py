from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.brokers.dhan import DhanAPIError, DhanClient
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.broker_service import (
    get_access_token,
    mark_sync_result,
)


def _find_transaction(
    db: Session,
    user_id: int,
    symbol: str,
    transaction_type: str,
    quantity: float,
    price: float,
    transaction_date,
):

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.symbol == symbol,
            Transaction.transaction_type
            == transaction_type,
            Transaction.quantity == quantity,
            Transaction.price == price,
        )
        .all()
    )

    for transaction in transactions:

        if transaction.transaction_date:
            if (
                transaction.transaction_date
                == transaction_date
            ):
                return transaction

    return None


def _sync_holdings(
    db: Session,
    user_id: int,
    dhan_holdings: list,
):

    updated = 0

    for item in dhan_holdings:

        symbol = (
            item.get("tradingSymbol")
            or item.get("symbol")
            or ""
        ).strip().upper()

        quantity = float(
            item.get("totalQty", 0)
        )

        average_price = float(
            item.get("avgCostPrice", 0)
        )

        if not symbol:
            continue

        holding = (
            db.query(Holding)
            .filter(
                Holding.user_id == user_id,
                Holding.symbol == symbol,
            )
            .first()
        )

        if holding is None:

            holding = Holding(
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                average_buy_price=average_price,
            )

            db.add(holding)

        else:

            holding.quantity = quantity
            holding.average_buy_price = (
                average_price
            )

        updated += 1

    db.commit()

    return updated


def _sync_trades(
    db: Session,
    user_id: int,
    dhan_trades: list,
):

    imported = 0

    for item in dhan_trades:

        symbol = (
            item.get("tradingSymbol")
            or ""
        ).strip().upper()

        transaction_type = (
            item.get("transactionType")
            or ""
        ).strip().upper()

        quantity = float(
            item.get("tradedQuantity", 0)
        )

        price = float(
            item.get("tradedPrice", 0)
        )

        if (
            not symbol
            or transaction_type
            not in {"BUY", "SELL"}
            or quantity <= 0
        ):
            continue

        raw_date = (
            item.get("exchangeTime")
            or item.get("updateTime")
            or item.get("createTime")
        )

        transaction_date = None

        if raw_date:

            try:

                transaction_date = (
                    datetime.fromisoformat(
                        raw_date.replace(
                            " ",
                            "T",
                        )
                    )
                )

            except ValueError:
                transaction_date = None

        existing = _find_transaction(
            db=db,
            user_id=user_id,
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            transaction_date=transaction_date,
        )

        if existing:
            continue

        transaction = Transaction(
            user_id=user_id,
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            transaction_date=transaction_date,
        )

        db.add(transaction)
        imported += 1

    db.commit()

    return imported


def sync_dhan_portfolio(
    db: Session,
    connection,
):

    token = get_access_token(
        connection
    )

    client = DhanClient(
        client_id=connection.client_id,
        access_token=token,
    )

    try:

        profile = client.profile()

        dhan_holdings = client.holdings()

        dhan_trades = client.trades()

        holdings_updated = _sync_holdings(
            db,
            connection.user_id,
            dhan_holdings,
        )

        transactions_imported = _sync_trades(
            db,
            connection.user_id,
            dhan_trades,
        )

        message = (
            "Dhan portfolio synchronized."
        )

        mark_sync_result(
            db,
            connection,
            True,
            message,
        )

        return {
            "broker_name":
                connection.broker_name,
            "status":
                "SUCCESS",
            "holdings_imported":
                len(dhan_holdings),
            "transactions_imported":
                transactions_imported,
            "holdings_updated":
                holdings_updated,
            "message":
                message,
            "synced_at":
                connection.last_sync_at,
        }

    except DhanAPIError as exc:

        mark_sync_result(
            db,
            connection,
            False,
            str(exc),
        )

        raise
