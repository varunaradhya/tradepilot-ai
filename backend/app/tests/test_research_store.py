from datetime import datetime, timezone

from app.services.historical_data_service import MarketBar
from app.services.research_store import ResearchStore


def bars():
    return [
        MarketBar(datetime(2025, 1, 2, tzinfo=timezone.utc), 100, 102, 99, 101, 1000),
        MarketBar(datetime(2025, 1, 3, tzinfo=timezone.utc), 101, 104, 100, 103, 1200),
    ]


def test_save_and_load_round_trip(tmp_path):
    store = ResearchStore(tmp_path)
    result = store.save("nse/tcs_daily", bars())
    assert result["valid"] is True
    loaded = store.load("nse/tcs_daily")
    assert len(loaded) == 2
    assert loaded[0].close == 101
    assert loaded[1].volume == 1200


def test_invalid_dataset_name_is_rejected(tmp_path):
    store = ResearchStore(tmp_path)
    try:
        store.load("../escape")
    except ValueError:
        pass
    else:
        raise AssertionError("Path traversal dataset name was accepted")
