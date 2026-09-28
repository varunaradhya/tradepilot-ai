from __future__ import annotations

"""Deterministic import boundary for externally supplied execution-grade F&O quotes.

The importer accepts raw CSV bytes, computes the SHA-256 of those exact bytes,
strictly parses the canonical quote schema, validates coverage, and produces a
provenance manifest. It never fills missing quotes or derives bid/ask from LTP.
"""

import csv
import hashlib
import io
from typing import Any, Iterable

from app.services.fno_evidence_manifest_service import ExecutionEvidenceManifest
from app.services.fno_execution_evidence_service import (
    ExecutionQuote,
    normalize_execution_quotes,
    validate_execution_quote_coverage,
)


REQUIRED_COLUMNS = (
    "timestamp",
    "strike",
    "option_type",
    "bid",
    "ask",
)
OPTIONAL_COLUMNS = (
    "spot",
    "expiry",
    "security_id",
    "exchange_segment",
    "source",
)


def sha256_bytes(raw_bytes: bytes) -> str:
    """Return the checksum of the exact source bytes before parsing."""
    if not isinstance(raw_bytes, (bytes, bytearray)):
        raise TypeError("raw evidence must be bytes")
    return hashlib.sha256(bytes(raw_bytes)).hexdigest()


def parse_execution_quote_csv(
    raw_bytes: bytes,
    *,
    expected_timestamps: set[int] | None = None,
) -> list[ExecutionQuote]:
    """Parse the canonical CSV schema without coercing missing columns."""
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("execution evidence CSV must be UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    fieldnames = tuple(reader.fieldnames or ())
    missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing:
        raise ValueError(f"execution evidence CSV missing columns: {missing}")

    rows: list[dict[str, Any]] = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(f"unexpected CSV columns at line {line_number}")
        if any(value is None for value in row.values()):
            raise ValueError(f"malformed CSV row at line {line_number}")
        rows.append(row)

    return normalize_execution_quotes(
        rows,
        expected_timestamps=expected_timestamps,
    )


def import_execution_evidence_csv(
    raw_bytes: bytes,
    *,
    source: str,
    license_name: str,
    coverage_start: int,
    coverage_end: int,
    timezone: str,
    sampling_seconds: int,
    contract_universe: str,
    expected_timestamps: set[int] | None = None,
    created_at: int | None = None,
) -> tuple[ExecutionEvidenceManifest, list[ExecutionQuote]]:
    """Import, validate and provenance-bind one external evidence file."""
    checksum = sha256_bytes(raw_bytes)
    quotes = parse_execution_quote_csv(
        raw_bytes,
        expected_timestamps=expected_timestamps,
    )

    if expected_timestamps is not None:
        coverage = validate_execution_quote_coverage(
            quotes,
            expected_timestamps=expected_timestamps,
        )
        if not coverage["valid"]:
            raise ValueError(
                "execution evidence timestamp coverage mismatch: "
                f"missing={coverage['missing_timestamps']}, "
                f"unexpected={coverage['unexpected_timestamps']}"
            )

    manifest = ExecutionEvidenceManifest(
        source=source.strip(),
        license=license_name.strip(),
        coverage_start=int(coverage_start),
        coverage_end=int(coverage_end),
        timezone=timezone.strip(),
        sampling_seconds=int(sampling_seconds),
        contract_universe=contract_universe.strip(),
        checksum_sha256=checksum,
        execution_grade=True,
        created_at=created_at,
    )
    return manifest, quotes
