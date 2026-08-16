from app.services.option_research_pipeline import normalize_rolling, summarize
from app.services.option_strategy_v1 import option_position_size

def test_option_position_size_is_lot_aligned():
    assert option_position_size(100000,100,80,65) % 65 == 0

def test_normalize_rolling_maps_call_rows():
    payload={'data':{'ce':{'timestamp':[1],'open':[100],'high':[110],'low':[90],'close':[105],'volume':[1000],'strike':[25000],'oi':[5000],'iv':[15],'spot':[25010]},'pe':None}}
    rows=normalize_rolling(payload)
    assert len(rows)==1 and rows[0]['side']=='ce' and rows[0]['strike']==25000

def test_summary_counts_pnl():
    result=summarize([{'pnl':100,'date':'2025-01-01'},{'pnl':-50,'date':'2025-01-02'}])
    assert result['trades']==2 and result['wins']==1 and result['losses']==1 and result['profit_factor']==2
