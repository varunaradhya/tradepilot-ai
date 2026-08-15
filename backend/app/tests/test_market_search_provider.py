from app.providers.market_search import SearchInstrument, YahooFinanceSearchProvider


def test_nse_master_returns_non_popular_stock(monkeypatch):
    YahooFinanceSearchProvider._cache.clear()
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_load_nse_master",
        lambda timeout=8.0: [
            SearchInstrument("TCS", "Tata Consultancy Services Limited", "NSE"),
            SearchInstrument("ZYDUSLIFE", "Zydus Lifesciences Limited", "NSE"),
        ],
    )
    monkeypatch.setattr(YahooFinanceSearchProvider, "_search_yahoo", lambda self, query: [])

    results = YahooFinanceSearchProvider().search("zydus")

    assert results == [SearchInstrument("ZYDUSLIFE", "Zydus Lifesciences Limited", "NSE")]


def test_search_combines_nse_and_yahoo_without_duplicates(monkeypatch):
    YahooFinanceSearchProvider._cache.clear()
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_load_nse_master",
        lambda timeout=8.0: [SearchInstrument("TCS", "Tata Consultancy Services Limited", "NSE")],
    )
    monkeypatch.setattr(
        YahooFinanceSearchProvider,
        "_search_yahoo",
        lambda self, query: [
            SearchInstrument("TCS", "Tata Consultancy Services Limited", "NSE"),
            SearchInstrument("TCS", "Tata Consultancy Services Limited", "BSE"),
        ],
    )

    results = YahooFinanceSearchProvider().search("tcs")

    assert [(item.symbol, item.exchange) for item in results] == [
        ("TCS", "NSE"),
        ("TCS", "BSE"),
    ]
