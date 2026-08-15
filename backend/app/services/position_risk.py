from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PositionRiskConfig:
    risk_per_trade_pct: float = 0.5
    max_capital_pct: float = 60.0
    max_quantity: int = 1000
    max_order_value: float = 100000.0
    min_risk_reward: float = 1.5
    daily_risk_budget: float = 2000.0


@dataclass(frozen=True)
class PositionRiskPlan:
    approved: bool
    reason: str
    entry: float
    stop: float
    target: float | None
    risk_per_share: float
    reward_per_share: float | None
    risk_reward: float | None
    risk_budget: float
    quantity: int
    capital_required: float
    max_loss: float
    remaining_daily_risk: float


def calculate_long_position(
    *,
    entry: float,
    stop: float,
    target: float | None,
    equity: float,
    daily_risk_used: float = 0.0,
    config: PositionRiskConfig | None = None,
) -> PositionRiskPlan:
    """Calculate a long-only position from explicit account and trade risk.

    This is a sizing/decision function only; it never places an order.
    It fails closed whenever required risk information is invalid or unsafe.
    """
    cfg = config or PositionRiskConfig()
    base = dict(
        entry=float(entry), stop=float(stop), target=None if target is None else float(target),
        risk_per_share=0.0, reward_per_share=None, risk_reward=None,
        risk_budget=0.0, quantity=0, capital_required=0.0, max_loss=0.0,
        remaining_daily_risk=max(0.0, cfg.daily_risk_budget - float(daily_risk_used)),
    )
    if entry <= 0 or stop <= 0 or equity <= 0:
        return PositionRiskPlan(False, "INVALID_RISK_INPUT", **base)
    if stop >= entry:
        return PositionRiskPlan(False, "INVALID_LONG_STOP", **base)
    if cfg.risk_per_trade_pct <= 0 or cfg.max_capital_pct <= 0 or cfg.max_quantity <= 0:
        return PositionRiskPlan(False, "INVALID_RISK_CONFIG", **base)

    risk_per_share = entry - stop
    risk_budget = equity * cfg.risk_per_trade_pct / 100.0
    remaining_daily_risk = max(0.0, cfg.daily_risk_budget - float(daily_risk_used))
    usable_risk = min(risk_budget, remaining_daily_risk)
    reward_per_share = None if target is None else target - entry
    risk_reward = None if reward_per_share is None else reward_per_share / risk_per_share
    base.update(risk_per_share=risk_per_share, risk_budget=usable_risk,
                reward_per_share=reward_per_share, risk_reward=risk_reward,
                remaining_daily_risk=remaining_daily_risk)

    if remaining_daily_risk <= 0:
        return PositionRiskPlan(False, "DAILY_RISK_LIMIT", **base)
    if target is not None and target <= entry:
        return PositionRiskPlan(False, "INVALID_LONG_TARGET", **base)
    if risk_reward is not None and risk_reward < cfg.min_risk_reward:
        return PositionRiskPlan(False, "RISK_REWARD_TOO_LOW", **base)

    qty_by_risk = math.floor(usable_risk / risk_per_share)
    qty_by_capital = math.floor((equity * cfg.max_capital_pct / 100.0) / entry)
    qty_by_order_value = math.floor(cfg.max_order_value / entry)
    quantity = max(0, min(qty_by_risk, qty_by_capital, qty_by_order_value, cfg.max_quantity))
    capital_required = quantity * entry
    max_loss = quantity * risk_per_share
    base.update(quantity=quantity, capital_required=capital_required, max_loss=max_loss)

    if quantity < 1:
        return PositionRiskPlan(False, "RISK_BUDGET_TOO_SMALL", **base)
    return PositionRiskPlan(True, "RISK_APPROVED", **base)
