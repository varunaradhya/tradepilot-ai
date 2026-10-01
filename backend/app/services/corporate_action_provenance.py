"""Source-backed corporate-action provenance for research datasets.

This module deliberately separates two facts:
1. which corporate actions are known for a dataset's symbols/date range; and
2. whether the provider's OHLCV series is already adjusted.

The second fact must be explicitly attested by the data provider/source. It must
never be inferred from price jumps or reconstructed from observed bars.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class CorporateActionRecord:
    symbol: str
    action_date: date
    action_type: str
    factor: float
    source: str
    source_reference: str


@dataclass(frozen=True)
class CorporateActionProvenance:
    dataset_id: str
    adjustment_state: bool | None
    provider: str
    provider_contract_reference: str | None
    action_source: str
    action_source_version: str
    action_records: tuple[CorporateActionRecord, ...] = ()

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["action_records"] = [
            {**record, "action_date": record["action_date"].isoformat()}
            for record in payload["action_records"]
        ]
        return payload


def validate_provenance(provenance: CorporateActionProvenance) -> None:
    if not provenance.dataset_id.strip():
        raise ValueError("Corporate-action provenance requires dataset_id")
    if not provenance.provider.strip():
        raise ValueError("Corporate-action provenance requires provider")
    if not provenance.action_source.strip():
        raise ValueError("Corporate-action provenance requires action_source")
    if not provenance.action_source_version.strip():
        raise ValueError("Corporate-action provenance requires action_source_version")

    if provenance.adjustment_state is not None and not isinstance(
        provenance.adjustment_state, bool
    ):
        raise ValueError("adjustment_state must be True, False, or None")

    for record in provenance.action_records:
        if not record.symbol.strip():
            raise ValueError("Corporate-action record requires symbol")
        if record.factor <= 0:
            raise ValueError("Corporate-action factor must be positive")
        if not record.source.strip() or not record.source_reference.strip():
            raise ValueError(
                "Corporate-action record requires source and source_reference"
            )


def filter_actions_for_range(
    actions: Iterable[CorporateActionRecord],
    *,
    symbols: set[str],
    start: date,
    end: date,
) -> tuple[CorporateActionRecord, ...]:
    normalized_symbols = {symbol.strip().upper() for symbol in symbols}
    return tuple(
        action
        for action in actions
        if action.symbol.strip().upper() in normalized_symbols
        and start <= action.action_date <= end
    )
