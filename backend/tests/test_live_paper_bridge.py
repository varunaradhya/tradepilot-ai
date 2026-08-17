from __future__ import annotations

import time

import pytest

from app.services.live_paper_bridge import (
    LivePaperPosition,
    mark_paper_position,
    quote_payload_to_ltp,
)


def position(**overrides):
    data = {
        "symbol": "TCS",
        "quantity": 10,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "target": 110.0,
        "trailing_stop": 103.0,
    }
    data.update(overrides)
    return LivePaperPosition(**data)


def test_live_mark_calculates_gross_and_net_pnl():
    mark = mark_paper_position(position(), 105.0, 1_000, now=1_005)
    assert mark.symbol == "TCS"
    assert mark.gross_pnl == 50.0
    assert mark.net_pnl == 50.0
    assert mark.exit_reason is None
    assert mark.stale is False


def test_target_triggers_exit():
    mark = mark_paper_position(position(), 110.0, 1_000, now=1_005)
    assert mark.exit_reason == "TARGET"


def test_stop_loss_triggers_exit():
    mark = mark_paper_position(position(), 95.0, 1_000, now=1_005)
    assert mark.exit_reason == "STOP_LOSS"


def test_trailing_stop_triggers_exit():
    mark = mark_paper_position(position(), 103.0, 1_000, now=1_005)
    assert mark.exit_reason == "TRAILING_STOP"


def test_stale_tick_never_triggers_exit():
    mark = mark_paper_position(position(), 110.0, 1_000, now=1_011, max_tick_age_seconds=10)
    assert mark.stale is True
    assert mark.exit_reason is None


def test_invalid_ltp_is_rejected():
    with pytest.raises(ValueError, match="ltp must be positive"):
        mark_paper_position(position(), 0, int(time.time()))


def test_quote_payload_accepts_dhan_style_last_price():
    assert quote_payload_to_ltp({"TCS": {"last_price": 4210.5}}, "TCS") == 4210.5


def test_quote_payload_accepts_normalized_ltp():
    assert quote_payload_to_ltp({"tcs": {"ltp": 4210.5}}, "TCS") == 4210.5


def test_missing_quote_is_rejected():
    with pytest.raises(ValueError, match="missing quote"):
        quote_payload_to_ltp({}, "TCS")
