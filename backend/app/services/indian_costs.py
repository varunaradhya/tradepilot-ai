from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndianEquityCostModel:
    """Conservative, configurable estimate for NSE equity delivery/intraday research.

    Rates are intentionally configurable; they are not a broker contract or tax advice.
    """

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
        gst_base = brokerage + exchange
        gst = gst_base * self.gst_rate
        slippage = turnover * self.slippage_rate
        total = brokerage + exchange + sebi + stt + gst + slippage
        return {
            "brokerage": round(brokerage, 2),
            "exchange_charges": round(exchange, 2),
            "sebi_charges": round(sebi, 2),
            "stt": round(stt, 2),
            "gst": round(gst, 2),
            "slippage": round(slippage, 2),
            "total": round(total, 2),
        }
