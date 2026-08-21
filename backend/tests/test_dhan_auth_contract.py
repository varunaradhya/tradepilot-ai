from app.brokers.dhan import DhanClient


def test_profile_uses_access_token_without_client_id(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"dhanClientId": "1234567890", "tokenValidity": "21/08/2026 23:59"}

    def fake_request(method, url, headers, json, timeout):
        captured.update({"method": method, "url": url, "headers": headers})
        return Response()

    monkeypatch.setattr("app.brokers.dhan.httpx.request", fake_request)
    result = DhanClient(" 1234567890 ", " token-with-padding ").profile()

    assert result["dhanClientId"] == "1234567890"
    assert captured["headers"]["access-token"] == "token-with-padding"
    assert "client-id" not in captured["headers"]


def test_market_quote_keeps_client_id_header(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"data": {}}

    def fake_request(method, url, headers, json, timeout):
        captured.update({"headers": headers, "json": json})
        return Response()

    monkeypatch.setattr("app.brokers.dhan.httpx.request", fake_request)
    DhanClient("1234567890", "token").market_ltp("NSE_FNO", [12345])

    assert captured["headers"]["client-id"] == "1234567890"
    assert captured["headers"]["access-token"] == "token"
    assert captured["json"] == {"NSE_FNO": [12345]}
