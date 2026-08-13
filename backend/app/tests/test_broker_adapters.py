from app.brokers.adapters import DhanBrokerAdapter
from app.brokers.registry import registry


class FakeDhanClient:
    def profile(self): return {"client": "test"}
    def holdings(self): return [{"tradingSymbol": "TCS", "totalQty": 2, "avgCostPrice": 3000}]
    def positions(self): return []
    def orders(self): return []
    def trades(self): return [{"tradingSymbol": "TCS", "transactionType": "BUY", "tradedQuantity": 2, "tradedPrice": 3000, "tradeId": "trade-1"}]


def test_dhan_adapter_is_registered_and_normalizes_data():
    assert registry.get("dhan") is DhanBrokerAdapter
    adapter = DhanBrokerAdapter(FakeDhanClient())
    holding = adapter.get_holdings()[0]
    trade = adapter.get_trades()[0]
    assert holding.symbol == "TCS"
    assert float(holding.quantity) == 2
    assert trade.side == "BUY"
    assert trade.transaction_id == "trade-1"
