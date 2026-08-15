from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine
from app.services.paper_trading_service import paper_summary


def test_paper_trade_hits_stop():
    e=PaperTradingEngine(PaperRiskConfig(initial_capital=100000,risk_per_trade=.01,max_daily_loss=.02)); e.new_session('2026-01-02'); assert e.enter(100,98,104); trade=e.on_bar('2026-01-02',101,97,99); assert trade['reason']=='STOP'; assert trade['pnl']<0


def test_daily_loss_halts_engine():
    e=PaperTradingEngine(PaperRiskConfig(initial_capital=100000,risk_per_trade=.01,max_daily_loss=.01)); e.new_session('2026-01-02'); assert e.enter(100,90,120); e.on_bar('2026-01-02',101,89,90); assert e.halted


def test_paper_summary_separates_open_and_realized_pnl():
    class Trade:
        status="CLOSED"; pnl=150.0
    class OpenTrade:
        status="OPEN"; pnl=25.0
    result=paper_summary([Trade(),OpenTrade()])
    assert result["trades"]==2
    assert result["closed_trades"]==1
    assert result["open_trades"]==1
    assert result["realized_pnl"]==150.0
    assert result["pnl"]==175.0
