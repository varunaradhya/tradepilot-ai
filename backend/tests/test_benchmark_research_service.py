from datetime import date

from app.services.benchmark_research_service import download_intraday_benchmark_dataset
from app.services.instrument_master_service import IndianInstrument


class FakeMaster:
    def index_lookup(self, query):
        assert query == "NIFTY"
        return [IndianInstrument("13", "IDX_I", "NIFTY", "NIFTY 50")]


class FakeStore:
    def __init__(self):
        self.calls = []

    def merge(self, dataset, bars):
        self.calls.append((dataset, bars))


class FakeClient:
    pass


def test_benchmark_ingestion_uses_index_instrument(monkeypatch):
    import app.services.benchmark_research_service as module

    class Bar:
        def __init__(self, timestamp):
            self.timestamp = timestamp

    def fake_fetch(client, request, start, end):
        assert request.security_id == "13"
        assert request.exchange_segment == "IDX_I"
        assert request.instrument == "INDEX"
        assert request.interval == "5"
        return [Bar("2026-01-01T09:15:00")], {
            "bars": 1,
            "start": "2026-01-01T09:15:00",
            "end": "2026-01-01T09:15:00",
            "valid": True,
        }

    monkeypatch.setattr(module, "fetch_intraday_history", fake_fetch)
    store = FakeStore()
    result = download_intraday_benchmark_dataset(
        FakeClient(),
        "NIFTY",
        date(2026, 1, 1),
        date(2026, 1, 2),
        master=FakeMaster(),
        store=store,
    )

    assert result.dataset == "benchmark/NIFTY_intraday_5m"
    assert result.security_id == "13"
    assert result.valid is True
    assert store.calls[0][0] == "benchmark/NIFTY_intraday_5m"
