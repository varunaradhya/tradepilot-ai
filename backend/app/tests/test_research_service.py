from datetime import date, datetime, timezone

from app.services.dhan_historical_service import HistoricalRequest
from app.services.historical_data_service import MarketBar
from app.services.instrument_master_service import IndianInstrument, InstrumentMaster
from app.services.research_service import download_daily_dataset, resolve_indian_symbol


class FakeClient:
    def historical_daily(self, **kwargs):
        assert kwargs["security_id"] == "1333"
        return {
            "timestamp": [1735776000, 1735862400],
            "open": [100, 101],
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 1200],
        }


class FakeStore:
    def __init__(self):
        self.saved = None

    def save(self, dataset, bars):
        self.saved = (dataset, bars)
        return {"dataset": dataset, "valid": True, "bars": len(bars)}


def fake_master():
    master = InstrumentMaster()
    master._items = [IndianInstrument("1333", "NSE_EQ", "TCS", "Tata Consultancy Services")]
    return master


def test_resolve_requires_exact_nse_symbol():
    assert resolve_indian_symbol("tcs", fake_master()).security_id == "1333"


def test_download_daily_dataset_persists_validated_bars():
    store = FakeStore()
    result = download_daily_dataset(
        FakeClient(), "TCS", date(2025, 1, 1), date(2025, 1, 5), master=fake_master(), store=store
    )
    assert result.symbol == "TCS"
    assert result.bars == 2
    assert store.saved[0] == "nse/TCS_daily"
