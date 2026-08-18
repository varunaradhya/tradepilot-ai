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
    qualification_required: bool = True


class PaperTradingOrchestrator:
    """Simulation-only signal-to-position coordinator. It never talks to a broker."""

    def __init__(self, config: PaperOrchestratorConfig = PaperOrchestratorConfig()):
        if config.max_trades_per_session < 1:
            raise ValueError("max_trades_per_session must be positive")
        self.config = config
        self._strategy_ready = not config.qualification_required
        self._strategy_fingerprint: str | None = None
        self.last_signal: dict[str, Any] | None = None
        self._session: str | None = None
        self.session_trades = 0
        self.engine = self._new_engine()

    def _new_engine(self) -> PaperTradingEngine:
        return PaperTradingEngine(PaperRiskConfig(
            initial_capital=self.config.initial_capital,
            risk_per_trade=self.config.risk_per_trade,
            max_daily_loss=self.config.max_daily_loss,
            trade_direction="LONG_ONLY",
            allocation_pct=self.config.allocation_pct,
            lot_size=self.config.lot_size,
            trailing_stop_pct=self.config.trailing_stop_pct,
            trailing_activation_pct=self.config.trailing_activation_pct,
            max_holding_bars=self.config.max_holding_bars,
        ))

    def reset(self) -> None:
        """Reset simulation state while retaining the server-granted authorization."""
        self.engine = self._new_engine()
        self.session_trades = 0
        self.last_signal = None
        self._session = None

    def authorize_strategy(self, *, fingerprint: str) -> None:
        if not fingerprint or len(fingerprint) < 8:
            raise ValueError("A valid strategy fingerprint is required")
        self._strategy_ready = True
        self._strategy_fingerprint = fingerprint

    def revoke_strategy(self) -> None:
        self._strategy_ready = False
        self._strategy_fingerprint = None

    def export_state(self) -> dict[str, Any]:
        return {
            "session_trades": self.session_trades,
            "last_signal": self.last_signal,
            "session": self._session,
            "strategy_ready": self._strategy_ready,
            "strategy_fingerprint": self._strategy_fingerprint,
            "engine": {
                "cash": self.engine.cash,
                "realized_pnl": self.engine.realized_pnl,
                "day_pnl": self.engine.day_pnl,
                "day": self.engine.day,
                "day_start_equity": self.engine.day_start_equity,
                "halted": self.engine.halted,
                "position": self.engine.position,
                "trades": self.engine.trades,
            },
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        engine_state = state.get("engine") or {}
        for name in ("cash", "realized_pnl", "day_pnl", "day_start_equity"):
            value = engine_state.get(name)
            if value is not None:
                setattr(self.engine, name, float(value))
        self.engine.day = engine_state.get("day")
        self.engine.halted = bool(engine_state.get("halted", False))
        self.engine.position = engine_state.get("position")
        self.engine.trades = list(engine_state.get("trades") or [])
        self.session_trades = int(state.get("session_trades", 0))
        self.last_signal = state.get("last_signal")
        self._session = state.get("session")
        self._strategy_ready = bool(state.get("strategy_ready", False))
        self._strategy_fingerprint = state.get("strategy_fingerprint")

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
        if not self._strategy_ready: return {"accepted": False, "reason": "STRATEGY_NOT_QUALIFIED", **self.engine.snapshot()}
        if self.config.trade_direction != "LONG_ONLY": return {"accepted": False, "reason": "UNSUPPORTED_DIRECTION", **self.engine.snapshot()}
        if self.session_trades >= self.config.max_trades_per_session: return {"accepted": False, "reason": "MAX_TRADES_REACHED", **self.engine.snapshot()}
        if not self.engine.can_trade(): return {"accepted": False, "reason": "RISK_GATE_BLOCKED", **self.engine.snapshot()}
        entry = float(signal["entry"]); stop = float(signal["stop"]); target = float(signal["target"])
        if not (stop < entry < target): return {"accepted": False, "reason": "INVALID_RISK_LEVELS", **self.engine.snapshot()}
        lot_size = int(signal.get("lot_size") or self.config.lot_size)
        accepted = self.engine.enter(entry, stop, target, "LONG", lot_size=lot_size, symbol=signal.get("symbol"))
        if not accepted: return {"accepted": False, "reason": "ORDER_REJECTED_OR_ALLOCATION_TOO_SMALL", **self.engine.snapshot()}
        self.session_trades += 1
        return {"accepted": True, "reason": "PAPER_ORDER_OPENED", "strategy_fingerprint": self._strategy_fingerprint, **self.engine.snapshot()}

    def close_session(self, session: str, close: float) -> dict[str, Any]:
        self._sync_session(session)
        trade = self.engine.close(float(close), "SESSION_CLOSE")
        return {"mode": "SIMULATION_ONLY", "trade": trade, **self.engine.snapshot()}

    def trades(self) -> list[dict[str, Any]]: return [dict(trade) for trade in self.engine.trades]

    def summary(self) -> dict[str, Any]:
        snapshot = self.engine.snapshot()
        snapshot["session_trades"] = self.session_trades
        snapshot["last_signal"] = self.last_signal
        snapshot["strategy_ready"] = self._strategy_ready
        snapshot["strategy_fingerprint"] = self._strategy_fingerprint
        return snapshot
