from app.services.walk_forward_service import build_walk_forward_windows, run_walk_forward, summarize_walk_forward


def test_walk_forward_windows_are_chronological_and_non_overlapping():
    windows = build_walk_forward_windows(20, train_size=8, validation_size=4)
    assert len(windows) == 3
    assert windows[0].train_end == windows[0].validation_start
    assert windows[0].validation_end == windows[1].train_start


def test_walk_forward_never_leaks_validation_into_train():
    rows = list(range(20))

    def evaluator(train, validation):
        assert max(train) < min(validation)
        return {"return_percent": 1}

    results = run_walk_forward(rows, 8, 4, evaluator)
    assert len(results) == 3
    assert summarize_walk_forward(results)["success_rate_percent"] == 100.0


def test_walk_forward_empty_for_insufficient_data():
    assert build_walk_forward_windows(10, 8, 4) == []
