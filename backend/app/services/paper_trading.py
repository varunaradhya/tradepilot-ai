from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any

from app.services.indian_costs import IndianEquityCostModel, IndianFnoOptionCostModel
from app.services.paper_pnl import calculate_mark_to_market, calculate_trade_net_pnl


@dataclass(frozen=True)
class PaperRiskConfig:
    initial_capital: float = 100000.0
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.01
    trade_direction: str = "LONG_ONLY"
    allocation_pct: float = 0.02
    lot_size: int = 1
    trailing_stop_pct: float = 0.015
    trailing_activation_pct: float = 0.01
    max_holding_bars: int = 24
    use_trailing_stop: bool = True
    cost_model: IndianEquityCostModel | IndianFnoOptionCostModel | None = None


class PaperTradingEngine:
    """Deterministic simulation-only ledger. It never sends broker orders."""

    def __init__(self, config: PaperRiskConfig = PaperRiskConfig()):
        if config.trade_direction not in {"LONG_ONLY", "LONG_SHORT"}: raise ValueError("trade_direction must be LONG_ONLY or LONG_SHORT")
        if not 0 < config.allocation_pct <= 1: raise ValueError("allocation_pct must be between 0 and 1")
        if config.lot_size < 1: raise ValueError("lot_size must be positive")
        if config.max_holding_bars < 1: raise ValueError("max_holding_bars must be positive")
        if not 0 <= config.trailing_stop_pct < 1: raise ValueError("trailing_stop_pct must be between 0 and 1")
        if not 0 <= config.trailing_activation_pct < 1: raise ValueError("trailing_activation_pct must be between 0 and 1")
        if not 0 < config.max_daily_loss <= 1: raise ValueError("max_daily_loss must be between 0 and 1")
        self.config = config
        self.cost_model = config.cost_model or IndianEquityCostModel()
        self.cash = config.initial_capital; self.realized_pnl = 0.0; self.day_pnl = 0.0; self.day = None
        self.day_start_equity = config.initial_capital
        self.position: dict[str, Any] | None = None; self.trades: list[dict[str, Any]] = []; self.halted = False

    def new_session(self, session: str):
        if self.day != session:
            if self.position is not None: self.close(self.position["last_price"], "SESSION_CLOSE")
            self.day = session; self.day_pnl = 0.0; self.day_start_equity = self.cash; self.halted = False

    def can_trade(self):
        return not self.halted and self.position is None and self.day_pnl > -(self.day_start_equity * self.config.max_daily_loss)

    def _max_lots_from_allocation(self, price: float, lot_size: int) -> int:
        allocation_cash = self.cash * self.config.allocation_pct; lot_value = price * lot_size
        return floor(allocation_cash / lot_value) if lot_value > 0 else 0

    def enter(self, price: float, stop: float, target: float, direction: str = "LONG", lot_size: int | None = None, symbol: str | None = None):
        if direction != "LONG": return False
        if self.config.trade_direction != "LONG_ONLY" and direction not in {"LONG", "SHORT"}: return False
        if not self.can_trade() or price <= stop or target <= price: return False
        lot_size = lot_size or self.config.lot_size
        if lot_size < 1: return False
        risk_cash = self.day_start_equity * self.config.risk_per_trade; risk_per_unit = price - stop
        risk_qty = floor(risk_cash / risk_per_unit) if risk_per_unit > 0 else 0
        allocation_lots = self._max_lots_from_allocation(price, lot_size); cash_lots = floor(self.cash / (price * lot_size))
        lots = min(floor(risk_qty / lot_size), allocation_lots, cash_lots); qty = lots * lot_size
        if qty <= 0: return False
        buy_value = qty * price; entry_costs = self.cost_model.estimate_order(buy_value, side="BUY", include_stt=False)
        if buy_value + entry_costs["total"] > self.cash: return False
        self.cash -= buy_value + entry_costs["total"]
        self.position = {"symbol": symbol.upper() if symbol else None, "entry": price, "stop": stop, "initial_stop": stop, "target": target,
                         "quantity": qty, "lots": lots, "lot_size": lot_size, "last_price": price, "high_watermark": price,
                         "trailing_stop": None, "bars_held": 0, "entry_costs": entry_costs, "direction": "LONG"}
        return True

    def close(self, price: float, reason: str):
        if self.position is None: return None
        p = self.position; price = float(price); proceeds = p["quantity"] * price
        exit_costs = self.cost_model.estimate_order(proceeds, side="SELL", include_stt=True)
        pnl = calculate_trade_net_pnl(p["entry"], price, p["quantity"], p["entry_costs"], exit_costs)
        self.cash += proceeds - exit_costs["total"]; self.realized_pnl += pnl["net_pnl"]; self.day_pnl += pnl["net_pnl"]
        trade = {"symbol": p.get("symbol"), "entry": p["entry"], "exit": price, "quantity": p["quantity"], "lots": p["lots"], "lot_size": p["lot_size"],
                 "stop": p["initial_stop"], "final_stop": p["stop"], "target": p["target"], "gross_pnl": pnl["gross_pnl"],
                 "brokerage": p["entry_costs"]["brokerage"] + exit_costs["brokerage"], "stt": p["entry_costs"].get("stt", 0.0) + exit_costs.get("stt", 0.0),
                 "exchange_charges": p["entry_costs"]["exchange_charges"] + exit_costs["exchange_charges"], "sebi_charges": p["entry_costs"]["sebi_charges"] + exit_costs["sebi_charges"],
                 "stamp_duty": p["entry_costs"]["stamp_duty"] + exit_costs["stamp_duty"], "ipft": p["entry_costs"]["ipft"] + exit_costs["ipft"],
                 "gst": p["entry_costs"]["gst"] + exit_costs["gst"], "slippage": p["entry_costs"].get("slippage", 0.0) + exit_costs.get("slippage", 0.0),
                 "total_charges": pnl["total_charges"], "net_pnl": pnl["net_pnl"], "pnl": pnl["net_pnl"],
                 "reason": reason, "exit_reason": "STOP_LOSS" if reason == "STOP" else reason, "direction": p["direction"], "bars_held": p["bars_held"]}
        self.trades.append(trade); self.position = None
        if self.day_pnl <= -(self.day_start_equity * self.config.max_daily_loss): self.halted = True
        return trade

    def _check_price(self, price: float):
        p = self.position
        if p is None: return None
        price = float(price); p["last_price"] = price; previous_trailing_stop = p["trailing_stop"]
        p["high_watermark"] = max(p["high_watermark"], price)
        if previous_trailing_stop is not None and price <= previous_trailing_stop: return self.close(previous_trailing_stop, "TRAILING_STOP")
        if price <= p["stop"]: return self.close(p["stop"], "STOP")
        if price >= p["target"]: return self.close(p["target"], "TARGET")
        activation = p["entry"] * (1 + self.config.trailing_activation_pct)
        if self.config.use_trailing_stop and price >= activation:
            candidate = p["high_watermark"] * (1 - self.config.trailing_stop_pct)
            if candidate > p["stop"]: p["stop"] = candidate; p["trailing_stop"] = candidate
        return None

    def on_tick(self, session: str, price: float):
        self.new_session(session)
        if price <= 0: raise ValueError("price must be positive")
        return self._check_price(price)

    def on_bar(self, session: str, high: float, low: float, close: float):
        self.new_session(session)
        if self.position is None: return None
        if low > high: raise ValueError("low cannot exceed high")
        p = self.position; p["bars_held"] += 1; p["last_price"] = close; previous_trailing_stop = p["trailing_stop"]
        p["high_watermark"] = max(p["high_watermark"], high)
        if previous_trailing_stop is not None and low <= previous_trailing_stop: return self.close(previous_trailing_stop, "TRAILING_STOP")
        if low <= p["stop"]: return self.close(p["stop"], "STOP")
        if high >= p["target"]: return self.close(p["target"], "TARGET")
        activation = p["entry"] * (1 + self.config.trailing_activation_pct)
        if self.config.use_trailing_stop and high >= activation:
            candidate = p["high_watermark"] * (1 - self.config.trailing_stop_pct)
            if candidate > p["stop"]: p["stop"] = candidate; p["trailing_stop"] = candidate
        if p["bars_held"] >= self.config.max_holding_bars: return self.close(close, "TIMEOUT")
        return None

    def snapshot(self):
        unrealized_gross = 0.0; unrealized_net = 0.0
        mark_components: dict[str, float] = {"unrealized_gross_pnl": 0.0, "projected_exit_charges": 0.0, "unrealized_net_pnl": 0.0}
        if self.position is not None:
            p = self.position; market_value = p["quantity"] * p["last_price"]
            exit_costs = self.cost_model.estimate_order(market_value, side="SELL", include_stt=True)
            mark_components = calculate_mark_to_market(p["entry"], p["last_price"], p["quantity"], p["entry_costs"], exit_costs)
            unrealized_gross = mark_components["unrealized_gross_pnl"]; unrealized_net = mark_components["unrealized_net_pnl"]
        return {"mode": "SIMULATION_ONLY", "trade_direction": self.config.trade_direction, "cash": round(self.cash, 2), "realized_pnl": round(self.realized_pnl, 2),
                "unrealized_gross_pnl": round(unrealized_gross, 2), "unrealized_net_pnl": round(unrealized_net, 2), "total_pnl": round(self.realized_pnl + unrealized_net, 2),
                "day_pnl": round(self.day_pnl + unrealized_net, 2), "halted": self.halted, "open_position": self.position, "trades": len(self.trades)}
