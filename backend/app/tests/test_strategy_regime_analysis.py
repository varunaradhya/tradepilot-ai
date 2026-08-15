import pytest

from app.services.strategy_regime_analysis import regime_report, summarize_regimes


def test_regime_summary_is_grouped_and_stable():
    result = summarize_regimes(
        ["TRENDING_UP", "SIDEWAYS", "TRENDING_UP", "TRENDING_DOWN"],
        [100, -20, -40, 30],
    )
    assert [item.regime for item in result] == ["SIDEWAYS", "TRENDING_DOWN", "TRENDING_UP"]
    up = next(item for item in result if item.regime == "TRENDING_UP")
    assert up.trades == 2
    assert up.wins == 1
    assert up.losses == 1
    assert up.net_pnl == pytest.approx(60)


def test_regime_profit_factor_and_win_rate_are_calculated():
    result = summarize_regimes(["TRENDING_UP"] * 3, [100, 50, -50])[0]
    assert result.win_rate == pytest.approx(66.6666667)
    assert result.profit_factor == pytest.approx(3.0)


def test_regime_input_length_is_validated():
    with pytest.raises(ValueError, match="equal length"):
        summarize_regimes(["SIDEWAYS"], [1, 2])


def test_regime_report_is_descriptive_not_an_optimizer():
    report = regime_report(["SIDEWAYS", "TRENDING_UP"], [-10, 20])
    assert report["selection_policy"] == "descriptive_only_no_regime_optimization"
    assert len(report["regimes"]) == 2
