from datetime import datetime, timezone
import sqlite3

from scripts.audit_dhan_equity_sqlite import audit


def _db(tmp_path):
    path = tmp_path / "market.sqlite"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE equity_bars (
            dataset_id TEXT,
            symbol TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL
        )
        """
    )
    return conn, path


def _ts(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def test_audit_detects_negative_volume_and_out_of_session_rows(tmp_path):
    conn, path = _db(tmp_path)
    conn.executemany(
        "INSERT INTO equity_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("equity_nse_discovery_5m", "TCS", _ts("2026-01-02T03:45:00"), 100, 101, 99, 100.5, 10),
            ("equity_nse_discovery_5m", "TCS", _ts("2026-01-02T03:50:00"), 100.5, 102, 100, 101, -1),
            ("equity_nse_discovery_5m", "TCS", _ts("2026-01-02T13:00:00"), 101, 102, 100, 101.5, 10),
            ("other", "TCS", _ts("2026-01-02T03:45:00"), 1, 1, 1, 1, 1),
        ],
    )
    conn.commit()
    conn.close()

    result = audit(path, "equity_nse_discovery_5m")

    assert result["total_bars"] == 3
    assert result["negative_volume_count"] == 1
    assert result["outside_regular_session_count"] == 1
    assert result["source_unchanged"] is True


def test_audit_flags_incomplete_regular_session(tmp_path):
    conn, path = _db(tmp_path)
    conn.executemany(
        "INSERT INTO equity_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("equity_nse_discovery_5m", "INFY", _ts("2026-01-02T03:46:00"), 100, 101, 99, 100.5, 10),
            ("equity_nse_discovery_5m", "INFY", _ts("2026-01-02T03:50:00"), 100.5, 102, 100, 101, 10),
        ],
    )
    conn.commit()
    conn.close()

    result = audit(path, "equity_nse_discovery_5m")

    assert result["incomplete_session_count"] == 1
