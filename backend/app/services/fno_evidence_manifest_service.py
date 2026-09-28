from __future__ import annotations

"""Provenance contract for execution-grade historical F&O evidence.

This module records where a dataset came from and what exact coverage was
validated. It does not download data, infer missing fields, or establish
strategy performance.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence


@dataclass(frozen=True)
class ExecutionEvidenceManifest:
    source: str
    license: str
    coverage_start: int
    coverage_end: int
    timezone: str
    sampling_seconds: int
    contract_universe: str
    checksum_sha256: str
    execution_grade: bool = True
    created_at: int | None = None


_REQUIRED_TEXT = (
    "source",
    "license",
    "timezone",
    "contract_universe",
    "checksum_sha256",
)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def validate_execution_evidence_manifest(
    manifest: ExecutionEvidenceManifest,
) -> dict[str, Any]:
    """Validate dataset provenance before execution-grade evidence is accepted."""
    errors: list[str] = []

    for field in _REQUIRED_TEXT:
        if not _text(getattr(manifest, field)):
            errors.append(f"MISSING_{field.upper()}")

    if manifest.coverage_start <= 0:
        errors.append("INVALID_COVERAGE_START")
    if manifest.coverage_end <= 0 or manifest.coverage_end < manifest.coverage_start:
        errors.append("INVALID_COVERAGE_END")
    if manifest.sampling_seconds <= 0:
        errors.append("INVALID_SAMPLING_SECONDS")
    if manifest.created_at is not None and manifest.created_at <= 0:
        errors.append("INVALID_CREATED_AT")
    if not manifest.execution_grade:
        errors.append("NOT_EXECUTION_GRADE")

    checksum = _text(manifest.checksum_sha256).lower()
    if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
        errors.append("INVALID_SHA256")

    return {
        "valid": not errors,
        "errors": errors,
        "source": manifest.source,
        "coverage_start": manifest.coverage_start,
        "coverage_end": manifest.coverage_end,
        "sampling_seconds": manifest.sampling_seconds,
        "execution_grade": manifest.execution_grade,
    }


def validate_execution_dataset(
    *,
    manifest: ExecutionEvidenceManifest,
    bars: Sequence[dict[str, Any]],
    snapshots: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Bind provenance validation to the existing historical dataset validator.

    The manifest is checked first. The dataset validator is then invoked so
    timestamp alignment and executable bid/ask checks remain the single source
    of truth for market-data integrity.
    """
    manifest_result = validate_execution_evidence_manifest(manifest)
    if not manifest_result["valid"]:
        return {
            "valid": False,
            "reason": "INVALID_EVIDENCE_MANIFEST",
            "manifest": manifest_result,
        }

    from app.services.fno_historical_data_service import validate_historical_dataset

    dataset_result = validate_historical_dataset(bars=bars, snapshots=snapshots)
    if not dataset_result["valid"]:
        return {
            "valid": False,
            "reason": "INVALID_HISTORICAL_DATASET",
            "manifest": manifest_result,
            "dataset": dataset_result,
        }

    return {
        "valid": True,
        "reason": "OK",
        "manifest": manifest_result,
        "dataset": dataset_result,
    }


def manifest_from_mapping(values: dict[str, Any]) -> ExecutionEvidenceManifest:
    """Create a manifest from an external metadata mapping without guessing."""
    return ExecutionEvidenceManifest(
        source=_text(values.get("source")),
        license=_text(values.get("license")),
        coverage_start=int(values.get("coverage_start", 0)),
        coverage_end=int(values.get("coverage_end", 0)),
        timezone=_text(values.get("timezone")),
        sampling_seconds=int(values.get("sampling_seconds", 0)),
        contract_universe=_text(values.get("contract_universe")),
        checksum_sha256=_text(values.get("checksum_sha256")),
        execution_grade=bool(values.get("execution_grade", True)),
        created_at=int(values["created_at"]) if values.get("created_at") is not None else None,
    )
