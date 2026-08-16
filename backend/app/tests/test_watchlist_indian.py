import pytest

from app.providers.market_search import MarketSearchProviderError, SearchInstrument
from app.services.instrument_service import IndianSymbolError, canonical_indian_symbol


def test_canonical_symbol_prefers_nse(monkeypatch):
    monkeypatch.setattr(
        "app.services.instrument_service._search_provider.search",
        lambda query: [
            SearchInstrument(symbol="TCS", name="Tata Consultancy Services", exchange="BSE"),
            SearchInstrument(symbol="TCS", name="Tata Consultancy Services", exchange="NSE"),
        ],
    )

    assert canonical_indian_symbol("tcs.ns") == "TCS"


def test_canonical_symbol_rejects_non_indian_symbol(monkeypatch):
    monkeypatch.setattr("app.services.instrument_service._search_provider.search", lambda query: [])

    with pytest.raises(IndianSymbolError, match="not available in the Indian"):
        canonical_indian_symbol("AAPL")


def test_canonical_symbol_surfaces_provider_outage(monkeypatch):
    def fail(_query):
        raise MarketSearchProviderError("upstream unavailable")

    monkeypatch.setattr("app.services.instrument_service._search_provider.search", fail)

    with pytest.raises(IndianSymbolError, match="temporarily unavailable"):
        canonical_indian_symbol("TCS")
