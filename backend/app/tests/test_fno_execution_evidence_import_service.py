import hashlib

import pytest

from app.services.fno_execution_evidence_import_service import (
    import_execution_evidence_csv,
    parse_execution_quote_csv,
    sha256_bytes,
)


CSV = (
    "timestamp,strike,option_type,bid,ask,spot,expiry,security_id,exchange_segment,source\n"
    "100,25000,CE,99.5,100,25010,2026-10-01,123,NSE_FNO,vendor_x\n"
    "160,25000,CE,98.5,99,25005,2026-10-01,123,NSE_FNO,vendor_x\n"
).encode()


def test_checksum_is_of_exact_source_bytes():
    assert sha256_bytes(CSV) == hashlib.sha256(CSV).hexdigest()


def test_parser_requires_bid_and_ask_columns():
    with pytest.raises(ValueError, match="missing columns"):
        parse_execution_quote_csv(
            b"timestamp,strike,option_type,bid\n100,25000,CE,99\n"
        )


def test_parser_rejects_unexpected_columns():
    raw = b"timestamp,strike,option_type,bid,ask,unexpected\n100,25000,CE,99,100,x\n"
    with pytest.raises(ValueError, match="unexpected CSV columns"):
        parse_execution_quote_csv(raw)


def test_import_creates_execution_grade_manifest_from_raw_checksum():
    manifest, quotes = import_execution_evidence_csv(
        CSV,
        source="vendor_x",
        license_name="commercial-research",
        coverage_start=100,
        coverage_end=160,
        timezone="Asia/Kolkata",
        sampling_seconds=60,
        contract_universe="NIFTY weekly options",
        expected_timestamps={100, 160},
    )
    assert manifest.execution_grade is True
    assert manifest.checksum_sha256 == hashlib.sha256(CSV).hexdigest()
    assert len(quotes) == 2


def test_import_rejects_missing_timestamp_coverage():
    with pytest.raises(ValueError, match="coverage mismatch"):
        import_execution_evidence_csv(
            CSV,
            source="vendor_x",
            license_name="commercial-research",
            coverage_start=100,
            coverage_end=220,
            timezone="Asia/Kolkata",
            sampling_seconds=60,
            contract_universe="NIFTY weekly options",
            expected_timestamps={100, 160, 220},
        )


def test_import_never_fabricates_bid_ask_from_close():
    raw = (
        "timestamp,strike,option_type,bid,ask,close\n"
        "100,25000,CE,,,100\n"
    ).encode()
    with pytest.raises(ValueError, match="positive bid and ask"):
        parse_execution_quote_csv(raw)
