from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal


@dataclass(frozen=True)
class IntradayBacktestConfig:
    initial_capital: float = 100000.0
    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    max_daily_loss_percent: float = 1.0
    max_trades_per_session: int = 3
    strategy: IntradayConfig = IntradayConfig()


def _metrics(initial_capital: float, ending_capital: float, trades: list[dict]) -> dict:
    pnls = [float(t["pnl"]) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_loss = abs(sum(losses))
    equity = float(initial_capital)
    peak = equity
    max_drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        if peak:
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
    expectancy = sum(pnls) / len(pnls) if pnls else 0.0
    return {
        "initial_capital": round(initial_capital, 2),
        "ending_capital": round(ending_capital, 2),
        "return_percent": round((ending_capital / initial_capital - 1) * 100, 2) if initial_capital else 0.0,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(sum(wins) / gross_loss, 4) if gross_loss else None,
        "expectancy": round(expectancy, 4),
        "average_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "average_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "max_drawdown_percent": round(max_drawdown, 2),
    }


def run_intraday_backtest(rows: Sequence[dict], config: IntradayBacktestConfig = IntradayBacktestConfig()) -> dict:
    """Conservative single-position intraday research backtest with session isolation and risk caps."""
    if not rows:
        return _metrics(config.initial_capital, config.initial_capital, []) | {"trades_detail": []}

    cash = float(config.initial_capital)
    trades: list[dict] = []
    position = None
    current_session = None
    session_rows: list[dict] = []
    session_start_cash = cash
    session_pnl = 0.0
    session_trade_count = 0
    session_halted = False

    def close_position(price: float, reason: str, exit_time: object = None) -> None:
        nonlocal cash, position, session_pnl
        if position is None:
            return
        exit_price = price * (1 - config.slippage_rate)
        qty = position["quantity"]
        gross = qty * exit_price
        costs = gross * config.brokerage_rate
        cash += gross - costs
        pnl = qty * (exit_price - position["entry"]) - costs - position["entry_cost"]
        trade = {
            "entry": position["entry"],
            "exit": exit_price,
            "quantity": qty,
            "pnl": pnl,
            "reason": reason,
        }
        if position.get("entry_time") is not None:
            trade["entry_time"] = position["entry_time"]
        if exit_time is not None:
            trade["exit_time"] = exit_time
        session_pnl += pnl
        trades.append(trade)
        position = None

    for i, row in enumerate(rows):
        session = row.get("session")
        if session is not None and current_session is not None and session != current_session:
            if position is not None:
                close_position(float(rows[i - 1]["close"]), "SESSION_CLOSE", rows[i - 1].get("timestamp", rows[i - 1].get("time")))
            session_rows = []
            session_start_cash = cash
            session_pnl = 0.0
            session_trade_count = 0
            session_halted = False
        current_session = session
        session_rows.append(row)

        if position is not None:
            high = float(row["high"])
            low = float(row["low"])
            if low <= position["stop"]:
                close_position(position["stop"], "STOP", row.get("timestamp", row.get("time")))
            elif high >= position["target"]:
                close_position(position["target"], "TARGET", row.get("timestamp", row.get("time")))

            if session_start_cash and (-session_pnl / session_start_cash * 100) >= config.max_daily_loss_percent:
                session_halted = True
            if position is not None:
                continue

        if session_start_cash and (-session_pnl / session_start_cash * 100) >= config.max_daily_loss_percent:
            session_halted = True
        if session_halted or session_trade_count >= config.max_trades_per_session:
            continue

        minimum = max(config.strategy.slow_period, config.strategy.volume_period, config.strategy.atr_period + 1)
        if len(session_rows) >= minimum:
            history = session_rows
            opening = history[: config.strategy.opening_bars]
            signal = generate_intraday_signal(
                [float(x["open"]) for x in history], [float(x["high"]) for x in history],
                [float(x["low"]) for x in history], [float(x["close"]) for x in history],
                [float(x["volume"]) for x in history],
                opening_high=max(float(x["high"]) for x in opening),
                opening_low=min(float(x["low"]) for x in opening),
                config=config.strategy,
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
                    position = {
                        "entry": entry,
                        "stop": signal["stop"],
                        "target": signal["target"],
                        "quantity": quantity,
                        "entry_cost": entry_cost,
                        "entry_time": row.get("timestamp", row.get("time")),
                    }
                    session_trade_count += 1

    if position is not None:
        close_position(float(rows[-1]["close"]), "END_OF_TEST", rows[-1].get("timestamp", rows[-1].get("time")))
    return _metrics(config.initial_capital, cash, trades) | {"trades_detail": trades}
