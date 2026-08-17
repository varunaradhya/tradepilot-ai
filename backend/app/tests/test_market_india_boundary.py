import pytest

from app.services.instrument_master_service import IndianInstrument
from app.services.instrument_service import IndianSymbolError, canonical_indian_symbol


def _mock_master(monkeypatch):
    monkeypatch.setattr(
        "app.services.instrument_service.instrument_master.search",
        lambda query, limit=100: [
            IndianInstrument("1", "NSE_EQ", "ABCIND", "ABC Industries Limited", "EQ", None),
            IndianInstrument("2", "NSE_EQ", "TCS", "Tata Consultancy Services", "EQ", None),
        ],
    )


def test_canonical_symbol_accepts_case_and_provider_suffix(monkeypatch):
    _mock_master(monkeypatch)
    assert canonical_indian_symbol("  tcs.ns ") == "TCS"
    assert canonical_indian_symbol("tcs") == "TCS"


def test_canonical_symbol_rejects_us_equity(monkeypatch):
    _mock_master(monkeypatch)
    with pytest.raises(IndianSymbolError, match="active NSE equity"):
        canonical_indian_symbol("AAPL")


def test_canonical_symbol_supports_less_popular_nse_symbol(monkeypatch):
    _mock_master(monkeypatch)
    assert canonical_indian_symbol("ABCIND") == "ABCIND"
