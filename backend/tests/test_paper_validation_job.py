from datetime import date
import app.services.paper_validation_job as job

def test_daily_validation_deduplicates_symbols_and_stays_simulation(monkeypatch):
    calls=[]
    def fake_run(db,user_id,symbol,session,interval):
        calls.append((symbol,session,interval))
        return {"validation":{"status":"COMPLETE"}}
    monkeypatch.setattr(job,"run_dhan_paper_session",fake_run)
    result=job.run_daily_dhan_validation(object(),7,["TCS","tcs"," RELIANCE "],date(2026,9,28),"5")
    assert calls==[("TCS","2026-09-28","5"),("RELIANCE","2026-09-28","5")]
    assert result["completed"]==2
    assert result["failed"]==0
    assert result["broker_orders_enabled"] is False
