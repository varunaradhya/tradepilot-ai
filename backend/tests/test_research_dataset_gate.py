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
