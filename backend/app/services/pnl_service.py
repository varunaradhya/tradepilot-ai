from collections import defaultdict

from app.models.transaction import Transaction


def calculate_fifo_realized_pnl(
    transactions: list[Transaction],
) -> tuple[float, float]:
    """Return (realized P/L, realized cost basis) using FIFO lots."""
    lots = defaultdict(list)
    realized = 0.0
    realized_cost_basis = 0.0

    ordered = sorted(
        transactions,
        key=lambda transaction: (
            transaction.transaction_date,
            transaction.id or 0,
        ),
    )

    for transaction in ordered:
        symbol = transaction.symbol.strip().upper()
        quantity = float(transaction.quantity)
        price = float(transaction.price)

        if transaction.transaction_type == "BUY":
            lots[symbol].append([quantity, price])
            continue

        if transaction.transaction_type != "SELL":
            continue

        remaining = quantity
        while remaining > 1e-12 and lots[symbol]:
            lot_quantity, lot_price = lots[symbol][0]
            matched = min(remaining, lot_quantity)
            realized_cost_basis += matched * lot_price
            realized += matched * (price - lot_price)
            remaining -= matched
            lot_quantity -= matched

            if lot_quantity <= 1e-12:
                lots[symbol].pop(0)
            else:
                lots[symbol][0][0] = lot_quantity

    return round(realized, 2), round(realized_cost_basis, 2)
