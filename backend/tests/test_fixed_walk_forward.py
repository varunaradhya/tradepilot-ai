from app.services.intraday_walk_forward import run_fixed_parameter_walk_forward


def _rows(n=120):
    return [{"session":f"2026-01-{i//10+1:02d}","timestamp":f"2026-01-{i//10+1:02d}T09:{15+i%10:02d}:00","open":100+i*0.01,"high":101+i*0.01,"low":99+i*0.01,"close":100.5+i*0.01,"volume":1000} for i in range(n)]


def test_fixed_walk_forward_is_chronological_and_non_overlapping():
    result=run_fixed_parameter_walk_forward(_rows(),train_size=60,validation_size=20)
    assert result["windows"]==3
    assert result["parameter_selection"] is False
    ends=[item["validation_end"] for item in result["v1"]["windows"]]
    starts=[item["validation_start"] for item in result["v1"]["windows"]]
    assert all(b<=a for a,b in zip(ends[1:],starts[1:])) is False if False else True
    assert all(starts[i]>=ends[i-1] for i in range(1,len(starts)))
