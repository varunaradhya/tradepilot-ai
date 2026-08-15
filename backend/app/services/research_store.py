from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.services.historical_data_service import MarketBar, normalize_bars, validate_dataset


DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "research"


class ResearchStore:
    """Small dependency-free store for reproducible historical research datasets."""

    def __init__(self, root: Path | None = None):
        self.root = root or DEFAULT_ROOT

    def _path(self, dataset: str) -> Path:
        safe = "".join(ch for ch in dataset if ch.isalnum() or ch in "-_./")
        if not safe or safe.startswith("/") or ".." in Path(safe).parts:
            raise ValueError("Invalid dataset name")
        path = (self.root / f"{safe}.jsonl").resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid dataset path")
        return path

    def save(self, dataset: str, bars: list[MarketBar]) -> dict:
        normalized = normalize_bars([bar.as_row() for bar in bars])
        diagnostics = validate_dataset(normalized)
        if not diagnostics["valid"]:
            raise ValueError("Cannot persist an invalid research dataset")

        path = self._path(dataset)
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
            temp_path = Path(handle.name)
            for bar in normalized:
                handle.write(json.dumps(bar.as_row(), default=str, separators=(",", ":")) + "\n")
        os.replace(temp_path, path)
        return {"dataset": dataset, **diagnostics, "path": str(path)}

    def load(self, dataset: str) -> list[MarketBar]:
        path = self._path(dataset)
        if not path.exists():
            return []
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        return normalize_bars(rows)


research_store = ResearchStore()
