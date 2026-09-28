from datetime import date
import pytest
from app.services.corporate_action_service import CorporateActionFactor,cumulative_adjustment_factor,adjust_ohlcv
def test_split_factor_adjustment():
    action=CorporateActionFactor("TCS",date(2026,1,10),"SPLIT",0.5,"TEST")
    assert cumulative_adjustment_factor([action])["TCS"]==0.5
    row=adjust_ohlcv({"open":100,"high":110,"low":90,"close":105,"volume":1000},0.5)
    assert row["close"]==52.5 and row["volume"]==2000
def test_invalid_factor_rejected():
    with pytest.raises(ValueError): cumulative_adjustment_factor([CorporateActionFactor("TCS",date(2026,1,1),"SPLIT",0,"TEST")])
