from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine

def test_paper_trade_hits_stop():
    e=PaperTradingEngine(PaperRiskConfig(initial_capital=100000,risk_per_trade=.01,max_daily_loss=.02)); e.new_session('2026-01-02'); assert e.enter(100,98,104); trade=e.on_bar('2026-01-02',101,97,99); assert trade['reason']=='STOP'; assert trade['pnl']<0

def test_daily_loss_halts_engine():
    e=PaperTradingEngine(PaperRiskConfig(initial_capital=100000,risk_per_trade=.01,max_daily_loss=.01)); e.new_session('2026-01-02'); assert e.enter(100,90,120); e.on_bar('2026-01-02',101,89,90); assert e.halted
