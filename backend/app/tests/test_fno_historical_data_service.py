from app.services.fno_historical_data_service import (
    HistoricalFNODataConfig,
    validate_historical_dataset,
    validate_historical_snapshot,
)


def _snapshot(timestamp=1000.0, bid=99.0, ask=100.0):
    return {
        "timestamp": timestamp,
        "oc": {
            "25000": {
                "ce": {"top_bid_price": bid, "top_ask_price": ask},
                "pe": {"top_bid_price": bid, "top_ask_price": ask},
            }
        },
    }


def test_snapshot_rejects_future_quote():
    result = validate_historical_snapshot(snapshot=_snapshot(1001), decision_timestamp=1000)
    assert result["valid"] is False
    assert result["reason"] == "FUTURE_QUOTE"


def test_snapshot_requires_executable_bid_ask():
    result = validate_historical_snapshot(
        snapshot=_snapshot(1000, bid=0, ask=0),
        decision_timestamp=1000,
        config=HistoricalFNODataConfig(require_bid_ask_for_execution=True),
    )
    assert result["valid"] is False
    assert result["reason"] == "NO_EXECUTABLE_QUOTES"


def test_dataset_requires_aligned_monotonic_bars_and_snapshots():
    bars = [{"timestamp": 1000}, {"timestamp": 1300}]
    result = validate_historical_dataset(bars=bars, snapshots=[_snapshot(1000), _snapshot(1300)])
    assert result["valid"] is True
    assert result["invalid_count"] == 0


def test_dataset_rejects_non_monotonic_bars():
    bars = [{"timestamp": 1300}, {"timestamp": 1000}]
    result = validate_historical_dataset(bars=bars, snapshots=[_snapshot(1300), _snapshot(1000)])
    assert result["valid"] is False
    assert result["invalid_rows"][0]["reason"] == "NON_MONOTONIC_BAR_TIMESTAMP"


def test_dataset_rejects_length_mismatch():
    result = validate_historical_dataset(bars=[{"timestamp": 1000}], snapshots=[])
    assert result["valid"] is False
    assert result["reason"] == "LENGTH_MISMATCH"
