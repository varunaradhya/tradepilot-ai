from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FNOCostConfig:
    """Conservative NSE equity-options cost model for paper trading.

    Defaults mirror the currently published Dhan/market rates where available.
    Broker/regulatory charges can change, so the model is intentionally
    configurable and should be refreshed from the connected broker before live
    execution.
    """

    brokerage_per_order: float = 20.0
    exchange_transaction_rate: float = 0.0003503  # 0.03503% of option premium turnover
    stt_sell_rate: float = 0.001  # 0.10% of premium on sell side
    sebi_turnover_rate: float = 0.000001  # 0.0001%
    stamp_buy_rate: float = 0.00003  # 0.003%
    ipft_rate: float = 0.000000005  # Rs 0.50/crore, configurable
    gst_rate: float = 0.18


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return value


def estimate_fno_option_costs(
    entry_price: float,
    exit_price: float,
    quantity: int,
    config: FNOCostConfig = FNOCostConfig(),
) -> dict[str, float]:
    """Estimate round-trip costs for a long NSE equity option position.

    Turnover is based on option premium, not underlying notional. Brokerage is
    charged once on each executed leg. STT is applied only on the sell leg.
    GST is applied to brokerage + exchange + SEBI + IPFT charges.
    """
    entry_price = _positive(entry_price, "entry_price")
    exit_price = _positive(exit_price, "exit_price")
    if int(quantity) != quantity or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    quantity = int(quantity)

    buy_turnover = entry_price * quantity
    sell_turnover = exit_price * quantity
    turnover = buy_turnover + sell_turnover

    brokerage = config.brokerage_per_order * 2.0
    exchange = turnover * config.exchange_transaction_rate
    sebi = turnover * config.sebi_turnover_rate
    ipft = turnover * config.ipft_rate
    stt = sell_turnover * config.stt_sell_rate
    stamp = buy_turnover * config.stamp_buy_rate
    gst = (brokerage + exchange + sebi + ipft) * config.gst_rate
    total = brokerage + exchange + sebi + ipft + stt + stamp + gst

    return {
        "brokerage": round(brokerage, 2),
        "exchange_transaction": round(exchange, 2),
        "sebi_turnover": round(sebi, 2),
        "ipft": round(ipft, 2),
        "stt": round(stt, 2),
        "stamp_duty": round(stamp, 2),
        "gst": round(gst, 2),
        "total": round(total, 2),
    }


def estimate_net_pnl(
    entry_price: float,
    exit_price: float,
    quantity: int,
    config: FNOCostConfig = FNOCostConfig(),
) -> tuple[float, dict[str, float]]:
    gross = (float(exit_price) - float(entry_price)) * int(quantity)
    costs = estimate_fno_option_costs(entry_price, exit_price, quantity, config)
    return round(gross - costs["total"], 2), costs
