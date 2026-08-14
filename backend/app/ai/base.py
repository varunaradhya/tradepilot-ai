from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Produces advisory analysis from a sanitized, structured context."""

    name: str

    @abstractmethod
    def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return a structured analysis without performing trades."""
