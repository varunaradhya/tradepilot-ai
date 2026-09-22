from app.services.fno_historical_ingestion_service import (
    HistoricalOptionBar,
    build_option_chain_snapshots,
    merge_historical_option_sources,
    normalize_dhan_rolling_option_response,
)


def _response():
    return {
        "data": {
            "ce": {
                "timestamp": [1000, 1300],
                "strike": [25000, 25000],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [102.0, 104.0],
                "iv": [12.0, 12.5],
                "volume": [1000, 1200],
                "oi": [5000, 5100],
                "spot": [25010.0, 25020.0],
            }
        }
    }


def test_normalize_dhan_rolling_response():
    rows = normalize_dhan_rolling_option_response(
        _response(), strike_hint=25000, option_type="CALL"
    )
    assert len(rows) == 2
    assert rows[0].option_type == "CE"
    assert rows[0].timestamp == 1000
    assert rows[1].close == 104.0
    assert rows[0].execution_grade is False


def test_missing_side_returns_no_rows():
    rows = normalize_dhan_rolling_option_response(
        _response(), strike_hint=25000, option_type="PUT"
    )
    assert rows == []


def test_snapshots_merge_ce_and_pe_without_fake_bid_ask():
    ce = normalize_dhan_rolling_option_response(
        _response(), strike_hint=25000, option_type="CE"
    )
    pe_response = {
        "data": {
            "pe": {
                "timestamp": [1000],
                "strike": [25000],
                "close": [98.0],
                "open": [99.0],
                "high": [100.0],
                "low": [97.0],
            }
        }
    }
    pe = normalize_dhan_rolling_option_response(
        pe_response, strike_hint=25000, option_type="PE"
    )
    snapshots = build_option_chain_snapshots([*ce, *pe])
    assert len(snapshots) == 2
    assert "ce" in snapshots[0]["oc"]["25000"]
    assert "pe" in snapshots[0]["oc"]["25000"]
    assert "top_bid_price" not in snapshots[0]["oc"]["25000"]["ce"]
    assert snapshots[0]["oc"]["25000"]["ce"]["last_price"] == 102.0


def test_merge_rejects_duplicate_observation():
    row = HistoricalOptionBar(
        timestamp=1000,
        strike=25000,
        option_type="CE",
        open=100,
        high=105,
        low=99,
        close=102,
        iv=12,
        volume=1000,
        oi=5000,
        spot=25010,
    )
    try:
        merge_historical_option_sources([[row], [row]])
        assert False, "expected duplicate rejection"
    except ValueError as exc:
        assert "duplicate historical option observation" in str(exc)


def test_normalize_rejects_duplicate_timestamps():
    response = _response()
    response["data"]["ce"]["timestamp"] = [1000, 1000]
    try:
        normalize_dhan_rolling_option_response(response, strike_hint=25000, option_type="CE")
        assert False, "expected duplicate timestamp rejection"
    except ValueError as exc:
        assert "duplicate historical option timestamp" in str(exc)
