from datetime import datetime, timezone

import pytest

from app.services.dataset_provenance import fingerprint_market_bars
from app.services.historical_data_service import MarketBar
from app.services.research_dataset_gate import require_certified_dataset
from app.services.research_store import ResearchStore


def _bars():
    return [
        MarketBar(datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc), 100, 101, 99, 100.5, 10),
        MarketBar(datetime(2026, 1, 5, 9, 20, tzinfo=timezone.utc), 100.5, 102, 100, 101.5, 12),
    ]


def _provenance(bars, corporate_action_adjusted):
    return {
        "dataset_id": "nse/TCS_5m",
        "symbol": "TCS",
        "timeframe": "5m",
        "quality_status": "VALID",
        "content_fingerprint": fingerprint_market_bars(bars, symbol="TCS", timeframe="5m"),
        "corporate_action_adjusted": corporate_action_adjusted,
    }


def test_certified_dataset_requires_matching_provenance(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars()
    store.save("nse/TCS_5m", bars)
    with pytest.raises(ValueError, match="missing provenance"):
        require_certified_dataset("nse/TCS_5m", store=store)


def test_certified_dataset_requires_explicit_corporate_action_state(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars()
    store.save_with_provenance(
        "nse/TCS_5m",
        bars,
        type("P", (), {
            "dataset_id": "nse/TCS_5m",
            "as_dict": lambda self: _provenance(bars, None),
        })(),
    )
    with pytest.raises(ValueError, match="corporate-action"):
        require_certified_dataset("nse/TCS_5m", store=store)


def test_certified_dataset_rejects_fingerprint_mismatch(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars()
    store.save_with_provenance(
        "nse/TCS_5m",
        bars,
        type("P", (), {
            "dataset_id": "nse/TCS_5m",
            "as_dict": lambda self: {**_provenance(bars, False), "content_fingerprint": "0" * 64},
        })(),
    )
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        require_certified_dataset("nse/TCS_5m", store=store)


def test_certified_dataset_accepts_explicit_adjustment_state(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars()
    store.save_with_provenance(
        "nse/TCS_5m",
        bars,
        type("P", (), {
            "dataset_id": "nse/TCS_5m",
            "as_dict": lambda self: _provenance(bars, False),
        })(),
    )
    loaded, provenance = require_certified_dataset("nse/TCS_5m", store=store)
    assert len(loaded) == 2
    assert provenance["corporate_action_adjusted"] is False


def _save_certified(store, bars, corporate_action_adjusted=False):
    store.save_with_provenance(
        "nse/TCS_5m",
        bars,
        type("P", (), {
            "dataset_id": "nse/TCS_5m",
            "as_dict": lambda self: _provenance(bars, corporate_action_adjusted),
        })(),
    )


def test_certified_dataset_rejects_weekend_bars(tmp_path):
    store = ResearchStore(tmp_path)
    bars = [
        MarketBar(datetime(2026, 1, 3, 9, 15, tzinfo=timezone.utc), 100, 101, 99, 100.5, 10),
        MarketBar(datetime(2026, 1, 3, 9, 20, tzinfo=timezone.utc), 100.5, 102, 100, 101.5, 12),
    ]
    _save_certified(store, bars)
    with pytest.raises(ValueError, match="unknown_session_bars=2"):
        require_certified_dataset("nse/TCS_5m", store=store)


class RawCertifiedStore:
    def __init__(self, bars):
        self.bars = bars

    def load(self, dataset):
        return self.bars

    def get_provenance(self, dataset):
        return _provenance(self.bars, False)


def test_certified_dataset_rejects_negative_volume(tmp_path):
    bars = _bars()
    bars[1] = MarketBar(bars[1].timestamp, bars[1].open, bars[1].high, bars[1].low, bars[1].close, -1)
    store = RawCertifiedStore(bars)
    with pytest.raises(ValueError, match="negative_volume_bars=1"):
        require_certified_dataset("nse/TCS_5m", store=store)


def test_certified_dataset_rejects_outside_regular_session(tmp_path):
    store = ResearchStore(tmp_path)
    bars = [
        MarketBar(datetime(2026, 1, 5, 3, 0, tzinfo=timezone.utc), 100, 101, 99, 100.5, 10),
        MarketBar(datetime(2026, 1, 5, 3, 5, tzinfo=timezone.utc), 100.5, 102, 100, 101.5, 12),
    ]
    _save_certified(store, bars)
    with pytest.raises(ValueError, match="outside_session_bars=2"):
        require_certified_dataset("nse/TCS_5m", store=store)


def _bars_for_day(day, start_hour, start_minute, count):
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    start = datetime(
        day.year, day.month, day.day, start_hour, start_minute,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )
    return [
        MarketBar(start + timedelta(minutes=5 * index), 100, 101, 99, 100.5, 10)
        for index in range(count)
    ]


def test_certified_dataset_accepts_known_live_muhurat_session(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars_for_day(datetime(2023, 11, 12).date(), 18, 15, 12)
    _save_certified(store, bars)
    loaded, _ = require_certified_dataset("nse/TCS_5m", store=store)
    assert len(loaded) == 12


def test_certified_dataset_rejects_known_mock_session(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars_for_day(datetime(2022, 4, 9).date(), 11, 15, 2)
    _save_certified(store, bars)
    with pytest.raises(ValueError, match="mock_session_bars=2"):
        require_certified_dataset("nse/TCS_5m", store=store)


def test_certified_dataset_accepts_multi_window_live_special_session(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars_for_day(datetime(2024, 3, 2).date(), 11, 30, 12)
    _save_certified(store, bars)
    loaded, _ = require_certified_dataset("nse/TCS_5m", store=store)
    assert len(loaded) == 12


def test_certified_dataset_rejects_unknown_weekend_session(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars_for_day(datetime(2026, 10, 3).date(), 9, 15, 2)
    _save_certified(store, bars)
    with pytest.raises(ValueError, match="unknown_session_bars=2"):
        require_certified_dataset("nse/TCS_5m", store=store)


def test_certified_dataset_rejects_outside_special_session_window(tmp_path):
    store = ResearchStore(tmp_path)
    bars = _bars_for_day(datetime(2024, 3, 2).date(), 10, 5, 2)
    _save_certified(store, bars)
    with pytest.raises(ValueError, match="outside_session_bars=2"):
        require_certified_dataset("nse/TCS_5m", store=store)
