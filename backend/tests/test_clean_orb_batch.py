from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_clean_orb_batch import discover_symbols


def test_discover_symbols_is_sorted_and_symbol_only(tmp_path: Path) -> None:
    clean = tmp_path / "dhan_equity_clean"
    clean.mkdir()
    (clean / "TCS.jsonl").write_text("{}\n", encoding="utf-8")
    (clean / "INFY.jsonl").write_text("{}\n", encoding="utf-8")
    (clean / "README.txt").write_text("ignore", encoding="utf-8")

    assert discover_symbols(tmp_path) == ["INFY", "TCS"]
