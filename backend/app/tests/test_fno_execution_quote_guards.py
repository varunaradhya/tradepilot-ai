from app.services.fno_strategy import select_option_contracts
from app.services.fno_algo_engine import build_autonomous_option_decision
from app.services import fno_backtest_service


def _bars(count=80):
    rows=[]
    price=100.0
    for i in range(count):
        price += 0.5
        rows.append({"open":price-0.1,"high":price+0.3,"low":price-0.3,"close":price,"volume":1000+(500 if i==count-1 else 0)})
    return rows


def _chain(**quote):
    contract={
        "strike":25000,"security_id":"CE1","last_price":100,
        "top_bid_price":quote.get("bid",99),"top_ask_price":quote.get("ask",100),
        "volume":100000,"oi":500000,"implied_volatility":15,
        "greeks":{"delta":0.52}
    }
    return {"oc":{"25000":{"ce":contract}}}


def test_strategy_rejects_contract_without_executable_bid_or_ask():
    assert select_option_contracts(_chain(ask=0), "BULLISH") == []
    assert select_option_contracts(_chain(bid=0), "BULLISH") == []


def test_autonomous_decision_never_uses_ltp_when_ask_is_missing():
    result=build_autonomous_option_decision(
        underlying={"symbol":"NIFTY","capital":300000},
        bars=_bars(),
        option_chain=_chain(ask=0),
        lot_size=75,
    )
    assert result["decision"]=="NO_TRADE"
    assert result["reason"]=="NO_OPTION_CONTRACT_PASSED_FILTERS"


def test_historical_backtest_never_uses_ltp_as_entry_quote(monkeypatch):
    bars=[{"open":100,"high":101,"low":99,"close":100,"timestamp":i} for i in range(62)]
    chains=[{"oc":{"25000":{"ce":{"strike":25000,"option_type":"CE","last_price":100}}}} for _ in bars]
    decision={"decision":"QUALIFIED","quantity":75,"entry":100,"stop":95,"target":120,
              "contract":{"strike":25000,"option_type":"CE","last_price":100}}
    monkeypatch.setattr(fno_backtest_service,"replay_autonomous_option_decisions",
                        lambda **kwargs:[{"bar_index":60,"timestamp":60,"decision":decision}])
    result=fno_backtest_service.run_fno_backtest(
        underlying={"symbol":"NIFTY"},bars=bars,option_chain_snapshots=chains,lot_size=75
    )
    assert result["trades"]==0
