import pytest

from app.providers.market_search import SearchInstrument, YahooFinanceSearchProvider
from app.services.instrument_service import IndianSymbolError, canonical_indian_symbol


def _mock_nse_master(monkeypatch):
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_load_nse_master",
        classmethod(
            lambda cls, timeout=8.0: [
                SearchInstrument("ABCIND", "ABC Industries Limited", "NSE"),
                SearchInstrument("TCS", "Tata Consultancy Services", "NSE"),
            ]
        ),
    )
    monkeypatch.setattr(YahooFinanceSearchProvider, "_search_yahoo", lambda self, query: [])
    YahooFinanceSearchProvider._cache.clear()
    YahooFinanceSearchProvider._nse_master = None


def test_canonical_symbol_accepts_case_and_provider_suffix(monkeypatch):
    _mock_nse_master(monkeypatch)

    assert canonical_indian_symbol("  tcs.ns ") == "TCS"
    assert canonical_indian_symbol("tcs") == "TCS"


def test_canonical_symbol_rejects_us_equity(monkeypatch):
    _mock_nse_master(monkeypatch)

    with pytest.raises(IndianSymbolError, match="not available in the Indian"):
        canonical_indian_symbol("AAPL")


def test_canonical_symbol_supports_less_popular_nse_symbol(monkeypatch):
    _mock_nse_master(monkeypatch)

    assert canonical_indian_symbol("ABCIND") == "ABCIND"
