from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def args():
    p = argparse.ArgumentParser(
        description=(
            "Safely isolate the current V3 rolling-series option dataset by removing "
            "legacy NULL-identity option rows after verifying they are exact duplicates."
        )
    )
    p.add_argument("--db", default="data/research/market_data.sqlite")
    p.add_argument("--backup", default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    a = args()
    db_path = Path(a.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    backup = Path(a.backup) if a.backup else db_path.with_name(
        f"{db_path.stem}.pre_v3_cleanup_{datetime.now():%Y%m%d_%H%M%S}{db_path.suffix}"
    )

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(option_bars)")]
        required = {"timestamp", "side", "strike_key", "contract_identity"}
        missing = sorted(required - set(cols))
        if missing:
            raise SystemExit(f"option_bars is missing required columns: {missing}")

        total = con.execute("SELECT COUNT(*) FROM option_bars").fetchone()[0]
        rolling = con.execute(
            "SELECT COUNT(*) FROM option_bars WHERE contract_identity LIKE 'ROLLING:%'"
        ).fetchone()[0]
        legacy = con.execute(
            "SELECT COUNT(*) FROM option_bars WHERE contract_identity IS NULL"
        ).fetchone()[0]
        other = total - rolling - legacy

        print(f"V3 CLEANUP: total_rows={total}")
        print(f"V3 CLEANUP: rolling_identity_rows={rolling}")
        print(f"V3 CLEANUP: null_identity_rows={legacy}")
        print(f"V3 CLEANUP: other_identity_rows={other}")

        if other:
            raise SystemExit("Unexpected non-NULL/non-ROLLING identities found; refusing cleanup.")
        if rolling == 0:
            raise SystemExit("No ROLLING identities found; refusing cleanup.")

        duplicate_keys = con.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, side, strike_key
                FROM option_bars
                GROUP BY timestamp, side, strike_key
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        print(f"V3 CLEANUP: duplicate_logical_keys_before={duplicate_keys}")

        # Every duplicate must be exactly one legacy NULL row plus one rolling row.
        bad = con.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, side, strike_key,
                       COUNT(*) AS n,
                       SUM(contract_identity IS NULL) AS null_n,
                       SUM(contract_identity LIKE 'ROLLING:%') AS rolling_n
                FROM option_bars
                GROUP BY timestamp, side, strike_key
                HAVING n != 2 OR null_n != 1 OR rolling_n != 1
            )
        """).fetchone()[0]
        if bad:
            raise SystemExit(
                f"Found {bad} logical keys that are not exactly NULL+ROLLING pairs; refusing cleanup."
            )

        # Verify all duplicated rows match on every market-data field except identity/expiry.
        mismatch = con.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, side, strike_key,
                       MIN(strike) != MAX(strike) AS bad_strike,
                       MIN(open) != MAX(open) AS bad_open,
                       MIN(high) != MAX(high) AS bad_high,
                       MIN(low) != MAX(low) AS bad_low,
                       MIN(close) != MAX(close) AS bad_close,
                       MIN(volume) != MAX(volume) AS bad_volume,
                       MIN(oi) != MAX(oi) AS bad_oi,
                       MIN(iv) != MAX(iv) AS bad_iv,
                       MIN(spot) != MAX(spot) AS bad_spot
                FROM option_bars
                GROUP BY timestamp, side, strike_key
                HAVING COUNT(*) = 2
                   AND (bad_strike OR bad_open OR bad_high OR bad_low OR bad_close
                        OR bad_volume OR bad_oi OR bad_iv OR bad_spot)
            )
        """).fetchone()[0]
        print(f"V3 CLEANUP: value_mismatch_keys={mismatch}")
        if mismatch:
            raise SystemExit("Duplicate rows have different market values; refusing cleanup.")

        if a.dry_run:
            print("V3 CLEANUP: DRY RUN - no rows changed")
            return

        shutil.copy2(db_path, backup)
        print(f"V3 CLEANUP: backup={backup}")

        con.execute("BEGIN")
        deleted = con.execute(
            "DELETE FROM option_bars WHERE contract_identity IS NULL"
        ).rowcount
        con.commit()

        remaining = con.execute("SELECT COUNT(*) FROM option_bars").fetchone()[0]
        remaining_null = con.execute(
            "SELECT COUNT(*) FROM option_bars WHERE contract_identity IS NULL"
        ).fetchone()[0]
        remaining_dupes = con.execute("""
            SELECT COUNT(*) FROM (
                SELECT timestamp, side, strike_key
                FROM option_bars
                GROUP BY timestamp, side, strike_key
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        print(f"V3 CLEANUP: deleted_legacy_rows={deleted}")
        print(f"V3 CLEANUP: remaining_rows={remaining}")
        print(f"V3 CLEANUP: remaining_null_identity={remaining_null}")
        print(f"V3 CLEANUP: remaining_duplicate_logical_keys={remaining_dupes}")

        if remaining_null or remaining_dupes or remaining != rolling:
            raise SystemExit("Post-cleanup verification failed; restore the backup before continuing.")

        print("V3 CLEANUP: PASS")
        print("V3 CLEANUP: option_bars now contains only the verified V3 rolling-series rows.")

    finally:
        con.close()


if __name__ == "__main__":
    main()
