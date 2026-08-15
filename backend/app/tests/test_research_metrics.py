from app.services.market_regime import classify_market_regime
from app.services.research_metrics import summarize_equity_curve, summarize_trades


def test_market_regime_detects_bullish_series():
    closes = [100 + i * 1.2 for i in range(80)]
    regime = classify_market_regime(closes)
    assert regime.label == "BULL"
    assert regime.confidence > 0


def test_market_regime_requires_enough_data():
    regime = classify_market_regime([100] * 10)
    assert regime.label == "INSUFFICIENT_DATA"


def test_equity_metrics_and_trade_summary_are_deterministic():
    equity = summarize_equity_curve([100000, 101000, 100000, 103000])
    trades = summarize_trades([{"pnl": 100}, {"pnl": -50}, {"pnl": -25}, {"pnl": 75}])
    assert equity["max_drawdown_percent"] > 0
    assert trades["win_rate_percent"] == 50.0
    assert trades["worst_losing_streak"] == 2
    assert trades["profit_factor"] == 2.3333
