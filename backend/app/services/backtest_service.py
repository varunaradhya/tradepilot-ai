from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.algo_strategy import StrategyConfig, generate_regime_momentum_signal, position_size


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100000.0
    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    max_daily_loss_percent: float = 0.02
    max_trades_per_day: int = 3
    trailing_stop_enabled: bool = True
    strategy: StrategyConfig = StrategyConfig()


def _sell_fill(price: float, slippage_rate: float) -> float:
    return float(price) * (1.0 - slippage_rate)


def _buy_fill(price: float, slippage_rate: float) -> float:
    return float(price) * (1.0 + slippage_rate)


def run_daily_backtest(rows: Sequence[dict], config: BacktestConfig = BacktestConfig()) -> dict:
    """Conservative long-only daily backtest with execution and risk realism."""
    if config.initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if not rows:
        raise ValueError("rows must not be empty")
    if config.max_daily_loss_percent <= 0 or config.max_trades_per_day < 1:
        raise ValueError("invalid portfolio risk limits")

    cash = float(config.initial_capital)
    quantity = 0
    entry_price = stop = target = 0.0
    initial_risk = 0.0
    high_watermark = 0.0
    pending_signal = None
    trades: list[dict] = []
    equity_curve: list[float] = []
    daily_pnl = 0.0
    daily_trades = 0
    current_session = None
    halted = False

    def close_position(exit_price: float, reason: str, entry_cost: float) -> None:
        nonlocal cash, quantity, entry_price, stop, target, initial_risk, high_watermark, daily_pnl
        gross = quantity * exit_price
        exit_cost = gross * config.brokerage_rate
        pnl = quantity * (exit_price - entry_price) - entry_cost - exit_cost
        cash += gross - exit_cost
        daily_pnl += pnl
        trades.append({"entry": entry_price, "exit": exit_price, "quantity": quantity, "pnl": pnl, "reason": reason})
        quantity = 0
        entry_price = stop = target = initial_risk = high_watermark = 0.0

    for i, row in enumerate(rows):
        session = row.get("date") or row.get("timestamp") or "BACKTEST"
        if session != current_session:
            current_session = session
            daily_pnl = 0.0
            daily_trades = 0
            halted = False

        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])
        open_price = float(row.get("open", close))
        if min(open_price, close, high, low) <= 0 or low > high:
            continue

        if quantity == 0 and pending_signal is not None and not halted and daily_trades < config.max_trades_per_day:
            signal = pending_signal
            pending_signal = None
            actual_entry = _buy_fill(open_price, config.slippage_rate)
            actual_stop = float(signal.stop)
            actual_target = float(signal.target)
            size = position_size(cash, actual_entry, actual_stop, config.strategy)
            if size > 0:
                entry_cost = size * actual_entry * config.brokerage_rate
                total_entry_cash = size * actual_entry + entry_cost
                if total_entry_cash <= cash:
                    cash -= total_entry_cash
                    quantity = size
                    entry_price = actual_entry
                    stop = actual_stop
                    target = actual_target
                    initial_risk = actual_entry - actual_stop
                    high_watermark = actual_entry
                    daily_trades += 1
                    if open_price <= stop:
                        close_position(_sell_fill(open_price, config.slippage_rate), "STOP_GAP", entry_cost)
                    elif open_price >= target:
                        close_position(_sell_fill(open_price, config.slippage_rate), "TARGET_GAP", entry_cost)

        if quantity:
            exit_price = None
            exit_reason = None
            high_watermark = max(high_watermark, high)
            if open_price <= stop:
                exit_price, exit_reason = _sell_fill(open_price, config.slippage_rate), "STOP_GAP"
            elif open_price >= target:
                exit_price, exit_reason = _sell_fill(open_price, config.slippage_rate), "TARGET_GAP"
            elif low <= stop:
                exit_price, exit_reason = _sell_fill(stop, config.slippage_rate), "STOP"
            elif high >= target:
                exit_price, exit_reason = _sell_fill(target, config.slippage_rate), "TARGET"
            if exit_price is not None:
                entry_cost = quantity * entry_price * config.brokerage_rate
                close_position(exit_price, exit_reason, entry_cost)

        if quantity and config.trailing_stop_enabled:
            risk_unit = initial_risk
            if risk_unit > 0 and high_watermark >= entry_price + config.strategy.trailing_activation_r * risk_unit:
                trailing = high_watermark - config.strategy.trailing_atr * max((high - low), entry_price * 0.001)
                if trailing > stop:
                    stop = min(trailing, target * 0.999)

        equity_curve.append(cash + quantity * close if quantity else cash)

        if daily_pnl <= -(config.initial_capital * config.max_daily_loss_percent):
            halted = True
            pending_signal = None

        if quantity == 0 and pending_signal is None and not halted and daily_trades < config.max_trades_per_day and i >= 60:
            history = rows[: i + 1]
            closes = [float(x["close"]) for x in history]
            highs = [float(x["high"]) for x in history]
            lows = [float(x["low"]) for x in history]
            volumes = [float(x["volume"]) for x in history] if all(x.get("volume") is not None for x in history) else None
            signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config.strategy)
            if signal.action == "BUY" and signal.entry and signal.stop and signal.target:
                pending_signal = signal

    if quantity:
        entry_cost = quantity * entry_price * config.brokerage_rate
        final_price = _sell_fill(float(rows[-1]["close"]), config.slippage_rate)
        close_position(final_price, "END_OF_TEST", entry_cost)
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

    expectancy = ((sum(wins) / len(wins)) * (len(wins) / len(trades)) + (sum(losses) / len(losses)) * (len(losses) / len(trades))) if trades else 0.0
    return {
        "initial_capital": round(config.initial_capital, 2),
        "ending_capital": round(ending, 2),
        "return_percent": round((ending / config.initial_capital - 1) * 100, 2),
        "trades": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate_percent": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (None if not gross_profit else float("inf")),
        "expectancy_per_trade": round(expectancy, 2),
        "max_drawdown_percent": round(max_drawdown, 2),
        "gross_profit": round(gross_profit, 2), "gross_loss": round(gross_loss, 2),
        "trades_detail": trades, "equity_curve": [round(value, 2) for value in equity_curve],
    }
