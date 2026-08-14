from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.ai.base import AIProvider


class ExternalProviderUnavailable(RuntimeError):
    """Raised when the configured external provider cannot return valid analysis."""


class ExternalAnalysisPayload(BaseModel):
    model_config = {"extra": "forbid"}
    summary: str = Field(min_length=1, max_length=2000)
    market_view: str = Field(default="", max_length=2000)
    signal: str
    confidence: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)
    data_quality: str = Field(default="PARTIAL", max_length=50)
    limitations: list[str] = Field(default_factory=list)


class ExternalAIProvider(AIProvider):
    """Bounded OpenAI-compatible JSON client isolated from portfolio business logic."""

    name = "external"

    def __init__(self, *, api_key: str, model: str, base_url: str, timeout_seconds: float, max_retries: int, rate_limit: int) -> None:
        if not api_key or not model or not base_url:
            raise ExternalProviderUnavailable("AI provider is not configured. Set API key, model, and base URL or use mock.")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._rate_limit = rate_limit
        self._requests: deque[float] = deque()
        self._lock = threading.Lock()

    def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        self._check_rate_limit()
        request = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Return only valid JSON. Explain supplied facts without adding prices, news, trade execution instructions, or certainty."},
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
        }
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=httpx.Timeout(self._timeout_seconds, connect=self._timeout_seconds)) as client:
                    response = client.post(f"{self._base_url}/chat/completions", headers={"Authorization": f"Bearer {self._api_key}"}, json=request)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                payload = ExternalAnalysisPayload.model_validate_json(content)
                if payload.signal not in {"BUY", "HOLD", "SELL", "NEUTRAL"}:
                    raise ExternalProviderUnavailable("AI provider returned an invalid signal.")
                result = payload.model_dump()
                result["generated_at"] = datetime.now(timezone.utc)
                return result
            except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError, ValidationError, ExternalProviderUnavailable) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(min(0.25 * (attempt + 1), 1.0))
        raise ExternalProviderUnavailable("AI provider is unavailable or returned an invalid response.") from last_error

    def _check_rate_limit(self) -> None:
        now = time.monotonic()
        with self._lock:
            while self._requests and now - self._requests[0] >= 60:
                self._requests.popleft()
            if len(self._requests) >= self._rate_limit:
                raise ExternalProviderUnavailable("AI provider request limit reached. Try again shortly.")
            self._requests.append(now)
