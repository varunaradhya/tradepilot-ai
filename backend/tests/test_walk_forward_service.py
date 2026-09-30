from __future__ import annotations

import pytest

from app.services.walk_forward_service import build_walk_forward_windows, run_walk_forward


def test_exact_fit_produces_one_walk_forward_window() -> None:
    windows = build_walk_forward_windows(length=10, train_size=6, validation_size=4)

    assert windows == [
        type(windows[0])(train_start=0, train_end=6, validation_start=6, validation_end=10)
    ]


def test_overlapping_validation_windows_are_rejected() -> None:
    with pytest.raises(ValueError, match="validation_size"):
        build_walk_forward_windows(length=30, train_size=10, validation_size=10, step=5)


def test_default_windows_are_chronological_and_non_overlapping() -> None:
    windows = build_walk_forward_windows(length=30, train_size=10, validation_size=5)

    assert len(windows) == 4
    for previous, current in zip(windows, windows[1:]):
        assert previous.validation_end <= current.train_start
        assert previous.train_end <= previous.validation_start
