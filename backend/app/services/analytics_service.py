from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.market_service import MarketDataProviderError, get_quote
from app.services.pnl_service import calculate_fifo_realized_pnl


def calculate_realized_profit_loss(db: Session, user_id: int) -> tuple[float, float]:
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    return calculate_fifo_realized_pnl(transactions)


def calculate_analytics(db: Session, user_id: int):
    holdings = db.query(Holding).filter(Holding.user_id == user_id).order_by(Holding.symbol.asc()).all()
    transaction_count = db.query(Transaction).filter(Transaction.user_id == user_id).count()
    stocks = []
    total_invested = 0.0
    current_value = 0.0
    unavailable_symbols: list[str] = []

    for holding in holdings:
        quantity = float(holding.quantity)
        average_price = float(holding.average_buy_price)
        invested = quantity * average_price
        total_invested += invested
        try:
            current_price = float(get_quote(holding.symbol).price)
            value = quantity * current_price
            unrealized = value - invested
            unrealized_percent = (unrealized / invested) * 100 if invested else 0.0
            available = True
            current_value += value
        except MarketDataProviderError:
            current_price = 0.0
            value = 0.0
            unrealized = 0.0
            unrealized_percent = 0.0
            available = False
            unavailable_symbols.append(holding.symbol)

        stocks.append({
            "symbol": holding.symbol,
            "quantity": quantity,
            "invested_amount": round(invested, 2),
            "current_price": round(current_price, 2),
            "current_value": round(value, 2),
            "unrealized_profit_loss": round(unrealized, 2),
            "unrealized_profit_loss_percent": round(unrealized_percent, 2),
            "market_data_available": available,
        })

    available_invested = sum(item["invested_amount"] for item in stocks if item["market_data_available"])
    unrealized_profit_loss = current_value - available_invested
    unrealized_percent = (unrealized_profit_loss / available_invested) * 100 if available_invested else 0.0
    realized_profit_loss, realized_cost_basis = calculate_realized_profit_loss(db, user_id)
    total_profit_loss = realized_profit_loss + unrealized_profit_loss
    total_cost_basis = total_invested + realized_cost_basis
    total_return_percent = (total_profit_loss / total_cost_basis) * 100 if total_cost_basis else 0.0
    available_stocks = [x for x in stocks if x["market_data_available"]]
    best_performer = max(available_stocks, key=lambda x: x["unrealized_profit_loss_percent"])["symbol"] if available_stocks else None
    worst_performer = min(available_stocks, key=lambda x: x["unrealized_profit_loss_percent"])["symbol"] if available_stocks else None

    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "unrealized_profit_loss": round(unrealized_profit_loss, 2),
        "unrealized_profit_loss_percent": round(unrealized_percent, 2),
        "realized_profit_loss": round(realized_profit_loss, 2),
        "total_profit_loss": round(total_profit_loss, 2),
        "total_return_percent": round(total_return_percent, 2),
        "best_performer": best_performer,
        "worst_performer": worst_performer,
        "holdings_count": len(holdings),
        "transactions_count": transaction_count,
        "market_data_complete": not unavailable_symbols,
        "unavailable_symbols": sorted(set(unavailable_symbols)),
        "stocks": stocks,
    }
