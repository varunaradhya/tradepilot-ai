from app.services.fno_qualification_service import QualificationConfig, qualify_walk_forward


def _trades(values):
    return [{"pnl": value} for value in values]


def test_walk_forward_requires_oos_evidence():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 30),
        out_of_sample_trades=_trades([]),
    )
    assert result["qualified"] is False
    assert result["gates"]["oos_min_trades"] is False


def test_walk_forward_uses_frozen_oos_results_without_optimizing():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 20 + [-50.0] * 10),
        out_of_sample_trades=_trades([80.0] * 10),
        config=QualificationConfig(min_trades=30, min_oos_trades=10, min_profit_factor=1.2),
    )
    assert result["qualified"] is True
    assert result["in_sample"]["trades"] == 30
    assert result["out_of_sample"]["trades"] == 10


def test_walk_forward_rejects_excessive_drawdown():
    result = qualify_walk_forward(
        in_sample_trades=_trades([100.0] * 30),
        out_of_sample_trades=_trades([100.0, -1000.0] * 5),
        config=QualificationConfig(min_trades=30, min_oos_trades=10, max_drawdown_percent=20.0),
    )
    assert result["qualified"] is False
    assert result["gates"]["oos_drawdown"] is False
