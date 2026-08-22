from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from app.services.fno_cost_service import FNOCostConfig, estimate_net_pnl
from app.services.fno_replay_service import replay_autonomous_option_decisions


@dataclass(frozen=True)
class FNOBacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade: float = 0.005
    max_capital_percent: float = 0.50
    slippage_rate: float = 0.0
    cost: FNOCostConfig = FNOCostConfig()


def _quote(contract: dict[str, Any], side: str) -> float:
    keys = ("ask", "top_ask_price", "last_price") if side == "BUY" else ("bid", "top_bid_price", "last_price")
    for key in keys:
        try:
            value = float(contract.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0.0


def _option_type(value: Any) -> str:
    return str(value or "").strip().upper()


def _find_contract(snapshot: dict[str, Any], strike: float, option_type: str) -> dict[str, Any] | None:
    """Resolve the same contract from the quote snapshot at a later bar.

    Dhan option-chain snapshots use lowercase ``ce``/``pe`` keys while our
    internal decision model stores ``CE``/``PE``. Never fall back to the
    signal-time contract: doing so would silently create stale/future fills.
    """
    side = _option_type(option_type).lower()
    if side not in {"ce", "pe"}:
        return None
    chain = snapshot.get("oc") or {}
    for raw_strike, data in chain.items():
        try:
            snapshot_strike = float(raw_strike)
        except (TypeError, ValueError):
            continue
        if snapshot_strike != float(strike):
            continue
        contract = (data or {}).get(side)
        return contract if isinstance(contract, dict) else None
    return None


def _bar_range(contract: dict[str, Any], fallback: float) -> tuple[float, float]:
    def number(key: str) -> float:
        try:
            value = float(contract.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0
        return value if value > 0 else 0.0

    low = number("low") or fallback
    high = number("high") or fallback
    return min(low, high), max(low, high)


def run_fno_backtest(
    *,
    underlying: dict[str, Any],
    bars: Sequence[dict[str, Any]],
    option_chain_snapshots: Sequence[dict[str, Any]],
    lot_size: int,
    config: FNOBacktestConfig = FNOBacktestConfig(),
) -> dict[str, Any]:
    """Replay autonomous decisions and simulate conservative next-bar option fills.

    A qualified decision at bar N is executed only from the matching contract
    in snapshot N+1. Open positions are marked/exited only from later snapshots;
    the signal-time contract is never reused as a substitute for missing data.
    """
    if config.initial_capital <= 0 or config.risk_per_trade <= 0:
        raise ValueError("invalid backtest capital/risk configuration")
    if not 0 < config.max_capital_percent <= 1:
        raise ValueError("max_capital_percent must be between 0 and 1")
    if config.slippage_rate < 0:
        raise ValueError("slippage_rate must be non-negative")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    if len(bars) != len(option_chain_snapshots):
        raise ValueError("bars and option_chain_snapshots must have the same length")

    decisions = replay_autonomous_option_decisions(
        underlying={**underlying, "capital": config.initial_capital},
        bars=bars,
        option_chain_snapshots=option_chain_snapshots,
        lot_size=lot_size,
    )
    capital = float(config.initial_capital)
    position: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []

    for item in decisions:
        index = item["bar_index"]
        decision = item["decision"]

        if position is not None:
            contract = _find_contract(option_chain_snapshots[index], position["strike"], position["option_type"])
            if contract is None:
                # Missing quote is a data-quality condition, not permission to
                # reuse an old price. Keep the position open until a valid
                # later snapshot or the end-of-test policy.
                continue
            bid = _quote(contract, "SELL")
            if bid <= 0:
                continue
            low, high = _bar_range(contract, bid)
            reason = None
            exit_price = bid * (1.0 - config.slippage_rate)
            if low <= position["stop"]:
                exit_price = position["stop"] * (1.0 - config.slippage_rate)
                reason = "STOP"
            elif high >= position["target"]:
                exit_price = position["target"] * (1.0 - config.slippage_rate)
                reason = "TARGET"
            if reason:
                pnl, costs = estimate_net_pnl(position["entry"], exit_price, position["quantity"], config.cost)
                capital += pnl
                trades.append({**position, "exit": round(exit_price, 4), "pnl": round(pnl, 2), "costs": costs, "reason": reason, "exit_bar_index": index})
                position = None
                continue

        if position is None and decision.get("decision") == "QUALIFIED" and index + 1 < len(option_chain_snapshots):
            signal_contract = decision.get("contract") or {}
            strike = float(signal_contract.get("strike") or 0)
            option_type = _option_type(signal_contract.get("option_type") or signal_contract.get("type"))
            if strike <= 0 or option_type not in {"CE", "PE"}:
                continue

            # The signal is observed at N; execution is based on the matching
            # executable quote available at N+1. This prevents same-bar fills.
            entry_contract = _find_contract(option_chain_snapshots[index + 1], strike, option_type)
            if entry_contract is None:
                continue
            entry = _quote(entry_contract, "BUY") * (1.0 + config.slippage_rate)
            quantity = int(decision.get("quantity") or 0)
            stop = float(decision.get("stop") or 0)
            target = float(decision.get("target") or 0)
            if entry <= 0 or quantity <= 0 or quantity % lot_size or not 0 < stop < entry < target:
                continue
            if entry * quantity > capital * config.max_capital_percent:
                continue
            risk, _ = estimate_net_pnl(entry, stop, quantity, config.cost)
            if abs(risk) > capital * config.risk_per_trade:
                continue
            position = {
                "entry_signal_bar_index": index,
                "entry_bar_index": index + 1,
                "entry": entry,
                "stop": stop,
                "target": target,
                "quantity": quantity,
                "lots": quantity // lot_size,
                "strike": strike,
                "option_type": option_type,
                "contract": entry_contract,
                "direction": decision.get("direction"),
                "underlying": underlying.get("symbol"),
            }

    if position is not None:
        # End-of-test liquidation must use the final available quote for the
        # actual contract, never the stale entry snapshot.
        final_contract = _find_contract(option_chain_snapshots[-1], position["strike"], position["option_type"])
        if final_contract is not None:
            bid = _quote(final_contract, "SELL")
            if bid > 0:
                exit_price = bid * (1.0 - config.slippage_rate)
                pnl, costs = estimate_net_pnl(position["entry"], exit_price, position["quantity"], config.cost)
                capital += pnl
                trades.append({**position, "exit": round(exit_price, 4), "pnl": round(pnl, 2), "costs": costs, "reason": "END_OF_TEST", "exit_bar_index": len(bars) - 1})

    wins = [float(t["pnl"]) for t in trades if t["pnl"] > 0]
    losses = [float(t["pnl"]) for t in trades if t["pnl"] < 0]
    gross_profit, gross_loss = sum(wins), abs(sum(losses))
    equity = [float(config.initial_capital)]
    running = float(config.initial_capital)
    for trade in trades:
        running += float(trade["pnl"])
        equity.append(running)
    peak = equity[0]
    max_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)

    return {
        "initial_capital": round(config.initial_capital, 2),
        "ending_capital": round(capital, 2),
        "return_percent": round((capital / config.initial_capital - 1.0) * 100.0, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (None if not gross_profit else float("inf")),
        "expectancy_per_trade": round(sum(float(t["pnl"]) for t in trades) / len(trades), 2) if trades else 0.0,
        "max_drawdown_percent": round(max_drawdown, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "trades_detail": trades,
        "equity_curve": [round(value, 2) for value in equity],
    }
