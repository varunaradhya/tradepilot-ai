from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.market_service import (
    MarketDataProviderError,
    get_quote,
)


def calculate_realized_profit_loss(
    db: Session,
    user_id: int,
) -> float:

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(
            Transaction.transaction_date.asc(),
            Transaction.id.asc(),
        )
        .all()
    )

    positions = {}
    realized = 0.0

    for transaction in transactions:

        symbol = transaction.symbol
        quantity = float(transaction.quantity)
        price = float(transaction.price)

        if symbol not in positions:
            positions[symbol] = {
                "quantity": 0.0,
                "average_cost": 0.0,
            }

        position = positions[symbol]

        if transaction.transaction_type == "BUY":

            old_quantity = position["quantity"]
            old_average = position["average_cost"]

            new_quantity = old_quantity + quantity

            if new_quantity > 0:

                position["average_cost"] = (
                    (
                        old_quantity * old_average
                    )
                    + (
                        quantity * price
                    )
                ) / new_quantity

            position["quantity"] = new_quantity

        elif transaction.transaction_type == "SELL":

            if quantity <= position["quantity"]:

                realized += (
                    quantity
                    * (
                        price
                        - position["average_cost"]
                    )
                )

                position["quantity"] -= quantity

    return round(realized, 2)


def calculate_analytics(
    db: Session,
    user_id: int,
):

    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id)
        .order_by(Holding.symbol.asc())
        .all()
    )

    transaction_count = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .count()
    )

    stocks = []

    total_invested = 0.0
    current_value = 0.0

    for holding in holdings:

        quantity = float(holding.quantity)
        average_price = float(
            holding.average_buy_price
        )

        invested = quantity * average_price

        try:

            quote = get_quote(
                holding.symbol
            )

            current_price = float(
                quote.price
            )

        except MarketDataProviderError:

            current_price = average_price

        value = quantity * current_price

        unrealized = value - invested

        unrealized_percent = (
            (unrealized / invested) * 100
            if invested
            else 0.0
        )

        stocks.append(
            {
                "symbol": holding.symbol,
                "quantity": quantity,
                "invested_amount": round(
                    invested,
                    2,
                ),
                "current_value": round(
                    value,
                    2,
                ),
                "unrealized_profit_loss": round(
                    unrealized,
                    2,
                ),
                "unrealized_profit_loss_percent": round(
                    unrealized_percent,
                    2,
                ),
            }
        )

        total_invested += invested
        current_value += value

    unrealized_profit_loss = (
        current_value - total_invested
    )

    unrealized_percent = (
        (
            unrealized_profit_loss
            / total_invested
        ) * 100
        if total_invested
        else 0.0
    )

    realized_profit_loss = (
        calculate_realized_profit_loss(
            db,
            user_id,
        )
    )

    total_profit_loss = (
        realized_profit_loss
        + unrealized_profit_loss
    )

    total_return_percent = (
        (
            total_profit_loss
            / total_invested
        ) * 100
        if total_invested
        else 0.0
    )

    best_performer = None
    worst_performer = None

    if stocks:

        best = max(
            stocks,
            key=lambda item:
            item["unrealized_profit_loss_percent"],
        )

        worst = min(
            stocks,
            key=lambda item:
            item["unrealized_profit_loss_percent"],
        )

        best_performer = best["symbol"]
        worst_performer = worst["symbol"]

    return {
        "total_invested": round(
            total_invested,
            2,
        ),
        "current_value": round(
            current_value,
            2,
        ),
        "unrealized_profit_loss": round(
            unrealized_profit_loss,
            2,
        ),
        "unrealized_profit_loss_percent": round(
            unrealized_percent,
            2,
        ),
        "realized_profit_loss": round(
            realized_profit_loss,
            2,
        ),
        "total_profit_loss": round(
            total_profit_loss,
            2,
        ),
        "total_return_percent": round(
            total_return_percent,
            2,
        ),
        "best_performer": best_performer,
        "worst_performer": worst_performer,
        "holdings_count": len(holdings),
        "transactions_count": transaction_count,
        "stocks": stocks,
    }
