from app.services.instrument_master_service import InstrumentMasterError, instrument_master


class IndianSymbolError(ValueError):
    """Raised when a symbol is not available in the authoritative NSE universe."""


def canonical_indian_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized.endswith(".NS"):
        normalized = normalized[:-3]
    if normalized.endswith(".BO"):
        raise IndianSymbolError("TradePilot currently supports NSE cash equities only. Select an NSE stock from the suggestions.")
    if not normalized:
        raise IndianSymbolError("Select an NSE stock from the suggestions.")

    try:
        items = instrument_master.search(normalized, limit=100)
    except InstrumentMasterError as exc:
        raise IndianSymbolError(
            "The Indian stock universe is temporarily unavailable. Please try again shortly."
        ) from exc

    exact = next((item for item in items if item.symbol.upper() == normalized), None)
    if exact is None:
        raise IndianSymbolError(
            f"{normalized} is not an active NSE equity instrument. Select a stock from the suggestions."
        )
    return exact.symbol.upper()
