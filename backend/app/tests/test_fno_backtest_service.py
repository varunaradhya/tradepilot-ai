from app.services import fno_backtest_service as service


def _chain(price=100.0, low=100.0, high=100.0):
    return {"oc": {"25000": {"ce": {"strike": 25000, "option_type": "CE", "ask": price, "bid": price, "last_price": price, "low": low, "high": high}}}}


def _decision():
    return {
        "decision": "QUALIFIED",
        "direction": "BULLISH",
        "quantity": 75,
        "entry": 100,
        "stop": 90,
        "target": 120,
        "contract": {"strike": 25000, "option_type": "CE", "ask": 100, "bid": 100, "last_price": 100},
    }


def test_fno_backtest_uses_next_bar_for_entry_and_target(monkeypatch):
    bars = [{"open": 100, "high": 101, "low": 99, "close": 100, "timestamp": i} for i in range(62)]
    chains = [_chain() for _ in bars]
    chains[61] = _chain(price=125, low=100, high=125)
    decisions = [{"bar_index": 60, "timestamp": 60, "decision": _decision()}]
    monkeypatch.setattr(service, "replay_autonomous_option_decisions", lambda **kwargs: decisions)

    result = service.run_fno_backtest(
        underlying={"symbol": "NIFTY"},
        bars=bars,
        option_chain_snapshots=chains,
        lot_size=75,
    )

    assert result["trades"] == 1
    assert result["trades_detail"][0]["entry_bar_index"] == 61
    assert result["trades_detail"][0]["reason"] == "TARGET"
    assert result["trades_detail"][0]["pnl"] > 0


def test_fno_backtest_rejects_invalid_lot_size():
    try:
        service.run_fno_backtest(underlying={"symbol": "NIFTY"}, bars=[], option_chain_snapshots=[], lot_size=0)
    except ValueError as exc:
        assert "lot_size" in str(exc)
    else:
        raise AssertionError("expected invalid lot size to fail")


def test_fno_backtest_reports_no_trades_without_qualified_decisions(monkeypatch):
    bars = [{"open": 100, "high": 101, "low": 99, "close": 100, "timestamp": i} for i in range(61)]
    chains = [_chain() for _ in bars]
    monkeypatch.setattr(service, "replay_autonomous_option_decisions", lambda **kwargs: [])

    result = service.run_fno_backtest(
        underlying={"symbol": "NIFTY"},
        bars=bars,
        option_chain_snapshots=chains,
        lot_size=75,
    )
    assert result["trades"] == 0
    assert result["ending_capital"] == result["initial_capital"]
