from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndianEquityCostModel:
    """Conservative, configurable estimate for NSE equity delivery/intraday research."""

    brokerage_rate: float = 0.0003
    slippage_rate: float = 0.0005
    stt_rate: float = 0.00025
    exchange_rate: float = 0.0000325
    sebi_rate: float = 0.000001
    gst_rate: float = 0.18

    def estimate_round_trip(self, buy_value: float, sell_value: float) -> dict:
        turnover = max(0.0, buy_value) + max(0.0, sell_value)
        brokerage = turnover * self.brokerage_rate
        exchange = turnover * self.exchange_rate
        sebi = turnover * self.sebi_rate
        stt = max(0.0, sell_value) * self.stt_rate
        gst_base = brokerage + exchange + sebi
        gst = gst_base * self.gst_rate
        slippage = turnover * self.slippage_rate
        total = brokerage + exchange + sebi + stt + gst + slippage
        return {
            "brokerage": round(brokerage, 2),
            "exchange_charges": round(exchange, 2),
            "sebi_charges": round(sebi, 2),
            "stt": round(stt, 2),
            "stamp_duty": 0.0,
            "ipft": 0.0,
            "gst": round(gst, 2),
            "slippage": round(slippage, 2),
            "total": round(total, 2),
        }


@dataclass(frozen=True)
class IndianFnoOptionCostModel:
    """Configurable NSE/Dhan-style option cost model.

    The model intentionally keeps exchange/IPFT rates configurable because those
    levies can change. Defaults reflect the current 2026 environment: Dhan charges
    ₹20 per executed F&O options order, NSE option STT is 0.15% on sale from
    2026-04-01, SEBI turnover fee is 0.0001%, and equity-option stamp duty is
    0.003% on the buyer. GST is 18% on brokerage + exchange + SEBI + IPFT/other
    taxable charges.
    """

    brokerage_per_order: float = 20.0
    exchange_rate: float = 0.0003503
    sebi_rate: float = 0.000001
    stt_sell_rate: float = 0.0015
    stamp_buy_rate: float = 0.00003
    ipft_rate: float = 0.000004999
    gst_rate: float = 0.18

    def estimate_order(self, trade_value: float, *, side: str, include_stt: bool = True) -> dict:
        if trade_value < 0:
            raise ValueError("trade_value cannot be negative")
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        brokerage = min(self.brokerage_per_order, trade_value)
        exchange = trade_value * self.exchange_rate
        sebi = trade_value * self.sebi_rate
        stt = trade_value * self.stt_sell_rate if side == "SELL" and include_stt else 0.0
        stamp_duty = trade_value * self.stamp_buy_rate if side == "BUY" else 0.0
        ipft = trade_value * self.ipft_rate
        gst = (brokerage + exchange + sebi + ipft) * self.gst_rate
        total = brokerage + exchange + sebi + stt + stamp_duty + ipft + gst
        return {
            "brokerage": round(brokerage, 2),
            "exchange_charges": round(exchange, 2),
            "sebi_charges": round(sebi, 2),
            "stt": round(stt, 2),
            "stamp_duty": round(stamp_duty, 2),
            "ipft": round(ipft, 2),
            "gst": round(gst, 2),
            "slippage": 0.0,
            "total": round(total, 2),
        }

    def estimate_round_trip(self, buy_value: float, sell_value: float) -> dict:
        buy = self.estimate_order(buy_value, side="BUY", include_stt=False)
        sell = self.estimate_order(sell_value, side="SELL", include_stt=True)
        keys = ["brokerage", "exchange_charges", "sebi_charges", "stt", "stamp_duty", "ipft", "gst", "slippage", "total"]
        return {key: round(buy[key] + sell[key], 2) for key in keys}
