from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward


def _rows(n=120):
    rows = []
    for i in range(n):
        close = 100 + i * 0.2
        rows.append({
            "session": f"D{i // 40}",
            "open": close - 0.05,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": 1000 + i * 5,
            "market_close": close * 0.999,
            "sector_close": close * 1.001,
        })
    return rows


def test_fixed_parameter_walk_forward_is_chronological_and_oos():
    result = run_fixed_parameter_walk_forward(_rows(), train_size=60, validation_size=20)
    assert result["parameter_selection"] is False
    assert result["windows"] == 3
    windows = result["v1"]["windows"]
    assert windows[0]["train_end"] == windows[0]["validation_start"]
    assert windows[0]["validation_end"] == windows[1]["validation_start"]
    assert windows[1]["validation_end"] == windows[2]["validation_start"]


def test_fixed_parameter_walk_forward_reports_both_versions():
    result = run_fixed_parameter_walk_forward(_rows(), train_size=60, validation_size=20)
    assert result["v1"]["summary"]["windows"] == result["v2"]["summary"]["windows"]
    assert len(result["comparison"]) == result["windows"]


def test_walk_forward_rejects_insufficient_data_at_service_level():
    result = run_fixed_parameter_walk_forward(_rows(30), train_size=20, validation_size=20, config=IntradayBacktestConfig())
    assert result["windows"] == 0
    assert result["v1"]["summary"]["success_rate_percent"] == 0.0
