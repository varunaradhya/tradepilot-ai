from app.services.fno_execution_evidence_service import (
    build_execution_grade_snapshots,
    normalize_execution_quotes,
    validate_execution_quote_coverage,
)


def _row(**overrides):
    row = {
        "timestamp": 100,
        "strike": 25000,
        "option_type": "CE",
        "bid": 99.5,
        "ask": 100.0,
        "spot": 25010,
        "expiry": "2026-10-01",
        "security_id": "12345",
            "exchange_segment": "NSE_FNO",
        "source": "vendor_x",
        "exchange_segment": "NSE_FNO",
    }
    row.update(overrides)
    return row


def test_execution_quotes_require_real_bid_ask():
    rows = normalize_execution_quotes([_row()])
    assert rows[0].bid == 99.5
    assert rows[0].ask == 100.0
    assert rows[0].source == "vendor_x"


def test_execution_quotes_preserve_contract_identity():
    rows = normalize_execution_quotes([_row()])
    assert rows[0].expiry == "2026-10-01"
    assert rows[0].security_id == "12345"
    assert rows[0].exchange_segment == "NSE_FNO"


def test_execution_quotes_reject_explicit_blank_contract_identity():
    import pytest

    with pytest.raises(ValueError, match="security_id cannot be empty"):
        normalize_execution_quotes([_row(security_id="")])


def test_execution_quotes_never_fallback_to_close():
    import pytest

    with pytest.raises(ValueError, match="positive bid and ask"):
        normalize_execution_quotes([_row(bid=None, ask=None, close=100.0)])


def test_execution_quotes_reject_inverted_quotes():
    import pytest

    with pytest.raises(ValueError, match="inverted"):
        normalize_execution_quotes([_row(bid=101, ask=100)])


def test_execution_quotes_reject_future_or_unaligned_timestamp():
    import pytest

    with pytest.raises(ValueError, match="timestamp-aligned"):
        normalize_execution_quotes([_row(timestamp=101)], expected_timestamps={100})


def test_execution_quotes_reject_duplicates():
    import pytest

    with pytest.raises(ValueError, match="duplicate"):
        normalize_execution_quotes([_row(), _row()])


def test_execution_quote_coverage_reports_missing_without_repair():
    rows = normalize_execution_quotes([
        _row(timestamp=100),
    ])
    result = validate_execution_quote_coverage(rows, expected_timestamps={100, 160})
    assert result["valid"] is False
    assert result["missing_timestamps"] == [160]
    assert result["unexpected_timestamps"] == []


def test_execution_grade_snapshots_preserve_executable_quotes():
    rows = normalize_execution_quotes([
        _row(timestamp=100, option_type="CE"),
        _row(timestamp=100, option_type="PE", bid=101, ask=101.5),
    ])
    snapshots = build_execution_grade_snapshots(rows)

    assert len(snapshots) == 1
    assert snapshots[0]["execution_grade"] is True
    assert snapshots[0]["oc"]["25000"]["ce"]["top_bid_price"] == 99.5
    assert snapshots[0]["oc"]["25000"]["ce"]["top_ask_price"] == 100.0
    assert snapshots[0]["oc"]["25000"]["pe"]["top_bid_price"] == 101.0


def test_execution_quotes_reject_non_positive_timestamp():
    import pytest
    with pytest.raises(ValueError, match="positive timestamp"):
        normalize_execution_quotes([_row(timestamp=0)])
