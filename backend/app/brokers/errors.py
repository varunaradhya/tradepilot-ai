from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BrokerErrorCode(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION = "VALIDATION"
    BROKER_ERROR = "BROKER_ERROR"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class NormalizedBrokerError(Exception):
    code: BrokerErrorCode
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


def normalize_broker_error(exc: Exception) -> NormalizedBrokerError:
    """Convert provider exceptions to a safe, provider-neutral error."""
    raw = str(exc).lower()
    if any(token in raw for token in ("401", "unauthorized", "invalid token", "access token")):
        return NormalizedBrokerError(BrokerErrorCode.AUTHENTICATION, "Broker authentication failed.", False)
    if any(token in raw for token in ("429", "rate limit", "too many requests")):
        return NormalizedBrokerError(BrokerErrorCode.RATE_LIMIT, "Broker rate limit reached.", True)
    if any(token in raw for token in ("timeout", "timed out", "temporarily unavailable")):
        return NormalizedBrokerError(BrokerErrorCode.TIMEOUT, "Broker request timed out.", True)
    if any(token in raw for token in ("404", "not found")):
        return NormalizedBrokerError(BrokerErrorCode.NOT_FOUND, "Broker resource was not found.", False)
    if any(token in raw for token in ("invalid", "validation", "bad request")):
        return NormalizedBrokerError(BrokerErrorCode.VALIDATION, "Broker request validation failed.", False)
    return NormalizedBrokerError(BrokerErrorCode.BROKER_ERROR, "Broker request failed.", False)
