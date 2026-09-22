import httpx

from app.brokers.dhan import DhanAPIError, DhanClient


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_retry_after_is_capped(monkeypatch):
    client = DhanClient("cid", "token", max_retries=1)
    sleeps = []
    monkeypatch.setattr("app.brokers.dhan.time.sleep", sleeps.append)
    monkeypatch.setattr("app.brokers.dhan.random.uniform", lambda *_: 0.0)
    responses = iter([
        FakeResponse(429, {"error": "rate"}, {"Retry-After": "999"}),
        FakeResponse(200, {"ok": True}),
    ])
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: next(responses))

    assert client._request("GET", "/profile") == {"ok": True}
    assert sleeps == [20.0]


def test_negative_retry_after_uses_bounded_exponential_backoff(monkeypatch):
    client = DhanClient("cid", "token", max_retries=1)
    sleeps = []
    monkeypatch.setattr("app.brokers.dhan.time.sleep", sleeps.append)
    monkeypatch.setattr("app.brokers.dhan.random.uniform", lambda *_: 0.0)
    responses = iter([
        FakeResponse(503, {"error": "unavailable"}, {"Retry-After": "-5"}),
        FakeResponse(200, {"ok": True}),
    ])
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: next(responses))

    assert client._request("GET", "/profile") == {"ok": True}
    assert sleeps == [1.5]


def test_retry_exhaustion_preserves_final_http_status(monkeypatch):
    client = DhanClient("cid", "token", max_retries=1)
    monkeypatch.setattr("app.brokers.dhan.time.sleep", lambda *_: None)
    monkeypatch.setattr("app.brokers.dhan.random.uniform", lambda *_: 0.0)
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: FakeResponse(502, {"error": "bad gateway"}))

    try:
        client._request("GET", "/profile")
    except DhanAPIError as exc:
        assert exc.status_code == 502
        assert "after 2 attempts" in str(exc)
    else:
        raise AssertionError("expected DhanAPIError")
