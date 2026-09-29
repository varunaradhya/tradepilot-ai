from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine
import app.services.intraday_backtest as backtest_module


def _rows(n=40):
    rows=[]
    price=100.0
    for i in range(n):
        price += 0.15
        rows.append({"open":price-0.05,"high":price+0.2,"low":price-0.2,"close":price,"volume":1000.0,"session":"2026-01-02"})
    return rows


def test_intraday_requires_sufficient_data():
    rows=_rows(10)
    signal=generate_intraday_signal([r["open"] for r in rows],[r["high"] for r in rows],[r["low"] for r in rows],[r["close"] for r in rows],[r["volume"] for r in rows])
    assert signal["action"] == "NEUTRAL"
    assert signal["trade_direction"] == "LONG_ONLY"


def test_extreme_gap_is_blocked():
    rows=_rows()
    rows[0]["open"] = 110
    signal=generate_intraday_signal([r["open"] for r in rows],[r["high"] for r in rows],[r["low"] for r in rows],[r["close"] for r in rows],[r["volume"] for r in rows])
    assert signal["action"] == "NEUTRAL"
    assert signal["reason"] == "EXTREME_GAP"


def test_low_volume_blocks_breakout():
    rows=_rows()
    rows[-1]["high"] = rows[-1]["close"] + 2
    rows[-1]["volume"] = 100
    signal=generate_intraday_signal([r["open"] for r in rows],[r["high"] for r in rows],[r["low"] for r in rows],[r["close"] for r in rows],[r["volume"] for r in rows], opening_high=100)
    assert signal["action"] == "NEUTRAL"


def test_intraday_backtest_returns_metrics_and_declares_long_mode():
    rows=_rows(80)
    rows[25]["high"] = 104
    rows[25]["close"] = 103
    rows[25]["volume"] = 3000
    result=run_intraday_backtest(rows, IntradayBacktestConfig())
    assert "return_percent" in result
    assert "profit_factor" in result
    assert result["trade_direction"] == "LONG_ONLY"
    assert all(t["direction"] == "LONG" for t in result["trades_detail"])


def test_backtest_executes_completed_bar_signal_on_next_bar_open(monkeypatch):
    rows=_rows(30)

    def fake_signal(opens, highs, lows, closes, volumes, opening_high=None, opening_low=None, config=None):
        if len(closes) == 20:
            return {
                "action": "BUY",
                "entry": 100.0,
                "stop": 99.0,
                "target": 200.0,
            }
        return {"action": "NEUTRAL"}

    monkeypatch.setattr(backtest_module, "generate_intraday_signal", fake_signal)
    rows[20]["open"] = 110.0
    rows[20]["high"] = 111.0
    rows[20]["low"] = 109.0
    rows[20]["close"] = 110.5

    result = run_intraday_backtest(rows, IntradayBacktestConfig())
    assert result["signal_execution"] == "NEXT_BAR_OPEN"
    assert result["trades_detail"]
    trade = result["trades_detail"][0]
    assert trade["signal_entry"] == 100.0
    assert trade["entry"] > 105.0
    assert trade["entry"] != trade["signal_entry"]


def test_invalid_trade_direction_is_rejected():
    try:
        generate_intraday_signal([], [], [], [], [], config=IntradayConfig(trade_direction="SHORT_ONLY"))
    except ValueError as exc:
        assert "trade_direction" in str(exc)
    else:
        raise AssertionError("invalid trade direction should fail")


def test_paper_engine_rejects_short_entries_in_long_first_mode():
    engine = PaperTradingEngine(PaperRiskConfig(trade_direction="LONG_ONLY"))
    engine.new_session("2026-01-02")
    assert engine.enter(100, 98, 104, direction="SHORT") is False
    assert engine.enter(100, 98, 104, direction="LONG") is True
    assert engine.snapshot()["trade_direction"] == "LONG_ONLY"


def test_backtest_requires_valid_dataset_fingerprint():
    rows = _rows(40)
    try:
        run_intraday_backtest(
            rows,
            IntradayBacktestConfig(dataset_fingerprint="not-a-sha256", corporate_action_adjusted=True),
        )
    except ValueError as exc:
        assert "dataset_fingerprint" in str(exc)
    else:
        raise AssertionError("Invalid dataset fingerprint must be rejected")


def test_backtest_preserves_dataset_fingerprint():
    result = run_intraday_backtest(
        _rows(40),
        IntradayBacktestConfig(dataset_fingerprint="b" * 64, corporate_action_adjusted=False),
    )
    assert result["dataset_fingerprint"] == "b" * 64


def test_backtest_rejects_unknown_corporate_action_state_for_lineage():
    try:
        run_intraday_backtest(
            _rows(40),
            IntradayBacktestConfig(dataset_fingerprint="c" * 64),
        )
    except ValueError as exc:
        assert "corporate_action_adjusted" in str(exc)
    else:
        raise AssertionError("Lineage-backed research must declare corporate-action state")
