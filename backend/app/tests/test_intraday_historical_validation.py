import pytest

from app.services.intraday_backtest import IntradayBacktestConfig
from app.services.intraday_historical_validation import HistoricalValidationConfig, validate_historical_datasets


def _rows(days=4, bars_per_day=3):
    rows = []
    for day in range(1, days + 1):
        for minute in range(bars_per_day):
            price = 100 + day + minute
            rows.append({
                "session": f"2026-01-{day:02d}",
                "timestamp": f"2026-01-{day:02d} 09:{15 + minute * 5:02d}:00",
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price + 0.5,
                "volume": 1000,
            })
    return rows


def test_historical_validation_splits_at_session_boundary():
    result = validate_historical_datasets(
        {"TCS": _rows()},
        IntradayBacktestConfig(),
        HistoricalValidationConfig(train_fraction=0.5, min_train_bars=1, min_test_bars=1),
    )
    item = result["ranked"][0]
    assert item["train"]["bars"] == 6
    assert item["out_of_sample"]["bars"] == 6


def test_historical_validation_never_tunes_parameters():
    result = validate_historical_datasets(
        {"TCS": _rows()},
        IntradayBacktestConfig(),
        HistoricalValidationConfig(train_fraction=0.75, min_train_bars=1, min_test_bars=1),
    )
    assert result["assumptions"]["parameter_selection"] is False
    assert result["assumptions"]["cross_stock_optimization"] is False
    assert "fixed parameters" in result["method"]


def test_historical_validation_reports_missing_trade_evidence():
    result = validate_historical_datasets(
        {"TCS": _rows(2, 2)},
        IntradayBacktestConfig(),
        HistoricalValidationConfig(train_fraction=0.5, min_train_bars=1, min_test_bars=1),
    )
    assert "NO_OUT_OF_SAMPLE_TRADES" in result["ranked"][0]["reasons"]
    assert result["ranked"][0]["status"] == "REVIEW"


def test_historical_validation_empty_input_is_safe():
    result = validate_historical_datasets({}, IntradayBacktestConfig())
    assert result["status"] == "NO_DATA"
    assert result["summary"]["symbols_tested"] == 0
    assert result["ranked"] == []


def test_historical_validation_rejects_invalid_fraction():
    with pytest.raises(ValueError):
        validate_historical_datasets(
            {"TCS": _rows()},
            IntradayBacktestConfig(),
            HistoricalValidationConfig(train_fraction=0.4),
        )
