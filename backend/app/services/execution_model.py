from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionModelConfig:
    """Research-only execution assumptions used to turn signals into executable fills."""

    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    spread_bps: float = 0.0
    market_impact_bps: float = 0.0
    impact_reference_value: float = 100_000.0
    max_volume_participation: float = 0.0

    def __post_init__(self) -> None:
        if self.brokerage_rate < 0 or self.slippage_rate < 0:
            raise ValueError("execution rates cannot be negative")
        if self.spread_bps < 0 or self.market_impact_bps < 0:
            raise ValueError("spread and market impact cannot be negative")
        if self.impact_reference_value <= 0:
            raise ValueError("impact_reference_value must be positive")
        if self.max_volume_participation < 0 or self.max_volume_participation > 1:
            raise ValueError("max_volume_participation must be between 0 and 1")

    def _impact_rate(self, notional: float) -> float:
        if self.market_impact_bps == 0:
            return 0.0
        scale = max(notional / self.impact_reference_value, 0.0) ** 0.5
        return self.market_impact_bps / 10_000 * scale

    def fill_price(self, reference_price: float, side: str, notional: float) -> float:
        if reference_price <= 0:
            raise ValueError("reference_price must be positive")
        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        half_spread = self.spread_bps / 20_000
        friction = self.slippage_rate + half_spread + self._impact_rate(notional)
        return reference_price * (1 + friction if side == "BUY" else 1 - friction)

    def commission(self, notional: float) -> float:
        return abs(notional) * self.brokerage_rate

    def max_fill_quantity(self, requested_quantity: int, bar_volume: float | None) -> int:
        if requested_quantity <= 0:
            return 0
        if self.max_volume_participation == 0 or bar_volume is None:
            return requested_quantity
        if bar_volume < 0:
            raise ValueError("bar_volume cannot be negative")
        return min(requested_quantity, int(bar_volume * self.max_volume_participation))

    def fingerprint_dict(self) -> dict:
        return {
            "brokerage_rate": self.brokerage_rate,
            "slippage_rate": self.slippage_rate,
            "spread_bps": self.spread_bps,
            "market_impact_bps": self.market_impact_bps,
            "impact_reference_value": self.impact_reference_value,
            "max_volume_participation": self.max_volume_participation,
        }
