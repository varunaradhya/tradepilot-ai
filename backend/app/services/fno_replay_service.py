from __future__ import annotations

import copy
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
    timestamps = [bar.get("timestamp") for bar in bars]
    numeric_timestamps = []
    for value in timestamps:
        if value is None:
            numeric_timestamps = []
            break
        try:
            numeric_timestamps.append(float(value))
        except (TypeError, ValueError):
            raise ValueError("bar timestamps must be numeric when provided")
    if numeric_timestamps and any(current <= previous for previous, current in zip(numeric_timestamps, numeric_timestamps[1:])):
        raise ValueError("bars must be strictly chronological")
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

    mutated_chains = copy.deepcopy(option_chain_snapshots)
    for index in range(MIN_COMPLETED_BARS, len(mutated_chains)):
        chain = mutated_chains[index].get("oc") if isinstance(mutated_chains[index], dict) else None
        if isinstance(chain, dict):
            for quote_group in chain.values():
                if not isinstance(quote_group, dict):
                    continue
                for contract in quote_group.values():
                    if isinstance(contract, dict):
                        for key in ("last_price", "top_bid_price", "top_ask_price", "bid", "ask"):
                            if key in contract:
                                try:
                                    contract[key] = float(contract[key]) * 1.75
                                except (TypeError, ValueError):
                                    pass

    changed = replay_autonomous_option_decisions(
        underlying=underlying,
        bars=mutated,
        option_chain_snapshots=mutated_chains,
        lot_size=lot_size,
        config=config,
    )

    baseline_by_index = {item["bar_index"]: item["decision"] for item in baseline}
    changed_by_index = {item["bar_index"]: item["decision"] for item in changed}
    # Bars and option snapshots from MIN_COMPLETED_BARS onward are mutated.
    # Every decision strictly before that mutation boundary must remain
    # identical. This guards against future leakage from either input stream.
    mutation_start = MIN_COMPLETED_BARS
    for index in range(MIN_COMPLETED_BARS - 1, min(mutation_start, len(bars))):
        if baseline_by_index[index] != changed_by_index[index]:
            raise AssertionError(f"Future-bar mutation changed replay decision at bar {index}")
