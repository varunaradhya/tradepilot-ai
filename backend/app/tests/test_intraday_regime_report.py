from app.services.intraday_regime_report import build_intraday_regime_report


def rows():
    return [{"open":100+i*0.2,"high":100+i*0.2+0.2,"low":100+i*0.2-0.2,"close":100+i*0.2,"volume":1000.0,"session":"2026-01-02"} for i in range(50)]


def test_regime_report_has_v1_v2_comparison():
    result = build_intraday_regime_report(rows(), rows(), rows())
    assert result["status"] == "OK"
    assert "v1" in result["comparison"]
    assert "v2" in result["comparison"]
    assert result["optimization_performed"] is False


def test_empty_regime_report_is_safe():
    assert build_intraday_regime_report([])["status"] == "NO_DATA"
