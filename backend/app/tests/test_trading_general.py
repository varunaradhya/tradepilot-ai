from datetime import datetime

from app.models.transaction import Transaction
from app.services.trading_general_service import calculate_trading_general


def tx(symbol, kind, qty, price, ident):
    return Transaction(id=ident, symbol=symbol, transaction_type=kind, quantity=qty, price=price, transaction_date=datetime(2026, 1, ident))


def test_trading_general_calculates_fifo_wins_losses_and_profit_factor():
    result = calculate_trading_general([
        tx("TCS", "BUY", 10, 100, 1),
        tx("TCS", "SELL", 10, 150, 2),
        tx("INFY", "BUY", 10, 200, 3),
        tx("INFY", "SELL", 10, 180, 4),
    ])
    assert result["realized_pnl"] == 300
    assert result["winning_trades"] == 1
    assert result["losing_trades"] == 1
    assert result["win_rate_percent"] == 50
    assert result["profit_factor"] == 2.5
    assert result["expectancy_per_trade"] == 150


def test_trading_general_uses_fifo_for_multiple_lots():
    result = calculate_trading_general([
        tx("TCS", "BUY", 10, 100, 1),
        tx("TCS", "BUY", 10, 200, 2),
        tx("TCS", "SELL", 15, 180, 3),
    ])
    assert result["realized_pnl"] == 700
    assert result["sample_size"] == 2


def test_trading_general_empty_history_is_safe():
    result = calculate_trading_general([])
    assert result["realized_pnl"] == 0
    assert result["sample_size"] == 0
    assert result["strategy_score"] == 0
