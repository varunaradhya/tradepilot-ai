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


def _sell_fill(price: float, slippage_rate: float) -> float:
    return float(price) * (1.0 - slippage_rate)


def _buy_fill(price: float, slippage_rate: float) -> float:
    return float(price) * (1.0 + slippage_rate)


def run_daily_backtest(rows: Sequence[dict], config: BacktestConfig = BacktestConfig()) -> dict:
    """Run a conservative long-only daily backtest.

    A signal is generated only after a bar has closed and can therefore be
    executed no earlier than the following bar's open.  This is critical:
    using the signal bar's close as its execution price introduces look-ahead
    bias.  Existing positions are marked/exited using the current bar, with
    stop-first ordering when both stop and target are touched.
    """
    if config.initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if not rows:
        raise ValueError("rows must not be empty")

    cash = float(config.initial_capital)
    quantity = 0
    entry_price = 0.0
    stop = 0.0
    target = 0.0
    pending_signal = None
    trades: list[dict] = []
    equity_curve: list[float] = []

    for i, row in enumerate(rows):
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])
        open_price = float(row.get("open", close))

        # Execute yesterday's signal at today's open.  Position sizing is
        # recalculated using the actual fill so an overnight gap cannot silently
        # invalidate the configured risk budget.
        if quantity == 0 and pending_signal is not None:
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

                    # A gap through the protective levels must be filled at the
                    # executable open, not at an impossible historical stop/target.
                    if open_price <= stop:
                        exit_price = _sell_fill(open_price, config.slippage_rate)
                        gross = quantity * exit_price
                        exit_cost = gross * config.brokerage_rate
                        cash += gross - exit_cost
                        pnl = quantity * (exit_price - entry_price) - entry_cost - exit_cost
                        trades.append({"entry": entry_price, "exit": exit_price, "quantity": quantity, "pnl": pnl, "reason": "STOP_GAP"})
                        quantity = 0
                        entry_price = stop = target = 0.0
                    elif open_price >= target:
                        exit_price = _sell_fill(open_price, config.slippage_rate)
                        gross = quantity * exit_price
                        exit_cost = gross * config.brokerage_rate
                        cash += gross - exit_cost
                        pnl = quantity * (exit_price - entry_price) - entry_cost - exit_cost
                        trades.append({"entry": entry_price, "exit": exit_price, "quantity": quantity, "pnl": pnl, "reason": "TARGET_GAP"})
                        quantity = 0
                        entry_price = stop = target = 0.0

        # Manage an existing position using only information available during
        # the current bar.  If both levels are touched, stop wins conservatively.
        if quantity:
            exit_price = None
            exit_reason = None
            if open_price <= stop:
                exit_price, exit_reason = _sell_fill(open_price, config.slippage_rate), "STOP_GAP"
            elif open_price >= target:
                exit_price, exit_reason = _sell_fill(open_price, config.slippage_rate), "TARGET_GAP"
            elif low <= stop:
                exit_price, exit_reason = _sell_fill(stop, config.slippage_rate), "STOP"
            elif high >= target:
                exit_price, exit_reason = _sell_fill(target, config.slippage_rate), "TARGET"

            if exit_price is not None:
                gross = quantity * exit_price
                exit_cost = gross * config.brokerage_rate
                cash += gross - exit_cost
                pnl = quantity * (exit_price - entry_price) - exit_cost
                trades.append({"entry": entry_price, "exit": exit_price, "quantity": quantity, "pnl": pnl, "reason": exit_reason})
                quantity = 0
                entry_price = stop = target = 0.0

        # Equity is marked after execution/exit processing.  This prevents a
        # stale pre-trade cash value from contaminating drawdown calculations.
        equity_curve.append(cash + quantity * close)

        # Only a completed bar may generate a signal.  Store it for execution
        # on the next bar, never on the same bar.
        if quantity == 0 and pending_signal is None and i >= 60:
            history = rows[: i + 1]
            closes = [float(x["close"]) for x in history]
            highs = [float(x["high"]) for x in history]
            lows = [float(x["low"]) for x in history]
            volumes = [float(x["volume"]) for x in history] if all(x.get("volume") is not None for x in history) else None
            signal = generate_regime_momentum_signal(closes, highs, lows, volumes, config.strategy)
            if signal.action == "BUY" and signal.entry and signal.stop and signal.target:
                pending_signal = signal

    # If the final bar created a signal, it has no following bar and therefore
    # must not be executed.  If a position is still open, close it at the final
    # close with conservative sell-side slippage.
    if quantity:
        final_price = _sell_fill(float(rows[-1]["close"]), config.slippage_rate)
        gross = quantity * final_price
        exit_cost = gross * config.brokerage_rate
        cash += gross - exit_cost
        pnl = quantity * (final_price - entry_price) - exit_cost
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
