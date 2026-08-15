from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal


@dataclass(frozen=True)
class IntradayBacktestConfig:
    initial_capital: float = 100000.0
    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    strategy: IntradayConfig = IntradayConfig()


def run_intraday_backtest(rows: Sequence[dict], config: IntradayBacktestConfig = IntradayBacktestConfig()) -> dict:
    """Conservative single-position intraday research backtest.

    Rows must be chronological intraday OHLCV bars and may optionally contain
    ``session``. A position is never carried across sessions.
    """
    cash = float(config.initial_capital)
    trades: list[dict] = []
    position = None
    current_session = None

    def close_position(price: float, reason: str) -> None:
        nonlocal cash, position
        if position is None:
            return
        exit_price = price * (1 - config.slippage_rate)
        qty = position["quantity"]
        gross = qty * exit_price
        costs = gross * config.brokerage_rate
        cash += gross - costs
        pnl = qty * (exit_price - position["entry"]) - costs - position["entry_cost"]
        trades.append({"entry": position["entry"], "exit": exit_price, "quantity": qty, "pnl": pnl, "reason": reason})
        position = None

    for i, row in enumerate(rows):
        session = row.get("session")
        if session is not None and current_session is not None and session != current_session and position is not None:
            close_position(float(rows[i - 1]["close"]), "SESSION_CLOSE")
        current_session = session
        if position is not None:
            high = float(row["high"])
            low = float(row["low"])
            if low <= position["stop"]:
                close_position(position["stop"], "STOP")
                continue
            if high >= position["target"]:
                close_position(position["target"], "TARGET")
                continue
        if position is None and i >= max(config.strategy.slow_period, config.strategy.volume_period, config.strategy.atr_period + 1):
            history = rows[: i + 1]
            signal = generate_intraday_signal(
                [float(x["open"]) for x in history], [float(x["high"]) for x in history],
                [float(x["low"]) for x in history], [float(x["close"]) for x in history],
                [float(x["volume"]) for x in history], config=config.strategy,
            )
            if signal["action"] == "BUY":
                entry = signal["entry"] * (1 + config.slippage_rate)
                risk_per_share = entry - signal["stop"]
                risk_budget = cash * config.strategy.risk_per_trade
                max_value = cash * config.strategy.max_position_percent
                quantity = min(int(risk_budget / risk_per_share), int(max_value / entry)) if risk_per_share > 0 else 0
                if quantity > 0:
                    entry_cost = quantity * entry * config.brokerage_rate
                    cash -= quantity * entry + entry_cost
                    position = {"entry": entry, "stop": signal["stop"], "target": signal["target"], "quantity": quantity, "entry_cost": entry_cost}
    if position is not None and rows:
        close_position(float(rows[-1]["close"]), "END_OF_TEST")
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    gross_loss = abs(sum(losses))
    return {
        "initial_capital": round(config.initial_capital, 2),
        "ending_capital": round(cash, 2),
        "return_percent": round((cash / config.initial_capital - 1) * 100, 2),
        "trades": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(sum(wins) / gross_loss, 4) if gross_loss else None,
        "trades_detail": trades,
    }
