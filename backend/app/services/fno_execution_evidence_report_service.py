from __future__ import annotations

"""Audit report for frozen execution-grade evidence.

This is descriptive only: it does not score a strategy or infer profitability.
"""

from typing import Any

from app.services.fno_execution_evidence_freeze_service import (
    FrozenExecutionEvidencePackage,
    verify_frozen_execution_evidence,
)


def build_execution_evidence_report(
    package: FrozenExecutionEvidencePackage,
) -> dict[str, Any]:
    verified = verify_frozen_execution_evidence(package)
    timestamps = sorted({quote.timestamp for quote in package.quotes})
    contracts = sorted({
        (
            quote.security_id,
            quote.exchange_segment,
            quote.expiry,
            quote.strike,
            quote.option_type,
        )
        for quote in package.quotes
    })
    return {
        "verified": verified,
        "execution_grade": bool(package.manifest.execution_grade),
        "source": package.manifest.source,
        "license": package.manifest.license,
        "timezone": package.manifest.timezone,
        "sampling_seconds": package.manifest.sampling_seconds,
        "coverage": {
            "declared_start": package.manifest.coverage_start,
            "declared_end": package.manifest.coverage_end,
            "observed_start": min(timestamps) if timestamps else None,
            "observed_end": max(timestamps) if timestamps else None,
            "timestamp_count": len(timestamps),
        },
        "quote_count": len(package.quotes),
        "contract_count": len(contracts),
        "package_sha256": package.package_sha256,
        "source_checksum_sha256": package.manifest.checksum_sha256,
    }
