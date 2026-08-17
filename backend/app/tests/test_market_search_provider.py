from app.providers.market_search import DhanInstrumentSearchProvider
from app.services.instrument_master_service import IndianInstrument


def test_search_returns_non_popular_nse_stock(monkeypatch):
    monkeypatch.setattr(
        "app.providers.market_search.instrument_master.search",
        lambda query, limit=20: [
            IndianInstrument("123", "NSE_EQ", "ZYDUSLIFE", "Zydus Lifesciences Limited", "EQ", None)
        ],
    )
    results = DhanInstrumentSearchProvider().search("zydus")
    assert results[0].symbol == "ZYDUSLIFE"
    assert results[0].exchange == "NSE"
    assert results[0].security_id == "123"


def test_search_never_falls_back_to_bse_or_us_stocks(monkeypatch):
    calls = []
    monkeypatch.setattr("app.providers.market_search.instrument_master.search", lambda query, limit=20: calls.append(query) or [])
    assert DhanInstrumentSearchProvider().search("apple") == []
    assert calls == ["apple"]


def test_exact_resolution_rejects_unknown_symbol(monkeypatch):
    monkeypatch.setattr("app.providers.market_search.instrument_master.search", lambda query, limit=100: [])
    try:
        DhanInstrumentSearchProvider().resolve_exact("HINDUSTAN COPPER")
        assert False, "unknown company name must not resolve"
    except ValueError as exc:
        assert "Select an NSE stock" in str(exc)
