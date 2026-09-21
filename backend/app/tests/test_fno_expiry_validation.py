from datetime import date

import pytest

from app.api.v1.fno import _select_valid_expiry


def test_select_valid_expiry_rejects_expired_requested_contract():
    with pytest.raises(ValueError, match="not available or has already expired"):
        _select_valid_expiry(
            "2026-09-20",
            ["2026-09-20", "2026-09-24"],
            today=date(2026, 9, 21),
        )


def test_select_valid_expiry_rejects_requested_contract_not_returned_by_broker():
    with pytest.raises(ValueError, match="not available or has already expired"):
        _select_valid_expiry(
            "2026-10-01",
            ["2026-09-24"],
            today=date(2026, 9, 21),
        )


def test_select_valid_expiry_defaults_to_nearest_valid_expiry():
    assert _select_valid_expiry(
        None,
        ["2026-09-24", "2026-10-01"],
        today=date(2026, 9, 21),
    ) == "2026-09-24"


def test_select_valid_expiry_accepts_today_expiry():
    assert _select_valid_expiry(
        "2026-09-21",
        ["2026-09-21", "2026-09-24"],
        today=date(2026, 9, 21),
    ) == "2026-09-21"
