from __future__ import annotations

from typing import Any, Sequence

from app.services.fno_algo_engine import build_autonomous_option_decision
from app.services.fno_strategy import FNOConfig


MIN_COMPLETED_BARS = 60


def replay_autonomous_option_decisions(
    *,
    underlying: dict[str, Any],
    bars: Sequence[dict[str, Any]],
    option_chain_snapshots: Sequence[dict[str, Any]],
    lot_size: int,
    config: FNOConfig = FNOConfig(),
    start_index: int = MIN_COMPLETED_BARS - 1,
) -> list[dict[str, Any]]:
    """Replay the autonomous F&O decision using only information available at each bar.

    ``bars[:index + 1]`` and ``option_chain_snapshots[index]`` are the complete
    information set for decision ``index``. The function deliberately does not
    inspect any future candle or future option-chain snapshot.
    """
    if len(bars) != len(option_chain_snapshots):
        raise ValueError("bars and option_chain_snapshots must have the same length")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    if start_index < MIN_COMPLETED_BARS - 1:
        start_index = MIN_COMPLETED_BARS - 1

    decisions: list[dict[str, Any]] = []
    for index in range(start_index, len(bars)):
        decision = build_autonomous_option_decision(
            underlying={**underlying, "replay_bar_index": index},
            bars=bars[: index + 1],
            option_chain=option_chain_snapshots[index],
            lot_size=lot_size,
            config=config,
        )
        decisions.append(
            {
                "bar_index": index,
                "timestamp": bars[index].get("timestamp"),
                "decision": decision,
            }
        )
    return decisions


def assert_replay_is_future_invariant(
    *,
    underlying: dict[str, Any],
    bars: Sequence[dict[str, Any]],
    option_chain_snapshots: Sequence[dict[str, Any]],
    lot_size: int,
    config: FNOConfig = FNOConfig(),
) -> None:
    """Raise if changing future bars changes any earlier replay decision.

    This is a test/qualification guard against accidental look-ahead in the
    strategy pipeline. It is intentionally deterministic and does not require
    a live broker connection.
    """
    baseline = replay_autonomous_option_decisions(
        underlying=underlying,
        bars=bars,
        option_chain_snapshots=option_chain_snapshots,
        lot_size=lot_size,
        config=config,
    )
    if len(bars) < MIN_COMPLETED_BARS + 1:
        return

    mutated = [dict(bar) for bar in bars]
    for index in range(MIN_COMPLETED_BARS, len(mutated)):
        mutated[index]["close"] = float(mutated[index].get("close", 1.0)) * 1.75
        mutated[index]["high"] = float(mutated[index].get("high", 1.0)) * 1.75
        mutated[index]["low"] = float(mutated[index].get("low", 1.0)) * 1.75

    changed = replay_autonomous_option_decisions(
        underlying=underlying,
        bars=mutated,
        option_chain_snapshots=option_chain_snapshots,
        lot_size=lot_size,
        config=config,
    )

    baseline_by_index = {item["bar_index"]: item["decision"] for item in baseline}
    changed_by_index = {item["bar_index"]: item["decision"] for item in changed}
    cutoff = len(bars) - MIN_COMPLETED_BARS
    for index in range(MIN_COMPLETED_BARS - 1, cutoff):
        if baseline_by_index[index] != changed_by_index[index]:
            raise AssertionError(f"Future-bar mutation changed replay decision at bar {index}")
