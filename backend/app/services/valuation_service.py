from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.services.market_service import (
    MarketDataProviderError,
    get_quote,
)


def calculate_portfolio_valuation(
    db: Session,
    user_id: int,
):
    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id)
        .order_by(Holding.symbol.asc())
        .all()
    )

    valuation_holdings = []

    total_invested = 0.0
    current_value = 0.0

    for holding in holdings:

        invested_amount = (
            float(holding.quantity)
            * float(holding.average_buy_price)
        )

        try:
            quote = get_quote(holding.symbol)
            current_price = float(quote.price)

        except MarketDataProviderError:
            current_price = float(holding.average_buy_price)

        holding_current_value = (
            float(holding.quantity)
            * current_price
        )

        profit_loss = (
            holding_current_value
            - invested_amount
        )

        profit_loss_percent = (
            (profit_loss / invested_amount) * 100
            if invested_amount != 0
            else 0.0
        )

        valuation_holdings.append(
            {
                "id": holding.id,
                "symbol": holding.symbol,
                "quantity": float(holding.quantity),
                "average_buy_price": float(
                    holding.average_buy_price
                ),
                "invested_amount": round(
                    invested_amount,
                    2,
                ),
                "current_price": round(
                    current_price,
                    2,
                ),
                "current_value": round(
                    holding_current_value,
                    2,
                ),
                "profit_loss": round(
                    profit_loss,
                    2,
                ),
                "profit_loss_percent": round(
                    profit_loss_percent,
                    2,
                ),
            }
        )

        total_invested += invested_amount
        current_value += holding_current_value

    total_profit_loss = (
        current_value
        - total_invested
    )

    total_profit_loss_percent = (
        (total_profit_loss / total_invested) * 100
        if total_invested != 0
        else 0.0
    )

    return {
        "summary": {
            "total_invested": round(
                total_invested,
                2,
            ),
            "current_value": round(
                current_value,
                2,
            ),
            "profit_loss": round(
                total_profit_loss,
                2,
            ),
            "profit_loss_percent": round(
                total_profit_loss_percent,
                2,
            ),
            "holdings_count": len(holdings),
        },
        "holdings": valuation_holdings,
    }
