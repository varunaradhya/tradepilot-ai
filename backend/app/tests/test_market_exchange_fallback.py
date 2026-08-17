import httpx
import pytest

from app.providers.market_data import MarketDataProviderError, YahooFinanceProvider


def test_plain_symbol_uses_nse_only(monkeypatch):
    YahooFinanceProvider._cache.clear()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json={"chart": {"error": None, "result": [{"meta": {"regularMarketPrice": 250.0, "previousClose": 245.0, "currency": "INR", "exchangeName": "NSE"}}]}})

    monkeypatch.setattr("app.providers.market_data.httpx.get", fake_get)
    quote = YahooFinanceProvider().get_quote("SAMPLE")
    assert quote.symbol == "SAMPLE"
    assert quote.price == 250.0
    assert quote.exchange == "NSE"
    assert all(".BO" not in url for url in calls)
    assert any("SAMPLE.NS" in url for url in calls)


def test_bse_suffix_is_rejected():
    with pytest.raises(MarketDataProviderError, match="Only NSE"):
        YahooFinanceProvider().get_quote("SAMPLE.BO")
