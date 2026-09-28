import pytest
from dataclasses import replace

from app.services.fno_execution_evidence_import_service import import_execution_evidence_csv
from app.services.fno_execution_evidence_freeze_service import (
    canonical_package_bytes,
    freeze_execution_evidence,
    verify_frozen_execution_evidence,
)

CSV = (
    "timestamp,strike,option_type,bid,ask,spot,expiry,security_id,exchange_segment,source\n"
    "100,25000,CE,99.5,100,25010,2026-10-01,123,NSE_FNO,vendor_x\n"
    "160,25000,CE,98.5,99,25005,2026-10-01,123,NSE_FNO,vendor_x\n"
).encode()


def _package():
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
    return freeze_execution_evidence(
        manifest=manifest, quotes=quotes, expected_timestamps={100, 160}
    )


def test_freeze_is_deterministic():
    first, second = _package(), _package()
    assert first.package_sha256 == second.package_sha256
    assert canonical_package_bytes(first.manifest, first.quotes) == canonical_package_bytes(
        second.manifest, second.quotes
    )


def test_frozen_package_contains_execution_grade_snapshots():
    package = _package()
    assert package.snapshots[0]["execution_grade"] is True
    assert package.snapshots[0]["oc"]["25000"]["ce"]["top_ask_price"] == 100.0


def test_frozen_package_verification_detects_tampering():
    package = _package()
    assert verify_frozen_execution_evidence(package) is True
    tampered_quote = replace(package.quotes[0], bid=1.0)
    tampered = replace(package, quotes=(tampered_quote,) + package.quotes[1:])
    assert verify_frozen_execution_evidence(tampered) is False


def test_freeze_rejects_empty_quotes():
    manifest, _ = import_execution_evidence_csv(
        CSV,
        source="vendor_x",
        license_name="commercial-research",
        coverage_start=100,
        coverage_end=160,
        timezone="Asia/Kolkata",
        sampling_seconds=60,
        contract_universe="NIFTY weekly options",
    )
    with pytest.raises(ValueError, match="empty"):
        freeze_execution_evidence(manifest=manifest, quotes=[])


def test_frozen_package_round_trips_through_json():
    package = _package()
    raw = serialize_frozen_execution_evidence(package)
    loaded = load_frozen_execution_evidence(raw)
    assert loaded.package_sha256 == package.package_sha256
    assert loaded.quotes == package.quotes
    assert loaded.snapshots == package.snapshots


def test_loader_rejects_tampered_json():
    package = _package()
    raw = serialize_frozen_execution_evidence(package).decode("utf-8")
    raw = raw.replace('"bid":99.5', '"bid":1.0', 1)
    with pytest.raises(ValueError, match="integrity verification"):
        load_frozen_execution_evidence(raw.encode("utf-8"))
