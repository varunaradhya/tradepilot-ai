from app.services.fno_strategy_v1 import generate_signal, position_size
from app.services.fno_validation import evaluate_backtest, evaluate_paper, final_promotion, chronological_split, walk_forward_windows


def _bars(n=60):
    out=[]
    for i in range(n):
        base=100+i*0.2
        out.append({"open":base,"high":base+1,"low":base-1,"close":base+0.5,"volume":2000})
    for i in range(3): out[i]["high"]=101; out[i]["low"]=99
    out[-1].update({"close":110,"high":111,"volume":3000})
    return out


def test_position_size_is_lot_aligned():
    assert position_size(100000,100,95,25)%25==0


def test_strategy_is_deterministic_and_never_forces_trade():
    signal=generate_signal(_bars())
    assert signal.action in {"BUY","SELL","NO_TRADE"}
    assert signal.action==generate_signal(_bars()).action


def test_validation_rejects_weak_backtest():
    result=evaluate_backtest({"trades":100,"profit_factor":1.1,"expectancy_per_trade":1,"max_drawdown_percent":5,"return_percent":10},{"2022":5,"2023":5})
    assert not result["eligible"]


def test_paper_requires_minimum_days():
    result=evaluate_paper({"profit_factor":1.5,"expectancy_per_trade":10,"net_pnl":1000},30)
    assert not result["eligible"]


def test_live_promotion_requires_every_gate():
    result=final_promotion({"eligible":True},{"eligible":True},True,False)
    assert result["status"]=="REJECT"


def test_chronological_split_has_no_shuffle():
    rows=[{"timestamp":i} for i in range(10)]
    train,valid,test=chronological_split(rows)
    assert train[-1]["timestamp"] < valid[0]["timestamp"] < test[0]["timestamp"]


def test_walk_forward_windows_are_ordered_and_non_overlapping_by_default():
    rows=[{"timestamp":i} for i in range(20)]
    windows=walk_forward_windows(rows,10,5)
    assert len(windows)==2
    assert windows[0][0][-1]["timestamp"] < windows[0][1][0]["timestamp"]
