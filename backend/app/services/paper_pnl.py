from __future__ import annotations

from typing import Any


def calculate_trade_net_pnl(entry_price: float, exit_price: float, quantity: int, entry_costs: dict[str, Any], exit_costs: dict[str, Any]) -> dict[str, float]:
    gross = (float(exit_price) - float(entry_price)) * int(quantity)
    total_costs = float(entry_costs.get("total", 0.0)) + float(exit_costs.get("total", 0.0))
    net = gross - total_costs
    return {"gross_pnl": round(gross, 2), "total_charges": round(total_costs, 2), "net_pnl": round(net, 2)}


def calculate_mark_to_market(entry_price: float, market_price: float, quantity: int, entry_costs: dict[str, Any], projected_exit_costs: dict[str, Any]) -> dict[str, float]:
    gross = (float(market_price) - float(entry_price)) * int(quantity)
    entry_total = float(entry_costs.get("total", 0.0))
    exit_total = float(projected_exit_costs.get("total", 0.0))
    net = gross - entry_total - exit_total
    return {"unrealized_gross_pnl": round(gross, 2), "projected_exit_charges": round(exit_total, 2), "unrealized_net_pnl": round(net, 2)}
