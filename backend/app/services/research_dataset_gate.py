"""Fail-closed eligibility checks for research analytics datasets."""
from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from app.services.dataset_provenance import fingerprint_market_bars
from app.services.nse_equity_calendar import DEFAULT_NSE_EQUITY_CALENDAR
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

    structural_issues = _structural_dataset_issues(bars)
    if structural_issues:
        raise ValueError(
            "Research dataset is not certified: structural data-quality issues: "
            + ", ".join(structural_issues)
        )

    corporate_action_state = provenance.get("corporate_action_adjusted")
    if require_corporate_action_state and not isinstance(corporate_action_state, bool):
        raise ValueError(
            f"Research dataset corporate-action adjustment state is UNKNOWN: {dataset}"
        )

    return bars, provenance


def _structural_dataset_issues(bars: list[Any]) -> list[str]:
    """Return hard-fail structural defects that make research unsafe."""
    ist = ZoneInfo("Asia/Kolkata")
    weekend_bars = 0
    unknown_weekend_bars = 0
    holiday_bars = 0
    mock_session_bars = 0
    unknown_session_bars = 0
    outside_session_bars = 0
    negative_volume_bars = 0
    mixed_source_offsets = set()

    bars_by_date: dict[Any, list[Any]] = defaultdict(list)
    for bar in bars:
        timestamp = getattr(bar, "timestamp", None)
        if timestamp is None:
            return ["missing_timestamp"]
        local = timestamp.astimezone(ist)
        bars_by_date[local.date()].append(bar)
        weekend_bars += int(local.weekday() >= 5)
        volume = getattr(bar, "volume", None)
        if volume is not None and volume < 0:
            negative_volume_bars += 1
        mixed_source_offsets.add(timestamp.utcoffset())

    for day, day_bars in bars_by_date.items():
        classification = DEFAULT_NSE_EQUITY_CALENDAR.classify_session(day)
        if classification.status == "MOCK":
            mock_session_bars += len(day_bars)
            continue
        if classification.status == "HOLIDAY":
            holiday_bars += len(day_bars)
            continue
        if classification.status == "UNKNOWN":
            unknown_session_bars += len(day_bars)
            unknown_weekend_bars += len(day_bars)
            continue
        for bar in day_bars:
            local = bar.timestamp.astimezone(ist)
            if not DEFAULT_NSE_EQUITY_CALENDAR.is_timestamp_in_session(local.time(), classification):
                outside_session_bars += 1

    issues: list[str] = []
    if unknown_weekend_bars:
        issues.append(f"weekend_bars={unknown_weekend_bars}")
    if holiday_bars:
        issues.append(f"holiday_bars={holiday_bars}")
    if mock_session_bars:
        issues.append(f"mock_session_bars={mock_session_bars}")
    if unknown_session_bars:
        issues.append(f"unknown_session_bars={unknown_session_bars}")
    if outside_session_bars:
        issues.append(f"outside_session_bars={outside_session_bars}")
    if negative_volume_bars:
        issues.append(f"negative_volume_bars={negative_volume_bars}")
    if len(mixed_source_offsets) > 1:
        issues.append(f"mixed_source_timezone_offsets={len(mixed_source_offsets)}")
    return issues
