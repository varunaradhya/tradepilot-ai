from datetime import datetime, timezone
from pathlib import Path
from app.services.historical_data_service import MarketBar
from app.services.research_store import ResearchStore

def bar(ts,close):
    return MarketBar(datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),100,101,99,close,1000)

def test_incremental_merge_replaces_overlap_and_preserves_history(tmp_path: Path):
    store=ResearchStore(tmp_path)
    store.save("nse/TCS_test",[bar("2026-01-01T09:15:00",100),bar("2026-01-01T09:20:00",101)])
    result=store.merge("nse/TCS_test",[bar("2026-01-01T09:20:00",105),bar("2026-01-01T09:25:00",106)])
    rows=store.load("nse/TCS_test")
    assert result["bars"]==3
    assert [r.close for r in rows]==[100,105,106]
