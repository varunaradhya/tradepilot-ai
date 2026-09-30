from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndiaEquityIntradayFeeSchedule:
    """Configurable NSE cash-market intraday fee inputs.

    Rates are decimal fractions. This schedule is intentionally explicit and
    versioned by effective date outside the calculator because statutory and
    exchange charges can change over time.
    """

    version: str
    effective_from: str
    brokerage_rate: float
    exchange_and_ipft_rate: float
    sebi_turnover_rate: float
    stt_sell_rate: float
    stamp_buy_rate: float
    gst_rate: float = 0.18

    def validate(self) -> None:
        rates = (
            self.brokerage_rate,
            self.exchange_and_ipft_rate,
            self.sebi_turnover_rate,
            self.stt_sell_rate,
            self.stamp_buy_rate,
            self.gst_rate,
        )
        if any(rate < 0 for rate in rates):
            raise ValueError("fee rates must be non-negative")
        if self.gst_rate > 1:
            raise ValueError("gst_rate must be a decimal fraction")


def calculate_intraday_equity_fees(
    *,
    buy_value: float,
    sell_value: float,
    schedule: IndiaEquityIntradayFeeSchedule,
) -> dict[str, float]:
    """Calculate auditable cash-equity intraday statutory/broker charges.

    The calculator keeps STT and stamp duty outside the GST base. The exact
    broker's brokerage policy must be supplied through the schedule.
    """
    if buy_value < 0 or sell_value < 0:
        raise ValueError("turnover values must be non-negative")
    schedule.validate()

    brokerage = (buy_value + sell_value) * schedule.brokerage_rate
    exchange_and_ipft = (buy_value + sell_value) * schedule.exchange_and_ipft_rate
    sebi = (buy_value + sell_value) * schedule.sebi_turnover_rate
    stt = sell_value * schedule.stt_sell_rate
    stamp = buy_value * schedule.stamp_buy_rate
    gst = (brokerage + exchange_and_ipft + sebi) * schedule.gst_rate
    total = brokerage + exchange_and_ipft + sebi + stt + stamp + gst

    return {
        "brokerage": brokerage,
        "exchange_and_ipft": exchange_and_ipft,
        "sebi_turnover": sebi,
        "stt": stt,
        "stamp_duty": stamp,
        "gst": gst,
        "total": total,
    }


NSE_EQUITY_INTRADAY_2026 = IndiaEquityIntradayFeeSchedule(
    version="NSE_EQUITY_INTRADAY_2026_03",
    effective_from="2026-03-01",
    brokerage_rate=0.0003,
    exchange_and_ipft_rate=0.0000307,
    sebi_turnover_rate=0.000001,
    stt_sell_rate=0.00025,
    stamp_buy_rate=0.00003,
)
