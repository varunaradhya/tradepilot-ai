from app.services.walk_forward_service import build_walk_forward_windows, run_walk_forward, summarize_walk_forward


def test_walk_forward_windows_are_chronological_with_non_overlapping_validation_periods():
    windows = build_walk_forward_windows(20, train_size=8, validation_size=4)
    assert len(windows) == 3
    assert windows[0].train_end == windows[0].validation_start
    assert windows[0].validation_end == windows[1].validation_start
    assert windows[1].validation_end == windows[2].validation_start
    assert windows[0].train_start < windows[1].train_start < windows[2].train_start


def test_walk_forward_allows_exactly_one_train_validation_window():
    windows = build_walk_forward_windows(12, train_size=8, validation_size=4)
    assert len(windows) == 1
    assert (windows[0].train_start, windows[0].train_end, windows[0].validation_start, windows[0].validation_end) == (0, 8, 8, 12)


def test_walk_forward_never_leaks_validation_into_train():
    rows = list(range(20))

    def evaluator(train, validation):
        assert max(train) < min(validation)
        return {"return_percent": 1}

    results = run_walk_forward(rows, 8, 4, evaluator)
    assert len(results) == 3
    assert summarize_walk_forward(results)["success_rate_percent"] == 100.0


def test_walk_forward_malformed_result_is_not_counted_as_success():
    results = [
        {"result": {"return_percent": "not-a-number"}},
        {"result": {"return_percent": -1}},
        {"result": {"return_percent": 2}},
    ]
    summary = summarize_walk_forward(results)
    assert summary["windows"] == 3
    assert summary["successful_windows"] == 1
    assert summary["success_rate_percent"] == 33.33


def test_walk_forward_empty_for_insufficient_data():
    assert build_walk_forward_windows(10, 8, 4) == []
