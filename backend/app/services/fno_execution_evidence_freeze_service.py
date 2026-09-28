from __future__ import annotations

"""Immutable, deterministic representation of imported execution-grade evidence."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Sequence

from app.services.fno_evidence_manifest_service import (
    ExecutionEvidenceManifest,
    validate_execution_evidence_manifest,
)
from app.services.fno_execution_evidence_service import (
    ExecutionQuote,
    build_execution_grade_snapshots,
    validate_execution_quote_coverage,
)


@dataclass(frozen=True)
class FrozenExecutionEvidencePackage:
    manifest: ExecutionEvidenceManifest
    quotes: tuple[ExecutionQuote, ...]
    snapshots: tuple[dict[str, Any], ...]
    package_sha256: str


def _manifest_payload(manifest: ExecutionEvidenceManifest) -> dict[str, Any]:
    return {
        "source": manifest.source,
        "license": manifest.license,
        "coverage_start": manifest.coverage_start,
        "coverage_end": manifest.coverage_end,
        "timezone": manifest.timezone,
        "sampling_seconds": manifest.sampling_seconds,
        "contract_universe": manifest.contract_universe,
        "checksum_sha256": manifest.checksum_sha256,
        "execution_grade": manifest.execution_grade,
        "created_at": manifest.created_at,
    }


def _quote_payload(quote: ExecutionQuote) -> dict[str, Any]:
    return {
        "timestamp": quote.timestamp,
        "strike": quote.strike,
        "option_type": quote.option_type,
        "bid": quote.bid,
        "ask": quote.ask,
        "spot": quote.spot,
        "expiry": quote.expiry,
        "security_id": quote.security_id,
        "exchange_segment": quote.exchange_segment,
        "source": quote.source,
    }


def canonical_package_bytes(
    manifest: ExecutionEvidenceManifest,
    quotes: Sequence[ExecutionQuote],
) -> bytes:
    """Serialize only normalized evidence fields with stable JSON ordering."""
    payload = {
        "manifest": _manifest_payload(manifest),
        "quotes": [_quote_payload(q) for q in quotes],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def freeze_execution_evidence(
    *,
    manifest: ExecutionEvidenceManifest,
    quotes: Sequence[ExecutionQuote],
    expected_timestamps: set[int] | None = None,
) -> FrozenExecutionEvidencePackage:
    """Validate and freeze execution-grade evidence without repairing it."""
    manifest_result = validate_execution_evidence_manifest(manifest)
    if not manifest_result["valid"]:
        raise ValueError(
            "cannot freeze invalid execution evidence manifest: "
            f"{manifest_result['errors']}"
        )
    if not quotes:
        raise ValueError("cannot freeze empty execution evidence")

    ordered_quotes = tuple(
        sorted(quotes, key=lambda q: (q.timestamp, q.strike, q.option_type))
    )

    if expected_timestamps is not None:
        coverage = validate_execution_quote_coverage(
            ordered_quotes,
            expected_timestamps=expected_timestamps,
        )
        if not coverage["valid"]:
            raise ValueError(
                "cannot freeze incomplete timestamp coverage: "
                f"missing={coverage['missing_timestamps']}, "
                f"unexpected={coverage['unexpected_timestamps']}"
            )

    timestamps = {q.timestamp for q in ordered_quotes}
    if min(timestamps) < manifest.coverage_start or max(timestamps) > manifest.coverage_end:
        raise ValueError("execution evidence falls outside manifest coverage")

    snapshots = tuple(build_execution_grade_snapshots(ordered_quotes))
    package_sha256 = hashlib.sha256(
        canonical_package_bytes(manifest, ordered_quotes)
    ).hexdigest()

    return FrozenExecutionEvidencePackage(
        manifest=manifest,
        quotes=ordered_quotes,
        snapshots=snapshots,
        package_sha256=package_sha256,
    )


def verify_frozen_execution_evidence(
    package: FrozenExecutionEvidencePackage,
) -> bool:
    """Verify the deterministic package hash before replay consumes it."""
    expected = hashlib.sha256(
        canonical_package_bytes(package.manifest, package.quotes)
    ).hexdigest()
    return expected == package.package_sha256


def serialize_frozen_execution_evidence(
    package: FrozenExecutionEvidencePackage,
) -> bytes:
    """Serialize a frozen package with its integrity hash for durable storage."""
    if not verify_frozen_execution_evidence(package):
        raise ValueError("cannot serialize tampered frozen execution evidence")
    payload = {
        "manifest": _manifest_payload(package.manifest),
        "quotes": [_quote_payload(q) for q in package.quotes],
        "package_sha256": package.package_sha256,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_frozen_execution_evidence(raw_bytes: bytes) -> FrozenExecutionEvidencePackage:
    """Load and verify a serialized package before it can enter replay."""
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid frozen execution evidence JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("frozen execution evidence root must be an object")

    manifest = manifest_from_mapping(payload.get("manifest") or {})
    raw_quotes = payload.get("quotes")
    if not isinstance(raw_quotes, list):
        raise ValueError("frozen execution evidence quotes must be a list")

    quotes = tuple(
        ExecutionQuote(
            timestamp=int(item["timestamp"]),
            strike=float(item["strike"]),
            option_type=str(item["option_type"]),
            bid=float(item["bid"]),
            ask=float(item["ask"]),
            spot=float(item["spot"]) if item.get("spot") is not None else None,
            expiry=item.get("expiry"),
            security_id=item.get("security_id"),
            exchange_segment=item.get("exchange_segment"),
            source=str(item.get("source") or "external_historical_quotes"),
        )
        for item in raw_quotes
        if isinstance(item, dict)
    )
    package = FrozenExecutionEvidencePackage(
        manifest=manifest,
        quotes=quotes,
        snapshots=tuple(build_execution_grade_snapshots(quotes)),
        package_sha256=str(payload.get("package_sha256") or ""),
    )
    if not verify_frozen_execution_evidence(package):
        raise ValueError("frozen execution evidence integrity verification failed")
    return package
