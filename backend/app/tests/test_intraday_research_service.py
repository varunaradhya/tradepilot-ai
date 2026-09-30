from datetime import date, datetime

from app.services.historical_data_service import MarketBar
from app.services.dataset_provenance import fingerprint_market_bars
from app.services.intraday_research_service import backtest_intraday_dataset, download_intraday_dataset


class FakeInstrument:
    symbol = "TCS"
    security_id = "1333"
    exchange_segment = "NSE_EQ"


class FakeMaster:
    def load(self):
        return [FakeInstrument()]


class FakeClient:
    def historical_intraday(self, **kwargs):
        assert kwargs["security_id"] == "1333"
        assert kwargs["interval"] == "5"
        return {
            "timestamp": [1735812000, 1735812300],
            "open": [100, 101],
            "high": [101, 102],
            "low": [99, 100],
            "close": [100.5, 101.5],
            "volume": [1000, 1200],
        }


class FakeStore:
    def __init__(self):
        self.saved = {}
        self.provenance = {}

    def save(self, dataset, bars):
        self.saved[dataset] = list(bars)
        return {"dataset": dataset, "valid": True}

    def load(self, dataset):
        return self.saved.get(dataset, [])

    def get_provenance(self, dataset):
        return self.provenance.get(dataset)


def test_download_intraday_dataset_uses_nse_security_id():
    store = FakeStore()
    result = download_intraday_dataset(
        FakeClient(), "TCS", date(2025, 1, 1), date(2025, 1, 2), master=FakeMaster(), store=store
    )
    assert result.symbol == "TCS"
    assert result.interval == "5"
    assert result.dataset == "nse/TCS_intraday_5m"
    assert result.bars == 2
    assert store.saved[result.dataset]


def test_backtest_intraday_dataset_requires_stored_data():
    try:
        backtest_intraday_dataset("TCS", store=FakeStore())
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected missing dataset error")


def test_backtest_intraday_dataset_adds_sessions():
    store = FakeStore()
    rows = []
    base = datetime(2026, 1, 2, 9, 15)
    for i in range(35):
        price = 100 + i * 0.1
        rows.append(MarketBar(base.replace(minute=15 + i), price, price + 0.2, price - 0.2, price, 1000))
    store.saved["nse/TCS_intraday_5m"] = rows
    store.provenance["nse/TCS_intraday_5m"] = {
        "dataset_id": "nse/TCS_intraday_5m",
        "symbol": "TCS",
        "timeframe": "5m",
        "quality_status": "VALID",
        "content_fingerprint": fingerprint_market_bars(rows, symbol="TCS", timeframe="5m"),
        "corporate_action_adjusted": False,
    }
    result = backtest_intraday_dataset("TCS", store=store)
    assert result["symbol"] == "TCS"
    assert "trades" in result


def test_backtest_intraday_dataset_rejects_unknown_corporate_action_state():
    store = FakeStore()
    base = datetime(2026, 1, 2, 9, 15)
    rows = [MarketBar(base.replace(minute=15 + i), 100, 100.2, 99.8, 100, 1000) for i in range(35)]
    store.saved["nse/TCS_intraday_5m"] = rows
    store.provenance["nse/TCS_intraday_5m"] = {
        "dataset_id": "nse/TCS_intraday_5m", "symbol": "TCS", "timeframe": "5m",
        "quality_status": "VALID",
        "content_fingerprint": fingerprint_market_bars(rows, symbol="TCS", timeframe="5m"),
        "corporate_action_adjusted": None,
    }
    try:
        backtest_intraday_dataset("TCS", store=store)
    except ValueError as exc:
        assert "corporate-action" in str(exc)
    else:
        raise AssertionError("Expected unknown corporate-action state to block research")


def test_backtest_intraday_dataset_rejects_missing_provenance():
    store = FakeStore()
    base = datetime(2026, 1, 2, 9, 15)
    store.saved["nse/TCS_intraday_5m"] = [MarketBar(base, 100, 100.2, 99.8, 100, 1000)]
    try:
        backtest_intraday_dataset("TCS", store=store)
    except ValueError as exc:
        assert "missing provenance" in str(exc)
    else:
        raise AssertionError("Expected missing provenance to block research")
