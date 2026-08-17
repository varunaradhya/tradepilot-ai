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
    query = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.symbol == symbol,
            Transaction.transaction_type == transaction_type,
            Transaction.quantity == quantity,
            Transaction.price == price,
        )
    )

    # Keep the existing compatibility-based dedupe for historical rows.
    for transaction in query.all():
        if transaction.transaction_date == transaction_date:
            return transaction

    return None


def _sync_holdings(
    db: Session,
    user_id: int,
    dhan_holdings: list,
):
    """Make the Dhan holdings snapshot authoritative for the current user.

    The previous implementation only upserted returned symbols, which meant a
    position sold completely at Dhan could remain permanently stale in
    TradePilot. Dhan is the only supported broker in this sync path, so remove
    local holdings that are absent from the authoritative broker snapshot.
    """
    broker_symbols: set[str] = set()
    updated = 0

    for item in dhan_holdings:
        symbol = (
            item.get("tradingSymbol")
            or item.get("symbol")
            or ""
        ).strip().upper()

        if not symbol:
            continue

        try:
            quantity = float(item.get("totalQty", 0))
            average_price = float(item.get("avgCostPrice", 0))
        except (TypeError, ValueError):
            continue

        if quantity < 0 or average_price < 0:
            continue

        broker_symbols.add(symbol)

        holding = (
            db.query(Holding)
            .filter(
                Holding.user_id == user_id,
                Holding.symbol == symbol,
            )
            .first()
        )

        if holding is None:
            db.add(
                Holding(
                    user_id=user_id,
                    symbol=symbol,
                    quantity=quantity,
                    average_buy_price=average_price,
                )
            )
        else:
            holding.quantity = quantity
            holding.average_buy_price = average_price

        updated += 1

    # Remove positions that disappeared from the broker snapshot. This is
    # essential for sells/fully-closed positions and prevents stale P&L.
    stale_holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id)
        .all()
    )
    for holding in stale_holdings:
        if holding.symbol.upper() not in broker_symbols:
            db.delete(holding)

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
            or item.get("symbol")
            or ""
        ).strip().upper()
        transaction_type = (
            item.get("transactionType")
            or ""
        ).strip().upper()

        try:
            quantity = float(item.get("tradedQuantity", 0))
            price = float(item.get("tradedPrice", 0))
        except (TypeError, ValueError):
            continue

        if (
            not symbol
            or transaction_type not in {"BUY", "SELL"}
            or quantity <= 0
            or price < 0
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
                transaction_date = datetime.fromisoformat(
                    str(raw_date).replace(" ", "T")
                )
            except (TypeError, ValueError):
                transaction_date = None

        # A malformed broker timestamp must not be treated as an exact match
        # for every prior row. Fall back to the model's timestamp only when the
        # broker supplied no timestamp at all.
        if transaction_date is None and not raw_date:
            transaction_date = datetime.now(timezone.utc)

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

        db.add(
            Transaction(
                user_id=user_id,
                symbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                price=price,
                transaction_date=transaction_date or datetime.now(timezone.utc),
            )
        )
        imported += 1

    return imported


def sync_dhan_portfolio(
    db: Session,
    connection,
):
    token = get_access_token(connection)
    client = DhanClient(
        client_id=connection.client_id,
        access_token=token,
    )

    try:
        # Fetch the complete broker snapshot before mutating local state.
        # This prevents a partial update if one broker endpoint fails.
        client.profile()
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

        db.commit()

        message = "Dhan portfolio synchronized."
        mark_sync_result(db, connection, True, message)

        return {
            "broker_name": connection.broker_name,
            "status": "SUCCESS",
            "holdings_imported": len(dhan_holdings),
            "transactions_imported": transactions_imported,
            "holdings_updated": holdings_updated,
            "message": message,
            "synced_at": connection.last_sync_at,
        }

    except DhanAPIError as exc:
        db.rollback()
        mark_sync_result(
            db,
            connection,
            False,
            str(exc),
        )
        raise
    except Exception:
        db.rollback()
        mark_sync_result(
            db,
            connection,
            False,
            "Portfolio sync failed before local changes were committed.",
        )
        raise
