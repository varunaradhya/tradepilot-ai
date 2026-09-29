from datetime import datetime, timezone
from pathlib import Path
from app.services.historical_data_service import MarketBar
from app.services.research_store import ResearchStore

def bar(ts,close):
    return MarketBar(datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),close-0.5,close+0.5,close-1,close,1000)

def test_incremental_merge_replaces_overlap_and_preserves_history(tmp_path: Path):
    store=ResearchStore(tmp_path)
    store.save("nse/TCS_test",[bar("2026-01-01T09:15:00",100),bar("2026-01-01T09:20:00",101)])
    result=store.merge("nse/TCS_test",[bar("2026-01-01T09:20:00",105),bar("2026-01-01T09:25:00",106)])
    rows=store.load("nse/TCS_test")
    assert result["bars"]==3
    assert [r.close for r in rows]==[100,105,106]

def test_provenance_sidecar_is_written_and_read(tmp_path: Path):
    from app.services.dataset_provenance import DatasetProvenance, fingerprint_market_bars

    store = ResearchStore(tmp_path)
    bars = [bar("2026-01-05T09:15:00", 100)]
    provenance = DatasetProvenance.create(
        dataset_id="nse/TCS_5m",
        source="csv",
        symbol="TCS",
        timeframe="5m",
        bars=bars,
        quality_status="VALID",
        content_fingerprint=fingerprint_market_bars(bars, symbol="TCS", timeframe="5m"),
        import_method="csv",
    )
    store.save_with_provenance("nse/TCS_5m", bars, provenance)

    loaded = store.get_provenance("nse/TCS_5m")
    assert loaded is not None
    assert loaded["content_fingerprint"] == provenance.content_fingerprint
