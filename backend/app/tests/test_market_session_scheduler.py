from datetime import datetime

from app.services.market_session_scheduler import scheduler_status


def test_nse_scheduler_is_active_during_weekday_session():
    result = scheduler_status(datetime(2026, 8, 18, 10, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Kolkata")))
    assert result["market"] == "NSE_EQ"
    assert result["session_active"] is True
    assert result["broker_orders_enabled"] is False


def test_nse_scheduler_is_inactive_outside_session():
    result = scheduler_status(datetime(2026, 8, 18, 16, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Kolkata")))
    assert result["session_active"] is False
