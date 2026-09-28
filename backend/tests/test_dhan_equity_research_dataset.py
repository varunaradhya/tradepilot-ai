from datetime import datetime, timezone
import json
import sqlite3

from scripts.build_dhan_equity_research_dataset import build_research_dataset


def _ts(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def _db(tmp_path):
    path = tmp_path / "market.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE equity_bars (
            dataset_id TEXT, symbol TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        )
    """)
    return conn, path


def _full_session(conn, symbol="TCS"):
    base = datetime(2026, 1, 2, 3, 45, tzinfo=timezone.utc)
    rows = []
    for i in range(75):
        ts = int((base.timestamp() + i * 300))
        price = 100 + i * 0.1
        rows.append(("equity_nse_discovery_5m", symbol, ts, price, price + 1, price - 1, price + .5, 1000))
    conn.executemany("INSERT INTO equity_bars VALUES (?,?,?,?,?,?,?,?)", rows)


def test_builder_preserves_source_and_exports_full_session(tmp_path):
    conn, path = _db(tmp_path)
    _full_session(conn)
    conn.commit()
    before = conn.execute("SELECT count(*) FROM equity_bars").fetchone()[0]
    conn.close()

    out = tmp_path / "research"
    manifest = build_research_dataset(path, out)

    conn = sqlite3.connect(path)
    after = conn.execute("SELECT count(*) FROM equity_bars").fetchone()[0]
    conn.close()

    assert before == after == 75
    assert manifest["clean_rows"] == 75
    assert manifest["quarantine_rows"] == 0
    assert manifest["source_unchanged"] is True


def test_builder_quarantines_negative_volume_and_partial_sessions(tmp_path):
    conn, path = _db(tmp_path)
    _full_session(conn)
    conn.execute(
        "UPDATE equity_bars SET volume=-10 WHERE symbol='TCS' AND timestamp=?",
        (_ts("2026-01-02T04:00:00"),),
    )
    # A second symbol has only the first 10 bars: it must not be padded.
    base = _ts("2026-01-02T03:45:00")
    for i in range(10):
        ts = base + i * 300
        conn.execute(
            "INSERT INTO equity_bars VALUES (?,?,?,?,?,?,?,?)",
            ("equity_nse_discovery_5m", "INFY", ts, 100, 101, 99, 100.5, 1000),
        )
    conn.commit()
    conn.close()

    manifest = build_research_dataset(path, tmp_path / "research")
    assert manifest["clean_rows"] == 74
    assert manifest["quarantine_reasons"]["NEGATIVE_VOLUME"] == 1
    assert manifest["session_exclusions"]["EXCLUDED_PARTIAL_SESSION"] == 1


def test_builder_excludes_weekend_without_deleting_source(tmp_path):
    conn, path = _db(tmp_path)
    base = _ts("2026-01-03T03:45:00")
    for i in range(75):
        conn.execute(
            "INSERT INTO equity_bars VALUES (?,?,?,?,?,?,?,?)",
            ("equity_nse_discovery_5m", "INFY", base + i * 300, 100, 101, 99, 100.5, 1000),
        )
    conn.commit()
    conn.close()

    manifest = build_research_dataset(path, tmp_path / "research")
    assert manifest["clean_rows"] == 0
    assert manifest["quarantine_reasons"]["WEEKEND"] == 75

    report = json.loads((tmp_path / "research" / "equity_nse_discovery_5m_manifest.json").read_text())
    assert report["source_unchanged"] is True
