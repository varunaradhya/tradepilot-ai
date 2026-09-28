from datetime import date, datetime, timezone
from app.services.paper_validation_service import validation_run_key
from app.services.market_session_scheduler import scheduler_status, is_trading_day

def test_validation_run_is_bounded():
    assert validation_run_key(date(2026,9,1))=="P10_2026-09-01_30D"
    try: validation_run_key(date(2026,9,1),31)
    except ValueError: return
    raise AssertionError("validation window must be capped")

def test_market_scheduler_rejects_weekend():
    result=scheduler_status(datetime(2026,9,26,10,0,tzinfo=timezone.utc))
    assert result["weekday"] is False
    assert result["session_active"] is False

def test_market_scheduler_honours_configured_holiday():
    holiday=date(2026,9,25)
    assert is_trading_day(holiday,frozenset({holiday})) is False
