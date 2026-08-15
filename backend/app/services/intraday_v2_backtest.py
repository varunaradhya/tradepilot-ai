from __future__ import annotations

from typing import Sequence

from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_strategy_v2 import IntradayV2Config, generate_intraday_v2_signal


def run_intraday_v2_backtest(rows: Sequence[dict], market_rows: Sequence[dict] | None = None, sector_rows: Sequence[dict] | None = None, config: IntradayBacktestConfig | None = None, strategy: IntradayV2Config = IntradayV2Config()) -> dict:
    """Conservative V2 backtest using aligned benchmark/sector candles when supplied."""
    cfg = config or IntradayBacktestConfig(strategy=strategy)
    cash = float(cfg.initial_capital)
    position = None
    trades: list[dict] = []
    current_session = None

    def close_position(price: float, reason: str) -> None:
        nonlocal cash, position
        if position is None:
            return
        exit_price = price * (1 - cfg.slippage_rate)
        qty = position["quantity"]
        gross = qty * exit_price
        exit_cost = gross * cfg.brokerage_rate
        cash += gross - exit_cost
        pnl = qty * (exit_price - position["entry"]) - exit_cost - position["entry_cost"]
        trades.append({"entry": position["entry"], "exit": exit_price, "quantity": qty, "pnl": round(pnl, 4), "reason": reason})
        position = None

    minimum = max(strategy.slow_period, strategy.volume_period, strategy.atr_period + 1)
    for i, row in enumerate(rows):
        session = row.get("session")
        if session is not None and current_session is not None and session != current_session and position is not None:
            close_position(float(rows[i - 1]["close"]), "SESSION_CLOSE")
        current_session = session
        if position is not None:
            if float(row["low"]) <= position["stop"]:
                close_position(position["stop"], "STOP")
                continue
            if float(row["high"]) >= position["target"]:
                close_position(position["target"], "TARGET")
                continue
        if position is None and i >= minimum:
            history = rows[: i + 1]
            market_history = market_rows[: i + 1] if market_rows else None
            sector_history = sector_rows[: i + 1] if sector_rows else None
            signal = generate_intraday_v2_signal(
                [float(x["open"]) for x in history], [float(x["high"]) for x in history], [float(x["low"]) for x in history], [float(x["close"]) for x in history], [float(x["volume"]) for x in history],
                [float(x["close"]) for x in market_history] if market_history else None,
                [float(x["close"]) for x in sector_history] if sector_history else None,
                config=strategy,
            )
            if signal["action"] != "BUY":
                continue
            entry = signal["entry"] * (1 + cfg.slippage_rate)
            risk_per_share = entry - signal["stop"]
            risk_budget = cash * strategy.risk_per_trade
            max_value = cash * strategy.max_position_percent
            quantity = min(int(risk_budget / risk_per_share), int(max_value / entry)) if risk_per_share > 0 else 0
            if quantity > 0:
                entry_cost = quantity * entry * cfg.brokerage_rate
                cash -= quantity * entry + entry_cost
                position = {"entry": entry, "stop": signal["stop"], "target": signal["target"], "quantity": quantity, "entry_cost": entry_cost}
    if position is not None and rows:
        close_position(float(rows[-1]["close"]), "END_OF_TEST")
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    gross_loss = abs(sum(losses))
    return {"initial_capital": round(cfg.initial_capital, 2), "ending_capital": round(cash, 2), "return_percent": round((cash / cfg.initial_capital - 1) * 100, 2), "trades": len(trades), "wins": len(wins), "losses": len(losses), "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0, "profit_factor": round(sum(wins) / gross_loss, 4) if gross_loss else None, "trades_detail": trades}
