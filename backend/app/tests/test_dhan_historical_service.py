from datetime import date

import pytest

from app.brokers.dhan import DhanAPIError, DhanClient
from app.services.dhan_historical_service import HistoricalRequest, fetch_daily_history, fetch_intraday_history


class FakeDhanClient(DhanClient):
    def __init__(self, payloads):
        super().__init__("client", "token")
        self.payloads = list(payloads)
        self.calls = []

    def historical_daily(self, **kwargs):
        self.calls.append(("daily", kwargs))
        return self.payloads.pop(0)

    def historical_intraday(self, **kwargs):
        self.calls.append(("intraday", kwargs))
        return self.payloads.pop(0)


def payload(start=1704067200, count=2):
    return {
        "timestamp": [start + index * 86400 for index in range(count)],
        "open": [100 + index for index in range(count)],
        "high": [102 + index for index in range(count)],
        "low": [99 + index for index in range(count)],
        "close": [101 + index for index in range(count)],
        "volume": [1000, 1200][:count],
    }


def test_daily_history_normalizes_dhan_columnar_response():
    client = FakeDhanClient([payload()])
    bars, diagnostics = fetch_daily_history(
        client,
        HistoricalRequest("1333"),
        date(2024, 1, 1),
        date(2024, 2, 1),
    )

    assert len(bars) == 2
    assert bars[0].close == 101
    assert diagnostics["valid"] is True
    assert client.calls[0][1]["security_id"] == "1333"


def test_intraday_history_chunks_requests_at_90_days():
    client = FakeDhanClient([payload(count=1), payload(start=1704153600, count=1)])
    bars, diagnostics = fetch_intraday_history(
        client,
        HistoricalRequest("1333", interval="15"),
        date(2024, 1, 1),
        date(2024, 7, 1),
    )

    assert len(client.calls) == 3
    assert client.calls[0][1]["from_date"] == "2024-01-01"
    assert client.calls[0][1]["to_date"] == "2024-03-31"
    assert diagnostics["bars"] == 2
    assert len(bars) == 2


def test_intraday_rejects_unsupported_interval():
    with pytest.raises(ValueError, match="interval"):
        fetch_intraday_history(
            FakeDhanClient([]),
            HistoricalRequest("1333", interval="30"),
            date(2024, 1, 1),
            date(2024, 2, 1),
        )


def test_inconsistent_dhan_arrays_raise_api_error():
    bad = payload()
    bad["close"] = [101]
    with pytest.raises(DhanAPIError, match="inconsistent"):
        fetch_daily_history(
            FakeDhanClient([bad]),
            HistoricalRequest("1333"),
            date(2024, 1, 1),
            date(2024, 2, 1),
        )
