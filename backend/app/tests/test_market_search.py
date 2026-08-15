import httpx

from app.providers.market_search import YahooFinanceSearchProvider


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
    results = YahooFinanceSearchProvider().search("tcs")

    assert [(x.symbol, x.exchange) for x in results] == [("TCS", "NSE"), ("TCS", "BSE")]


def test_search_requires_two_characters():
    assert YahooFinanceSearchProvider().search("t") == []
