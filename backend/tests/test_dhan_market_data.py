from app.brokers.dhan import DhanClient


def test_ltp_normalizes_instrument_ids_and_uses_marketfeed_endpoint(monkeypatch):
    client = DhanClient("client", "token", max_retries=0)
    calls = []

    def fake_request(method, path, payload=None):
        calls.append((method, path, payload))
        return {"data": {"NSE_EQ": {"1333": {"last_price": 123.45}}}}

    monkeypatch.setattr(client, "_request", fake_request)

    result = client.ltp({"NSE_EQ": [1333]})

    assert result["data"]["NSE_EQ"]["1333"]["last_price"] == 123.45
    assert calls == [("POST", "/marketfeed/ltp", {"NSE_EQ": ["1333"]})]


def test_ltp_rejects_empty_instrument_map():
    client = DhanClient("client", "token", max_retries=0)

    try:
        client.ltp({})
    except ValueError as exc:
        assert "instruments" in str(exc)
    else:
        raise AssertionError("empty instrument map must be rejected")


def test_ltp_rejects_empty_security_id_list():
    client = DhanClient("client", "token", max_retries=0)

    try:
        client.ltp({"NSE_EQ": []})
    except ValueError as exc:
        assert "instruments" in str(exc)
    else:
        raise AssertionError("empty security-id list must be rejected")
