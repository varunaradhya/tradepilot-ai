from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.paper_trading import PaperRiskConfig, PaperTradingEngine


@dataclass(frozen=True)
class PaperOrchestratorConfig:
    initial_capital: float = 100_000.0
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.01
    max_trades_per_session: int = 3
    trade_direction: str = "LONG_ONLY"
    allocation_pct: float = 0.02
    lot_size: int = 1
    trailing_stop_pct: float = 0.015
    trailing_activation_pct: float = 0.01
    max_holding_bars: int = 24


class PaperTradingOrchestrator:
    """Simulation-only signal-to-position coordinator. It never talks to a broker."""

    def __init__(self, config: PaperOrchestratorConfig = PaperOrchestratorConfig()):
        if config.max_trades_per_session < 1:
            raise ValueError("max_trades_per_session must be positive")
        self.config = config
        self.engine = PaperTradingEngine(PaperRiskConfig(
            initial_capital=config.initial_capital, risk_per_trade=config.risk_per_trade,
            max_daily_loss=config.max_daily_loss, trade_direction="LONG_ONLY",
            allocation_pct=config.allocation_pct, lot_size=config.lot_size,
            trailing_stop_pct=config.trailing_stop_pct, trailing_activation_pct=config.trailing_activation_pct,
            max_holding_bars=config.max_holding_bars,
        ))
        self.session_trades = 0
        self.last_signal: dict[str, Any] | None = None
        self._session: str | None = None

    def _sync_session(self, session: str) -> None:
        if self._session != session:
            self.session_trades = 0
            self._session = session
        self.engine.new_session(session)

    def on_bar(self, session: str, high: float, low: float, close: float) -> dict[str, Any]:
        self._sync_session(session)
        before = self.engine.position
        trade = self.engine.on_bar(session, high, low, close)
        snapshot = self.engine.snapshot()
        snapshot["last_event"] = "EXIT" if trade else ("POSITION_OPEN" if before is not None and self.engine.position is not None else "MARK")
        if trade: snapshot["trade"] = trade
        return snapshot

    def on_tick(self, session: str, price: float) -> dict[str, Any]:
        self._sync_session(session)
        before = self.engine.position
        trade = self.engine.on_tick(session, float(price))
        snapshot = self.engine.snapshot()
        snapshot["last_event"] = "EXIT" if trade else ("POSITION_OPEN" if before is not None else "MARK")
        if trade: snapshot["trade"] = trade
        return snapshot

    def on_signal(self, session: str, signal: dict[str, Any]) -> dict[str, Any]:
        self._sync_session(session)
        self.last_signal = dict(signal)
        if signal.get("action") != "BUY": return {"accepted": False, "reason": "SIGNAL_NOT_BUY", **self.engine.snapshot()}
        if self.config.trade_direction != "LONG_ONLY": return {"accepted": False, "reason": "UNSUPPORTED_DIRECTION", **self.engine.snapshot()}
        if self.session_trades >= self.config.max_trades_per_session: return {"accepted": False, "reason": "MAX_TRADES_REACHED", **self.engine.snapshot()}
        if not self.engine.can_trade(): return {"accepted": False, "reason": "RISK_GATE_BLOCKED", **self.engine.snapshot()}
        entry = float(signal["entry"]); stop = float(signal["stop"]); target = float(signal["target"])
        if not (stop < entry < target): return {"accepted": False, "reason": "INVALID_RISK_LEVELS", **self.engine.snapshot()}
        lot_size = int(signal.get("lot_size") or self.config.lot_size)
        accepted = self.engine.enter(entry, stop, target, "LONG", lot_size=lot_size, symbol=signal.get("symbol"))
        if not accepted: return {"accepted": False, "reason": "ORDER_REJECTED_OR_ALLOCATION_TOO_SMALL", **self.engine.snapshot()}
        self.session_trades += 1
        return {"accepted": True, "reason": "PAPER_ORDER_OPENED", **self.engine.snapshot()}

    def close_session(self, session: str, close: float) -> dict[str, Any]:
        self._sync_session(session)
        trade = self.engine.close(float(close), "SESSION_CLOSE")
        return {"mode": "SIMULATION_ONLY", "trade": trade, **self.engine.snapshot()}

    def trades(self) -> list[dict[str, Any]]: return [dict(trade) for trade in self.engine.trades]

    def summary(self) -> dict[str, Any]:
        snapshot = self.engine.snapshot()
        snapshot["session_trades"] = self.session_trades
        snapshot["last_signal"] = self.last_signal
        return snapshot
