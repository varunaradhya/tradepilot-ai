import httpx

from app.providers.market_search import SearchInstrument, YahooFinanceSearchProvider


def test_search_filters_to_indian_equities(monkeypatch):
    def fake_get(url, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json={"quotes": [
            {"symbol": "TCS.NS", "longname": "Tata Consultancy Services", "quoteType": "EQUITY"},
            {"symbol": "TCS.BO", "longname": "Tata Consultancy Services", "quoteType": "EQUITY"},
            {"symbol": "AAPL", "longname": "Apple", "quoteType": "EQUITY"},
            {"symbol": "TCS.NS", "longname": "Duplicate", "quoteType": "EQUITY"},
            {"symbol": "TCS.NS", "longname": "Not equity", "quoteType": "ETF"},
        ]})

    monkeypatch.setattr("app.providers.market_search.httpx.get", fake_get)
    YahooFinanceSearchProvider._cache.clear()
    YahooFinanceSearchProvider._nse_master = None
    results = YahooFinanceSearchProvider().search("tcs")

    assert [(x.symbol, x.exchange) for x in results] == [("TCS", "NSE"), ("TCS", "BSE")]


def test_search_requires_two_characters():
    assert YahooFinanceSearchProvider().search("t") == []


def test_nse_master_finds_less_popular_symbol_and_ranks_exact_prefix_first(monkeypatch):
    YahooFinanceSearchProvider._cache.clear()
    YahooFinanceSearchProvider._nse_master = None
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_load_nse_master",
        classmethod(lambda cls, timeout=8.0: [
            SearchInstrument("ZOMATO", "Zomato Limited", "NSE"),
            SearchInstrument("ZOMATOHOLD", "Zomato Holding Example", "NSE"),
            SearchInstrument("DMART", "Avenue Supermarts", "NSE"),
        ]),
    )
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_search_yahoo",
        lambda self, query: [],
    )

    results = YahooFinanceSearchProvider().search("zomato")

    assert results
    assert results[0].symbol == "ZOMATO"
    assert all(item.exchange == "NSE" for item in results)
    assert any(item.symbol == "ZOMATOHOLD" for item in results)


def test_search_by_company_name_uses_nse_master(monkeypatch):
    YahooFinanceSearchProvider._cache.clear()
    YahooFinanceSearchProvider._nse_master = None
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_load_nse_master",
        classmethod(lambda cls, timeout=8.0: [
            SearchInstrument("ABCIND", "ABC Industries Limited", "NSE"),
            SearchInstrument("RELIANCE", "Reliance Industries Limited", "NSE"),
        ]),
    )
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_search_yahoo",
        lambda self, query: [],
    )

    results = YahooFinanceSearchProvider().search("abc industries")

    assert [(item.symbol, item.exchange) for item in results] == [("ABCIND", "NSE")]


def test_search_cache_is_normalized(monkeypatch):
    YahooFinanceSearchProvider._cache.clear()
    YahooFinanceSearchProvider._nse_master = None
    calls = {"count": 0}

    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_load_nse_master",
        classmethod(lambda cls, timeout=8.0: [SearchInstrument("TCS", "Tata Consultancy Services", "NSE")]),
    )

    def fake_yahoo(self, query):
        calls["count"] += 1
        return []

    monkeypatch.setattr(YahooFinanceSearchProvider, "_search_yahoo", fake_yahoo)
    provider = YahooFinanceSearchProvider()

    assert provider.search("  tcs ")
    assert provider.search("TCS")
    assert calls["count"] == 1
