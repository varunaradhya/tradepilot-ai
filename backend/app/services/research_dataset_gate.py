"""Fail-closed eligibility checks for research analytics datasets."""
from __future__ import annotations

from typing import Any

from app.services.dataset_provenance import fingerprint_market_bars
from app.services.research_store import ResearchStore, research_store


def require_certified_dataset(
    dataset: str,
    *,
    store: ResearchStore = research_store,
    require_corporate_action_state: bool = True,
) -> tuple[list[Any], dict]:
    """Load a dataset only when its persisted provenance matches the stored bars.

    This is deliberately stricter than the data-quality endpoint. Research
    analytics can only consume a dataset whose provenance is present, marked
    VALID, fingerprint-matched, and (for price-performance research) has an
    explicit corporate-action state.
    """
    bars = store.load(dataset)
    if not bars:
        raise ValueError(f"Research dataset not found: {dataset}")

    provenance = store.get_provenance(dataset)
    if not provenance:
        raise ValueError(
            f"Research dataset is not certified: missing provenance for {dataset}"
        )
    if str(provenance.get("quality_status", "")).upper() != "VALID":
        raise ValueError(
            f"Research dataset is not certified: quality_status={provenance.get('quality_status')!r}"
        )

    expected_fingerprint = str(provenance.get("content_fingerprint") or "")
    symbol = str(provenance.get("symbol") or "").strip().upper()
    timeframe = str(provenance.get("timeframe") or "").strip()
    actual_fingerprint = fingerprint_market_bars(
        bars,
        symbol=symbol,
        timeframe=timeframe,
    )
    if len(expected_fingerprint) != 64 or actual_fingerprint.lower() != expected_fingerprint.lower():
        raise ValueError(
            f"Research dataset provenance fingerprint mismatch: {dataset}"
        )

    corporate_action_state = provenance.get("corporate_action_adjusted")
    if require_corporate_action_state and not isinstance(corporate_action_state, bool):
        raise ValueError(
            f"Research dataset corporate-action adjustment state is UNKNOWN: {dataset}"
        )

    return bars, provenance
