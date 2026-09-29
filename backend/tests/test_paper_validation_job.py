from datetime import date
import app.services.paper_validation_job as job


def test_daily_validation_deduplicates_symbols_and_stays_simulation(monkeypatch):
    calls = []

    def fake_run(db, user_id, symbol, session, interval, finalize_validation=True):
        calls.append((symbol, session, interval))
        return {"validation": {"status": "COMPLETE"}}

    def fake_finalize(db, user_id, run_key, session_date, symbols):
        return type("Day", (), {"status": "COMPLETE"})()

    def fake_manifest(db, user_id, run_key):
        return type("Manifest", (), {"root_hash": "a" * 64})()

    monkeypatch.setattr(job, "run_dhan_paper_session", fake_run)
    monkeypatch.setattr(job, "finalize_multi_symbol_validation_day", fake_finalize)
    monkeypatch.setattr(job, "persist_validation_manifest", fake_manifest)

    result = job.run_daily_dhan_validation(
        object(), 7, ["TCS", "tcs", " RELIANCE ", "INFY"], date(2026, 9, 28), "5"
    )

    assert calls == [
        ("TCS", "2026-09-28", "5"),
        ("RELIANCE", "2026-09-28", "5"),
        ("INFY", "2026-09-28", "5"),
    ]
    assert result["completed_symbols"] == 3
    assert result["failed_symbols"] == 0
    assert result["broker_orders_enabled"] is False
