from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: int
    train_end: int
    validation_start: int
    validation_end: int


def build_walk_forward_windows(
    length: int,
    train_size: int,
    validation_size: int,
    step: int | None = None,
) -> list[WalkForwardWindow]:
    """Create chronological train/validation windows with no look-ahead."""
    if train_size <= 0 or validation_size <= 0 or length <= train_size + validation_size:
        return []
    step = validation_size if step is None else step
    if step <= 0:
        raise ValueError("step must be positive")

    windows: list[WalkForwardWindow] = []
    start = 0
    while start + train_size + validation_size <= length:
        train_end = start + train_size
        validation_end = train_end + validation_size
        windows.append(WalkForwardWindow(start, train_end, train_end, validation_end))
        start += step
    return windows


def run_walk_forward(
    rows: Sequence[T],
    train_size: int,
    validation_size: int,
    evaluator: Callable[[Sequence[T], Sequence[T]], R],
    step: int | None = None,
) -> list[dict]:
    """Evaluate each chronological window; validation data is never passed to training."""
    windows = build_walk_forward_windows(len(rows), train_size, validation_size, step)
    results: list[dict] = []
    for number, window in enumerate(windows, start=1):
        train = rows[window.train_start:window.train_end]
        validation = rows[window.validation_start:window.validation_end]
        results.append(
            {
                "window": number,
                "train_start": window.train_start,
                "train_end": window.train_end,
                "validation_start": window.validation_start,
                "validation_end": window.validation_end,
                "result": evaluator(train, validation),
            }
        )
    return results


def summarize_walk_forward(results: Sequence[dict]) -> dict:
    """Summarize validation outcomes without hiding failed windows."""
    if not results:
        return {"windows": 0, "successful_windows": 0, "success_rate_percent": 0.0}
    successful = 0
    for result in results:
        value = result.get("result")
        if isinstance(value, dict) and float(value.get("return_percent", 0.0)) > 0:
            successful += 1
    return {
        "windows": len(results),
        "successful_windows": successful,
        "success_rate_percent": round(successful / len(results) * 100, 2),
    }
