from app.providers.market_search import DhanInstrumentSearchProvider
from app.services.instrument_master_service import IndianInstrument


def test_search_requires_two_characters():
    assert DhanInstrumentSearchProvider().search("t") == []


def test_search_ranks_exact_prefix_and_company_name(monkeypatch):
    monkeypatch.setattr(
        "app.providers.market_search.instrument_master.search",
        lambda query, limit=20: [
            IndianInstrument("1", "NSE_EQ", "ZOMATO", "Zomato Limited", "EQ", None),
            IndianInstrument("2", "NSE_EQ", "ZOMATOHOLD", "Zomato Holding Example", "EQ", None),
            IndianInstrument("3", "NSE_EQ", "DMART", "Avenue Supermarts", "EQ", None),
        ],
    )
    results = DhanInstrumentSearchProvider().search("zomato")
    assert results[0].symbol == "ZOMATO"
    assert all(item.exchange == "NSE" for item in results)


def test_search_by_company_name(monkeypatch):
    monkeypatch.setattr(
        "app.providers.market_search.instrument_master.search",
        lambda query, limit=20: [IndianInstrument("4", "NSE_EQ", "ABCIND", "ABC Industries Limited", "EQ", None)],
    )
    results = DhanInstrumentSearchProvider().search("abc industries")
    assert results[0].symbol == "ABCIND"


def test_unknown_company_is_not_accepted(monkeypatch):
    monkeypatch.setattr("app.providers.market_search.instrument_master.search", lambda query, limit=100: [])
    try:
        DhanInstrumentSearchProvider().resolve_exact("NOT A REAL STOCK")
        assert False
    except ValueError:
        assert True
