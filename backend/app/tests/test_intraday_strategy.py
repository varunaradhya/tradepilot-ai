from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal
from app.services.intraday_backtest import IntradayBacktestConfig, run_intraday_backtest
from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine


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
