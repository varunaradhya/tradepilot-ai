from datetime import datetime, timezone

from app.services.dataset_provenance import DatasetProvenance, fingerprint_market_bars
from app.services.historical_data_service import MarketBar


def _bars():
    return [
        MarketBar(datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc), 100, 101, 99, 100.5, 10),
        MarketBar(datetime(2026, 1, 5, 9, 20, tzinfo=timezone.utc), 100.5, 102, 100, 101.5, 12),
    ]


def test_dataset_fingerprint_is_deterministic():
    bars = _bars()
    first = fingerprint_market_bars(bars, symbol="TCS", timeframe="5m")
    second = fingerprint_market_bars(list(bars), symbol="TCS", timeframe="5m")
    assert first == second
    assert len(first) == 64


def test_dataset_provenance_contains_reproducibility_fields():
    bars = _bars()
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
    payload = provenance.as_dict()
    assert payload["dataset_id"] == "nse/TCS_5m"
    assert payload["row_count"] == 2
    assert payload["start"] < payload["end"]
    assert len(payload["content_fingerprint"]) == 64
