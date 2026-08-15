import httpx
import pytest

from app.providers.market_data import MarketDataProviderError, YahooFinanceProvider


def test_nse_symbol_is_added_for_plain_indian_symbol():
    assert YahooFinanceProvider._provider_symbol("tcs") == "TCS.NS"


def test_existing_exchange_suffix_is_preserved():
    assert YahooFinanceProvider._provider_symbol("TCS.NS") == "TCS.NS"
    assert YahooFinanceProvider._provider_symbol("tcs.bo") == "TCS.BO"


def test_empty_market_symbol_is_rejected():
    with pytest.raises(MarketDataProviderError, match="Symbol is required"):
        YahooFinanceProvider._provider_symbol("   ")


def test_rate_limit_falls_back_to_second_yahoo_host(monkeypatch):
    YahooFinanceProvider._cache.clear()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        request = httpx.Request("GET", url)
        if len(calls) == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(
            200,
            request=request,
            json={
                "chart": {
                    "error": None,
                    "result": [{
                        "meta": {
                            "regularMarketPrice": 3500,
                            "previousClose": 3450,
                            "currency": "INR",
                            "exchangeName": "NSE",
                        }
                    }],
                }
            },
        )

    monkeypatch.setattr("app.providers.market_data.httpx.get", fake_get)
    quote = YahooFinanceProvider().get_quote("TCS")

    assert quote.symbol == "TCS"
    assert quote.price == 3500
    assert len(calls) == 2
    assert "query1.finance.yahoo.com" in calls[0]
    assert "query2.finance.yahoo.com" in calls[1]


def test_market_provider_uses_ttl_cache(monkeypatch):
    YahooFinanceProvider._cache.clear()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "chart": {
                    "error": None,
                    "result": [{
                        "meta": {
                            "regularMarketPrice": 3500,
                            "previousClose": 3450,
                            "currency": "INR",
                            "exchangeName": "NSE",
                        }
                    }],
                }
            },
        )

    monkeypatch.setattr("app.providers.market_data.httpx.get", fake_get)
    provider = YahooFinanceProvider()
    provider.get_quote("TCS")
    provider.get_quote("TCS")

    assert len(calls) == 1
