from __future__ import annotations

import pytest

from app.services.india_equity_fee_service import (
    IndiaEquityIntradayFeeSchedule,
    NSE_EQUITY_INTRADAY_2026,
    calculate_intraday_equity_fees,
)


def test_intraday_fee_model_breaks_out_each_charge() -> None:
    fees = calculate_intraday_equity_fees(
        buy_value=100_000.0,
        sell_value=101_000.0,
        schedule=NSE_EQUITY_INTRADAY_2026,
    )

    assert fees["brokerage"] == pytest.approx(60.3)
    assert fees["exchange_and_ipft"] == pytest.approx(6.1707)
    assert fees["sebi_turnover"] == pytest.approx(0.201)
    assert fees["stt"] == pytest.approx(25.25)
    assert fees["stamp_duty"] == pytest.approx(3.0)
    assert fees["gst"] == pytest.approx((60.3 + 6.1707 + 0.201) * 0.18)
    assert fees["total"] == pytest.approx(sum(fees.values()))


def test_fee_model_rejects_negative_turnover() -> None:
    with pytest.raises(ValueError, match="turnover"):
        calculate_intraday_equity_fees(
            buy_value=-1.0,
            sell_value=100.0,
            schedule=NSE_EQUITY_INTRADAY_2026,
        )


def test_fee_schedule_rejects_invalid_gst() -> None:
    schedule = IndiaEquityIntradayFeeSchedule(
        version="test",
        effective_from="2026-01-01",
        brokerage_rate=0.0,
        exchange_and_ipft_rate=0.0,
        sebi_turnover_rate=0.0,
        stt_sell_rate=0.0,
        stamp_buy_rate=0.0,
        gst_rate=1.1,
    )
    with pytest.raises(ValueError, match="gst_rate"):
        schedule.validate()
