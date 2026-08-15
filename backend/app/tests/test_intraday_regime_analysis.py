from app.services.intraday_regime_analysis import build_benchmark_regime_analysis


def _rows(n=100):
    return [{"timestamp": f"2026-01-01T09:{i % 60:02d}:00", "close": 100 + i * 0.2} for i in range(n)]


def test_regime_analysis_is_chronological_and_no_lookahead():
    result = build_benchmark_regime_analysis(_rows())
    assert result["status"] == "OK"
    assert result["lookahead_bias_protection"] is True
    timestamps = [item["timestamp"] for item in result["observations"]]
    assert timestamps == sorted(timestamps)
    assert sum(item["observations"] for item in result["distribution"].values()) == len(timestamps)


def test_regime_analysis_handles_insufficient_data():
    result = build_benchmark_regime_analysis(_rows(20))
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["observations"] == []


def test_regime_analysis_rejects_invalid_configuration():
    try:
        build_benchmark_regime_analysis(_rows(), lookback=10)
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid lookback to fail")
