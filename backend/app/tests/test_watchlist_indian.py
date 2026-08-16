import pytest

from app.providers.market_search import MarketSearchProviderError, SearchInstrument
from app.services.watchlist_service import WatchlistSymbolError, _canonical_indian_symbol


def test_canonical_symbol_prefers_nse(monkeypatch):
    monkeypatch.setattr(
        "app.services.watchlist_service.search_instruments",
        lambda query: [
            SearchInstrument(symbol="TCS", name="Tata Consultancy Services", exchange="BSE"),
            SearchInstrument(symbol="TCS", name="Tata Consultancy Services", exchange="NSE"),
        ],
    )

    assert _canonical_indian_symbol("tcs.ns") == "TCS"


def test_canonical_symbol_rejects_non_indian_symbol(monkeypatch):
    monkeypatch.setattr("app.services.watchlist_service.search_instruments", lambda query: [])

    with pytest.raises(WatchlistSymbolError, match="not available in the Indian"):
        _canonical_indian_symbol("AAPL")


def test_canonical_symbol_surfaces_provider_outage(monkeypatch):
    def fail(_query):
        raise MarketSearchProviderError("upstream unavailable")

    monkeypatch.setattr("app.services.watchlist_service.search_instruments", fail)

    with pytest.raises(WatchlistSymbolError, match="temporarily unavailable"):
        _canonical_indian_symbol("TCS")
