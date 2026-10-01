from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.dataset_provenance import fingerprint_market_bars

from app.services.historical_data_service import MarketBar
from app.services.intraday_batch_research import run_multi_stock_research
from app.services.research_store import ResearchStore


class FakeStore(ResearchStore):
    def __init__(self, datasets):
        self.datasets = datasets
        self.root = Path("/tmp/fake-research")

    def load(self, dataset):
        return self.datasets.get(dataset, [])

    def get_provenance(self, dataset):
        bars = self.datasets.get(dataset, [])
        if not bars:
            return None
        symbol = dataset.split("/", 1)[-1].split("_", 1)[0]
        interval = dataset.rsplit("_", 1)[-1].removesuffix("m")
        return {
            "dataset_id": dataset,
            "symbol": symbol,
            "timeframe": f"{interval}m",
            "quality_status": "VALID",
            "content_fingerprint": fingerprint_market_bars(
                bars, symbol=symbol, timeframe=f"{interval}m"
            ),
            "corporate_action_adjusted": False,
        }


def _bars(start=100.0):
    bars = []
    price = start
    base = datetime(2025, 1, 2, 9, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
    for i in range(60):
        price += 0.2
        bars.append(MarketBar(base + timedelta(minutes=5 * i), price - .1, price + .2, price - .2, price, 1000))
    return bars


def test_batch_reports_missing_without_hiding_it():
    result = run_multi_stock_research(["TCS", "INFY"], store=FakeStore({"nse/TCS_intraday_5m": _bars()}))
    assert result["tested"] == 1
    assert result["missing_datasets"] == ["INFY"]
    assert result["results"][0]["symbol"] == "TCS"


def test_batch_deduplicates_and_normalizes_symbols():
    result = run_multi_stock_research(["tcs", " TCS "], store=FakeStore({"nse/TCS_intraday_5m": _bars()}))
    assert result["requested"] == ["TCS"]
    assert result["tested"] == 1


def test_batch_rejects_invalid_interval():
    try:
        run_multi_stock_research(["TCS"], interval="2", store=FakeStore({}))
    except ValueError as exc:
        assert "interval" in str(exc)
    else:
        raise AssertionError("Expected invalid interval to fail")
