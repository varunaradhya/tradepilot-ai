import pytest

from app.services.strategy_quality_research import (
    compare_train_oos_quality_thresholds,
    evaluate_quality_thresholds,
)


def test_threshold_report_is_deterministic_and_sorted():
    result = evaluate_quality_thresholds([40, 70, 90], [10, -5, 20], [80, 50, 70])
    assert [item.threshold for item in result] == [50, 70, 80]
    assert result[0].trades == 2
    assert result[1].trades == 2
    assert result[2].trades == 1


def test_threshold_metrics_calculate_win_rate_and_profit_factor():
    result = evaluate_quality_thresholds([60, 80, 90], [100, -50, 150], [60])[0]
    assert result.trades == 3
    assert result.wins == 2
    assert result.losses == 1
    assert result.win_rate == pytest.approx(66.6666667)
    assert result.profit_factor == pytest.approx(5.0)
    assert result.net_pnl == pytest.approx(200.0)


def test_threshold_metrics_calculate_drawdown_in_trade_order():
    result = evaluate_quality_thresholds([80, 80, 80], [100, -160, 50], [80])[0]
    assert result.max_drawdown == pytest.approx(160.0)


def test_mismatched_score_and_pnl_lengths_are_rejected():
    with pytest.raises(ValueError, match="equal length"):
        evaluate_quality_thresholds([60, 70], [10])


def test_invalid_thresholds_are_rejected():
    with pytest.raises(ValueError, match="between 0 and 100"):
        evaluate_quality_thresholds([60], [10], [-1, 101])


def test_train_oos_report_does_not_select_a_threshold():
    report = compare_train_oos_quality_thresholds(
        [60, 80], [10, -5],
        [60, 80], [20, -2],
        [60, 80],
    )
    assert report["thresholds"] == [60, 80]
    assert report["selection_policy"] == "descriptive_only_no_threshold_optimization"
    assert len(report["train"]) == 2
    assert len(report["oos"]) == 2
