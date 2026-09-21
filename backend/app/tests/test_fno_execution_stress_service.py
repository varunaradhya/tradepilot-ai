from app.services import fno_execution_stress_service as stress


def test_fno_execution_stress_runs_frozen_scenarios(monkeypatch):
    calls = []

    def fake_backtest(**kwargs):
        calls.append(kwargs["config"])
        return {
            "return_percent": 1.0,
            "profit_factor": 1.2,
            "expectancy_per_trade": 10.0,
            "max_drawdown_percent": 2.0,
            "trades": 4,
        }

    monkeypatch.setattr(stress, "run_fno_backtest", fake_backtest)
    result = stress.run_fno_execution_stress(
        underlying={"symbol": "NIFTY"},
        bars=[],
        option_chain_snapshots=[],
        lot_size=75,
        slippage_rates=(0.0, 0.001),
        spread_limits=(None, 1.5),
    )

    assert result["scenario_count"] == 4
    assert len(calls) == 4
    assert calls[0].slippage_rate == 0.0
    assert calls[-1].max_spread_percent == 1.5

def test_execution_stress_rejects_negative_slippage_before_backtests(monkeypatch):
    monkeypatch.setattr(stress, "run_fno_backtest", lambda **kwargs: (_ for _ in ()).throw(AssertionError("must validate first")))
    try:
        stress.run_fno_execution_stress(
            underlying={"symbol": "NIFTY"},
            bars=[],
            option_chain_snapshots=[],
            lot_size=75,
            slippage_rates=(-0.001,),
            spread_limits=(None,),
        )
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("expected negative slippage to fail")
