from datetime import date
import app.services.paper_validation_job as job
from app.services.paper_validation_service import (
    DEFAULT_VALIDATION_SYMBOLS, MIN_VALIDATION_SYMBOLS, MAX_VALIDATION_SYMBOLS,
    normalize_validation_symbols,
)

def test_default_validation_universe_is_indian_equity_shape():
    symbols = normalize_validation_symbols(DEFAULT_VALIDATION_SYMBOLS)
    assert len(symbols) >= MIN_VALIDATION_SYMBOLS
    assert len(symbols) <= MAX_VALIDATION_SYMBOLS
    assert all(".NS" not in symbol and ".BO" not in symbol for symbol in symbols)

def test_validation_universe_normalizes_and_deduplicates():
    assert normalize_validation_symbols(["tcs.NS", "TCS", " reliancE.BO ", "INFY"]) == ["TCS", "RELIANCE", "INFY"]

def test_validation_universe_rejects_too_small():
    try:
        normalize_validation_symbols(["TCS", "INFY"])
    except ValueError as exc:
        assert "3 to 10" in str(exc)
    else:
        raise AssertionError("expected validation universe size failure")

def test_daily_validation_finalizes_one_day_across_symbols(monkeypatch):
    calls = []
    def fake_run(db, user_id, symbol, session, interval, finalize_validation=True):
        calls.append((symbol, finalize_validation))
        return {"validation": {"status": "COMPLETE", "trades": 0, "net_pnl": 0.0}}
    finalized = {}
    def fake_finalize(db, user_id, run_key, session_date, symbols):
        finalized.update({"run": run_key, "date": session_date, "symbols": symbols})
        return type("Day", (), {"status": "COMPLETE"})()
    monkeypatch.setattr(job, "run_dhan_paper_session", fake_run)
    monkeypatch.setattr(job, "finalize_multi_symbol_validation_day", fake_finalize)

    result = job.run_daily_dhan_validation(object(), 7, ["TCS", "tcs", "INFY", "RELIANCE"], date(2026, 9, 28), "5")

    assert calls == [("TCS", False), ("INFY", False), ("RELIANCE", False)]
    assert finalized["symbols"] == ["TCS", "INFY"]
    assert result["day_status"] == "COMPLETE"
    assert result["broker_orders_enabled"] is False


def test_daily_validation_rejects_nse_holiday():
    import pytest
    with pytest.raises(ValueError, match="not an NSE equity regular trading session"):
        job.run_daily_dhan_validation(object(), 7, ["TCS", "INFY", "RELIANCE"], date(2026, 10, 2), "5")
