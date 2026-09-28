from app.services.paper_replay_service import run_paper_replay


def _bars(n=35):
    rows=[]
    price=100.0
    for i in range(n):
        price += 0.2
        rows.append({"open":price-0.1,"high":price+0.2,"low":price-0.2,"close":price,"volume":1000+i*10})
    return rows


def test_replay_uses_simulation_only_and_returns_metrics():
    result=run_paper_replay(_bars(),session="2026-09-28",symbol="RELIANCE")
    assert result["mode"]=="SIMULATION_ONLY"
    assert result["processed_bars"]==35
    assert "metrics" in result


def test_replay_isolated_between_runs():
    a=run_paper_replay(_bars(),session="2026-09-28",symbol="RELIANCE")
    b=run_paper_replay(_bars(),session="2026-09-28",symbol="RELIANCE")
    assert a["processed_bars"]==b["processed_bars"]
    assert a["trades"]==b["trades"]
