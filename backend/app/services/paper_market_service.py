from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.intraday_strategy import IntradayConfig, generate_intraday_signal
from app.services.paper_trading_orchestrator import PaperTradingOrchestrator


@dataclass
class PaperMarketState:
    opens: list[float] = field(default_factory=list)
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)
    closes: list[float] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)

    def append(self, open_price: float, high: float, low: float, close: float, volume: float) -> None:
        if not (low <= open_price <= high and low <= close <= high):
            raise ValueError("OHLC prices must be inside the candle range")
        if volume < 0:
            raise ValueError("volume cannot be negative")
        self.opens.append(float(open_price))
        self.highs.append(float(high))
        self.lows.append(float(low))
        self.closes.append(float(close))
        self.volumes.append(float(volume))


class PaperMarketCoordinator:
    """Feeds normalized market bars into the long-only strategy and paper engine."""

    def __init__(self, orchestrator: PaperTradingOrchestrator | None = None, strategy: IntradayConfig | None = None):
        self.orchestrator = orchestrator or PaperTradingOrchestrator()
        self.strategy = strategy or IntradayConfig(trade_direction="LONG_ONLY")
        self._states: dict[tuple[str, str], PaperMarketState] = {}

    def on_bar(
        self,
        session: str,
        symbol: str,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        opening_high: float | None = None,
        opening_low: float | None = None,
    ) -> dict[str, Any]:
        if not session.strip() or not symbol.strip():
            raise ValueError("session and symbol are required")
        key = (session, symbol.upper())
        state = self._states.setdefault(key, PaperMarketState())
        state.append(open_price, high, low, close, volume)

        had_position = self.orchestrator.summary().get("open_position") is not None
        signal = generate_intraday_signal(
            state.opens,
            state.highs,
            state.lows,
            state.closes,
            state.volumes,
            opening_high=opening_high,
            opening_low=opening_low,
            config=self.strategy,
        )

        routed: dict[str, Any] | None = None
        if not had_position and signal.get("action") == "BUY":
            routed = self.orchestrator.on_signal(
                session,
                {**signal, "symbol": symbol.upper()},
            )
        elif had_position:
            routed = self.orchestrator.on_bar(session, high, low, close)

        return {
            "mode": "SIMULATION_ONLY",
            "symbol": symbol.upper(),
            "bars": len(state.closes),
            "signal": signal,
            "execution": routed,
            "paper": self.orchestrator.summary(),
        }

    def close_session(self, session: str, symbol: str, close: float) -> dict[str, Any]:
        return self.orchestrator.close_session(session, close)

    def reset(self) -> None:
        """Clear market history and reset the simulation without losing authorization."""
        self._states.clear()
        self.orchestrator.reset()
