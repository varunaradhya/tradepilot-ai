from collections import defaultdict
from app.models.transaction import Transaction


def calculate_trading_general(transactions: list[Transaction]):
    lots = defaultdict(list)
    closed = []
    ordered = sorted(transactions, key=lambda t: (t.transaction_date, t.id or 0))
    for tx in ordered:
        symbol, qty, price = tx.symbol.strip().upper(), float(tx.quantity), float(tx.price)
        if tx.transaction_type == "BUY":
            lots[symbol].append([qty, price])
            continue
        if tx.transaction_type != "SELL":
            continue
        remaining = qty
        while remaining > 1e-12 and lots[symbol]:
            lot_qty, lot_price = lots[symbol][0]
            matched = min(remaining, lot_qty)
            cost = matched * lot_price
            pnl = matched * (price - lot_price)
            closed.append({"symbol": symbol, "realized_pnl": pnl, "return_percent": pnl / cost * 100 if cost else 0.0, "quantity": matched, "sell_price": price, "cost_basis": cost})
            remaining -= matched
            lot_qty -= matched
            if lot_qty <= 1e-12: lots[symbol].pop(0)
            else: lots[symbol][0][0] = lot_qty

    wins = [x for x in closed if x["realized_pnl"] > 1e-9]
    losses = [x for x in closed if x["realized_pnl"] < -1e-9]
    pnl = sum(x["realized_pnl"] for x in closed)
    gp, gl = sum(x["realized_pnl"] for x in wins), abs(sum(x["realized_pnl"] for x in losses))
    win_rate = len(wins) / len(closed) * 100 if closed else 0.0
    avg_win = gp / len(wins) if wins else 0.0
    avg_loss = -gl / len(losses) if losses else 0.0
    pf = gp / gl if gl else (999.0 if gp else None)
    score = 0 if not closed else max(0, min(100, 50 + (15 if win_rate >= 55 else -15 if win_rate < 40 else 0) + (15 if pf is not None and pf >= 1.5 else -15 if pf is not None and pf < 1 else 0) + (10 if avg_win > abs(avg_loss) else -10 if losses else 0)))
    label = "Not enough data" if not closed else "Strong" if score >= 75 else "Needs improvement" if score < 50 else "Mixed"
    best = max(closed, key=lambda x: x["realized_pnl"]) if closed else None
    worst = min(closed, key=lambda x: x["realized_pnl"]) if closed else None
    return {
        "realized_pnl": round(pnl, 2), "total_closed_quantity": round(sum(x["quantity"] for x in closed), 4),
        "winning_trades": len(wins), "losing_trades": len(losses), "breakeven_trades": len(closed)-len(wins)-len(losses),
        "win_rate_percent": round(win_rate, 2), "average_win": round(avg_win, 2), "average_loss": round(avg_loss, 2),
        "profit_factor": round(pf, 2) if pf is not None else None, "expectancy_per_trade": round(pnl / len(closed), 2) if closed else 0.0,
        "best_trade": best, "worst_trade": worst,
        "largest_win_percent": round(max((x["return_percent"] for x in wins), default=0), 2) if wins else None,
        "largest_loss_percent": round(min((x["return_percent"] for x in losses), default=0), 2) if losses else None,
        "strategy_score": score, "strategy_label": label,
        "strategy_insights": ["Add more closed trades to improve the reliability of this analysis."] if not closed else [f"You have {len(closed)} closed FIFO trade lots to analyze."],
        "loss_patterns": (["Win rate is below 40%."] if win_rate < 40 and closed else []) + (["Average losing trade is at least as large as the average winner."] if losses and avg_win <= abs(avg_loss) else []),
        "profit_patterns": (["Win rate is above 55%."] if win_rate >= 55 else []) + (["Average winner is larger than average loser."] if wins and avg_win > abs(avg_loss) else []),
        "suggested_rules": ["Define a maximum loss before entering each trade.", "Record an entry reason and exit reason so repeated winning and losing setups can be identified."],
        "sample_size": len(closed),
        "disclaimer": "Retrospective analysis of recorded trades only; not a prediction or personalized financial advice.",
    }
