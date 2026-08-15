import httpx

from app.providers.market_data import YahooFinanceProvider


def test_plain_symbol_falls_back_from_nse_to_bse(monkeypatch):
    YahooFinanceProvider._cache.clear()
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        request = httpx.Request("GET", url)
        if ".NS" in url:
            return httpx.Response(
                200,
                request=request,
                json={
                    "chart": {
                        "error": {"description": "No data found"},
                        "result": None,
                    }
                },
            )
        return httpx.Response(
            200,
            request=request,
            json={
                "chart": {
                    "error": None,
                    "result": [{
                        "meta": {
                            "regularMarketPrice": 250.0,
                            "previousClose": 245.0,
                            "currency": "INR",
                            "exchangeName": "BSE",
                        }
                    }],
                }
            },
        )

    monkeypatch.setattr("app.providers.market_data.httpx.get", fake_get)
    quote = YahooFinanceProvider().get_quote("SAMPLE")

    assert quote.symbol == "SAMPLE"
    assert quote.price == 250.0
    assert quote.exchange == "BSE"
    assert any("SAMPLE.NS" in url for url in calls)
    assert any("SAMPLE.BO" in url for url in calls)
