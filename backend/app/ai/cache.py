from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from app.core.config import TRADEPILOT_CACHE_BACKEND

_cache: dict[tuple[int, str, str | None, str], tuple[datetime, dict[str, Any]]] = {}
_lock = Lock()


def backend_name() -> str:
    """Return the active cache backend; Redis can be added without changing callers."""
    return "memory" if TRADEPILOT_CACHE_BACKEND != "redis" else "redis_unconfigured"


def get(user_id: int, analysis_type: str, symbol: str | None, ttl_seconds: int) -> dict[str, Any] | None:
    key = (user_id, analysis_type, symbol, "v1")
    with _lock:
        item = _cache.get(key)
        if not item or item[0] < datetime.now(timezone.utc):
            _cache.pop(key, None)
            return None
        return item[1].copy()


def set(user_id: int, analysis_type: str, symbol: str | None, ttl_seconds: int, result: dict[str, Any]) -> None:
    key = (user_id, analysis_type, symbol, "v1")
    with _lock:
        _cache[key] = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds), result.copy())


def clear() -> None:
    with _lock:
        _cache.clear()
