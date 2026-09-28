from app.services.research_data_quality import analyze_intraday_quality


def test_quality_accepts_clean_ohlc():
    rows=[{"timestamp":"2026-01-01T09:15:00","session":"2026-01-01","open":100,"high":102,"low":99,"close":101,"volume":1000}]
    result=analyze_intraday_quality(rows)
    assert result["valid"] is True
    assert result["duplicates"]==0


def test_quality_rejects_duplicate_and_invalid_bars():
    rows=[{"timestamp":"2026-01-01T09:15:00","open":100,"high":99,"low":98,"close":101,"volume":1000}]
    rows.append(dict(rows[0]))
    result=analyze_intraday_quality(rows)
    assert result["valid"] is False
    assert result["duplicates"]==1
    assert result["invalid_ohlc"]==2
