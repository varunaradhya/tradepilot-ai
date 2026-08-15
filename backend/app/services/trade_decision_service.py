from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
from typing import Sequence

from app.services.broker_adapters import CanonicalOrder
from app.services.execution_guard import ExecutionContext, authorize_order
from app.services.intraday_signal_engine import IntradaySignal, generate_long_intraday_signal
from app.services.paper_risk_guard import PaperRiskConfig, PaperRiskState, evaluate_paper_entry
from app.services.position_risk import PositionRiskConfig, calculate_long_position


@dataclass(frozen=True)
class TradeDecision:
    signal_id: str
    symbol: str
    action: str
    status: str
    reason: str
    confidence: float
    entry: float | None
    stop: float | None
    target: float | None
    risk_reward: float | None
    quantity: int
    capital_required: float
    max_loss: float
    broker: str
    mode: str = "PAPER"

    def as_dict(self) -> dict:
        return asdict(self)


def _signal_id(symbol: str, session: str, signal: IntradaySignal) -> str:
    raw = "|".join([
        symbol.strip().upper(), session.strip(), signal.action,
        str(signal.entry), str(signal.stop), str(signal.target), str(signal.confidence),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def build_paper_trade_decision(
    *,
    symbol: str,
    session: str,
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    volumes: Sequence[float],
    equity: float,
    broker: str = "DHAN",
    in_market_session: bool = True,
    market_data_healthy: bool = True,
    strategy_ready: bool = True,
    risk_approved: bool = True,
    daily_risk_used: float = 0.0,
    paper_state: PaperRiskState | None = None,
    paper_config: PaperRiskConfig | None = None,
    position_config: PositionRiskConfig | None = None,
    opening_high: float | None = None,
    min_confidence: float = 65.0,
) -> TradeDecision:
    """Create one auditable BUY/NEUTRAL paper-trade decision.

    This composes signal, position risk, paper-session risk and execution
    authorization. It never sends a broker order and never enables LIVE mode.
    When an opening-high reference is supplied, this composer treats a break
    above it as a required intraday trigger rather than allowing weaker trend
    evidence to authorize a paper trade.
    """
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol or not session.strip():
        raise ValueError("SYMBOL_AND_SESSION_REQUIRED")

    signal = generate_long_intraday_signal(
        closes, highs, lows, volumes,
        opening_high=opening_high,
        min_confidence=min_confidence,
    )
    signal_id = _signal_id(normalized_symbol, session, signal)
    if signal.action != "BUY" or (opening_high is not None and float(closes[-1]) <= float(opening_high)):
        return TradeDecision(signal_id, normalized_symbol, "NEUTRAL", "NO_TRADE", "SIGNAL_NOT_BUY", signal.confidence, None, None, None, None, 0, 0.0, 0.0, broker.upper())

    if not strategy_ready:
        return TradeDecision(signal_id, normalized_symbol, "BUY", "BLOCKED", "STRATEGY_NOT_READY", signal.confidence, signal.entry, signal.stop, signal.target, signal.risk_reward, 0, 0.0, 0.0, broker.upper())

    state = paper_state or PaperRiskState(trading_date=date.today())
    pconfig = paper_config or PaperRiskConfig()
    paper_gate = evaluate_paper_entry(
        side="BUY", symbol=normalized_symbol, signal_id=signal_id,
        in_market_session=in_market_session, state=state, config=pconfig,
    )
    if not paper_gate.allowed:
        return TradeDecision(signal_id, normalized_symbol, "BUY", "BLOCKED", paper_gate.reason, signal.confidence, signal.entry, signal.stop, signal.target, signal.risk_reward, 0, 0.0, 0.0, broker.upper())

    plan = calculate_long_position(
        entry=float(signal.entry), stop=float(signal.stop), target=float(signal.target),
        equity=equity, daily_risk_used=daily_risk_used, config=position_config,
    )
    if not plan.approved:
        return TradeDecision(signal_id, normalized_symbol, "BUY", "BLOCKED", plan.reason, signal.confidence, signal.entry, signal.stop, signal.target, plan.risk_reward, plan.quantity, plan.capital_required, plan.max_loss, broker.upper())

    risk_reward = round(plan.risk_reward, 2) if plan.risk_reward is not None else None
    position_config = position_config or PositionRiskConfig()
    execution = authorize_order(
        ExecutionContext(
            broker=broker, mode="PAPER", market_data_healthy=market_data_healthy,
            strategy_ready=True, risk_approved=risk_approved, long_only=True,
            max_quantity=position_config.max_quantity,
            max_order_value=position_config.max_order_value,
        ),
        CanonicalOrder(
            symbol=normalized_symbol, side="BUY", quantity=plan.quantity,
            order_type="LIMIT", product="INTRADAY", price=plan.entry,
            stop_loss=plan.stop, target=plan.target,
        ),
    )
    if not execution.allowed:
        return TradeDecision(signal_id, normalized_symbol, "BUY", "BLOCKED", execution.reason, signal.confidence, plan.entry, plan.stop, plan.target, risk_reward, plan.quantity, plan.capital_required, plan.max_loss, execution.normalized_broker)

    return TradeDecision(signal_id, normalized_symbol, "BUY", "PAPER_READY", "PAPER_ORDER_AUTHORIZED", signal.confidence, plan.entry, plan.stop, plan.target, risk_reward, plan.quantity, plan.capital_required, plan.max_loss, execution.normalized_broker)
