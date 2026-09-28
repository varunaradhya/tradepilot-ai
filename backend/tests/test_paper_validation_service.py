from datetime import date
from app.services.paper_validation_service import validation_run_key

def test_validation_run_is_bounded():
    assert validation_run_key(date(2026,9,1))=="P10_2026-09-01_30D"
    try: validation_run_key(date(2026,9,1),31)
    except ValueError: return
    raise AssertionError("validation window must be capped")
