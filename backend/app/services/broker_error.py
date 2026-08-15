class BrokerIntegrationError(Exception):
    """Normalized broker integration error that never exposes credentials."""

    def __init__(self, broker: str, code: str, message: str):
        self.broker = broker
        self.code = code
        super().__init__(message)


def normalize_broker_error(broker: str, error: Exception) -> BrokerIntegrationError:
    text = str(error).lower()
    if "timeout" in text or "timed out" in text:
        code = "TIMEOUT"
    elif "401" in text or "unauthor" in text or "token" in text:
        code = "AUTHENTICATION"
    elif "429" in text or "rate" in text:
        code = "RATE_LIMIT"
    elif "404" in text or "not found" in text:
        code = "NOT_FOUND"
    else:
        code = "BROKER_ERROR"
    return BrokerIntegrationError(broker.strip().upper(), code, "Broker request failed safely")
