from datetime import date

import pytest

from app.services.corporate_action_provenance import (
    CorporateActionProvenance,
    CorporateActionRecord,
    filter_actions_for_range,
    validate_provenance,
)


def _provenance(adjustment_state=False):
    return CorporateActionProvenance(
        dataset_id="equity_nse_discovery_5m",
        adjustment_state=adjustment_state,
        provider="Dhan",
        provider_contract_reference=None,
        action_source="NSE Corporate Actions",
        action_source_version="2026-10-01",
        action_records=(
            CorporateActionRecord(
                "TCS",
                date(2025, 1, 10),
                "SPLIT",
                0.5,
                "NSE",
                "official-record-1",
            ),
        ),
    )


def test_provenance_requires_source_metadata():
    validate_provenance(_provenance(False))


def test_unknown_adjustment_state_is_allowed_but_not_attested():
    provenance = _provenance(None)
    validate_provenance(provenance)
    assert provenance.adjustment_state is None


def test_invalid_action_factor_rejected():
    provenance = _provenance(False)
    invalid = CorporateActionProvenance(
        **{
            **provenance.__dict__,
            "action_records": (
                CorporateActionRecord(
                    "TCS",
                    date(2025, 1, 10),
                    "SPLIT",
                    0,
                    "NSE",
                    "official-record-1",
                ),
            ),
        }
    )
    with pytest.raises(ValueError, match="positive"):
        validate_provenance(invalid)


def test_filter_actions_is_symbol_and_date_scoped():
    actions = (
        CorporateActionRecord(
            "TCS", date(2025, 1, 10), "SPLIT", 0.5, "NSE", "r1"
        ),
        CorporateActionRecord(
            "INFY", date(2025, 1, 10), "SPLIT", 0.5, "NSE", "r2"
        ),
        CorporateActionRecord(
            "TCS", date(2024, 1, 10), "SPLIT", 0.5, "NSE", "r3"
        ),
    )
    result = filter_actions_for_range(
        actions,
        symbols={"TCS"},
        start=date(2025, 1, 1),
        end=date(2025, 12, 31),
    )
    assert len(result) == 1
    assert result[0].source_reference == "r1"


def test_provenance_serializes_dates():
    payload = _provenance(False).as_dict()
    assert payload["action_records"][0]["action_date"] == "2025-01-10"
