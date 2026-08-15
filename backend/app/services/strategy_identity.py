from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def strategy_fingerprint(strategy: Any, *, strategy_version: str, execution: dict[str, Any] | None = None) -> str:
    payload = {
        "strategy_version": strategy_version,
        "strategy": _plain(strategy),
        "execution": _plain(execution or {}),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def strategy_identity(strategy: Any, *, strategy_version: str, execution: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "strategy_version": strategy_version,
        "fingerprint": strategy_fingerprint(strategy, strategy_version=strategy_version, execution=execution),
    }
