from datetime import datetime, timedelta


def test_clean_orb_research_keeps_symbol_sessions_separate(monkeypatch, tmp_path):
    root = tmp_path
    clean = root / "dhan_equity_clean"
    clean.mkdir()
    start = datetime(2026, 1, 2, 9, 15)
    rows = []
    for i in range(75):
        ts = start + timedelta(minutes=5 * i)
        rows.append(
            '{"timestamp": "%s", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}'
            % ts.isoformat()
        )
    (clean / "TCS.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")

    from scripts.run_clean_orb_research import load_symbol_dataset

    result = load_symbol_dataset(root, "TCS")
    assert len(result) == 75
    assert all(row["session"] == "2026-01-02" for row in result)
