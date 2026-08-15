from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.algo_strategy import StrategyConfig, generate_regime_momentum_signal, position_size


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100000.0
    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    strategy: StrategyConfig = StrategyConfig()


def run_daily_backtest(rows: Sequence[dict], config: BacktestConfig = BacktestConfig()) -> dict:
    cash = float(config.initial_capital)
    quantity = 0
    entry_price = 0.0
    stop = 0.0
    target = 0.0
    trades: list[dict] = []
    equity_curve: list[float] = []

    for i, row in enumerate(rows):
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])
        equity_curve.append(cash + quantity * close)

        if quantity:
            exit_price = None
            exit_reason = None
            # Conservative rule: if both stop and target are touched in one candle,
            # assume the stop was hit first. This avoids optimistic intrabar bias.
            if low <= stop:
                exit_price, exit_reason = stop * (1 - config.slippage_rate), "STOP"
            elif high >= target:
                exit_price, exit_reason = target * (1 - config.slippage_rate), "TARGET"
            if exit_price is not None:
                gross = quantity * exit_price
                costs = gross * config.brokerage_rate
                cash += gross - costs
                pnl = quantity * (exit_price - entry_price) - costs
                trades.append({"entry": entry_price, "exit": exit_price, "quantity": quantity, "pnl": pnl, "reason": exit_reason})
                quantity = 0
                entry_price = stop = target = 0.0
                equity_curve[-1] = cash
                continue

        if not quantity and i >= 60:
            history = rows[: i + 1]
            closes = [float(x["close"]) for x in history]
            highs = [float(x["high"]) for x in history]
            lows = [float(x["low"]) for x in history]
            volumes = [float(x["volume"]) for x in history] if all(x.get("volume") is not None for x in history) else None
            signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config.strategy)
            if signal.action == "BUY" and signal.entry and signal.stop and signal.target:
                size = position_size(cash, signal.entry, signal.stop, config.strategy)
                if size > 0:
                    entry_price = signal.entry * (1 + config.slippage_rate)
                    entry_cost = size * entry_price * config.brokerage_rate
                    cash -= size * entry_price + entry_cost
                    quantity = size
                    stop = signal.stop
                    target = signal.target

    if quantity:
        final_price = float(rows[-1]["close"]) * (1 - config.slippage_rate)
        gross = quantity * final_price
        costs = gross * config.brokerage_rate
        cash += gross - costs
        pnl = quantity * (final_price - entry_price) - costs
        trades.append({"entry": entry_price, "exit": final_price, "quantity": quantity, "pnl": pnl, "reason": "END_OF_TEST"})
        equity_curve[-1] = cash

    ending = cash
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    peak = config.initial_capital
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100)

    return {
        "initial_capital": round(config.initial_capital, 2),
        "ending_capital": round(ending, 2),
        "return_percent": round((ending / config.initial_capital - 1) * 100, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (None if not gross_profit else float("inf")),
        "max_drawdown_percent": round(max_drawdown, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "trades_detail": trades,
        "equity_curve": [round(value, 2) for value in equity_curve],
    }
