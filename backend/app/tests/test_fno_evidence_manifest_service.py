import pytest

from app.services.fno_evidence_manifest_service import (
    ExecutionEvidenceManifest,
    manifest_from_mapping,
    validate_execution_dataset,
    validate_execution_evidence_manifest,
)


def _manifest(**overrides):
    values = {
        "source": "vendor_x",
        "license": "commercial-research",
        "coverage_start": 1000,
        "coverage_end": 2000,
        "timezone": "Asia/Kolkata",
        "sampling_seconds": 60,
        "contract_universe": "NIFTY weekly options",
        "checksum_sha256": "a" * 64,
        "execution_grade": True,
    }
    values.update(overrides)
    return ExecutionEvidenceManifest(**values)


def _bars_and_snapshots():
    bars = [{"timestamp": 1000}, {"timestamp": 1060}]
    snapshots = [
        {
            "timestamp": 1000,
            "oc": {
                "25000": {
                    "ce": {"top_bid_price": 99, "top_ask_price": 100},
                }
            },
        },
        {
            "timestamp": 1060,
            "oc": {
                "25000": {
                    "ce": {"top_bid_price": 98, "top_ask_price": 99},
                }
            },
        },
    ]
    return bars, snapshots


def test_manifest_requires_valid_sha256():
    result = validate_execution_evidence_manifest(_manifest(checksum_sha256="bad"))
    assert result["valid"] is False
    assert "INVALID_SHA256" in result["errors"]


def test_manifest_rejects_non_execution_grade():
    result = validate_execution_evidence_manifest(_manifest(execution_grade=False))
    assert result["valid"] is False
    assert "NOT_EXECUTION_GRADE" in result["errors"]


def test_manifest_from_mapping_does_not_invent_missing_values():
    manifest = manifest_from_mapping({"source": "vendor_x"})
    result = validate_execution_evidence_manifest(manifest)
    assert result["valid"] is False
    assert "MISSING_LICENSE" in result["errors"]


def test_execution_dataset_binds_manifest_and_historical_validation():
    bars, snapshots = _bars_and_snapshots()
    result = validate_execution_dataset(
        manifest=_manifest(),
        bars=bars,
        snapshots=snapshots,
    )
    assert result["valid"] is True
    assert result["dataset"]["invalid_count"] == 0


def test_execution_dataset_fails_closed_on_bad_manifest():
    bars, snapshots = _bars_and_snapshots()
    result = validate_execution_dataset(
        manifest=_manifest(checksum_sha256="bad"),
        bars=bars,
        snapshots=snapshots,
    )
    assert result["valid"] is False
    assert result["reason"] == "INVALID_EVIDENCE_MANIFEST"


def test_execution_dataset_fails_closed_on_misaligned_snapshot():
    bars, snapshots = _bars_and_snapshots()
    snapshots[1]["timestamp"] = 1059
    result = validate_execution_dataset(
        manifest=_manifest(),
        bars=bars,
        snapshots=snapshots,
    )
    assert result["valid"] is False
    assert result["reason"] == "INVALID_HISTORICAL_DATASET"
