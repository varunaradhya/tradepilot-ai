import copy

import pytest

from app.services.fno_replay_service import (
    MIN_COMPLETED_BARS,
    assert_replay_is_future_invariant,
    replay_autonomous_option_decisions,
)


def _bars(count=75):
    rows = []
    price = 100.0
    for index in range(count):
        price += 0.5
        rows.append({
            "open": price - 0.1,
            "high": price + 0.3,
            "low": price - 0.3,
            "close": price,
            "volume": 1000,
            "timestamp": index,
        })
    return rows


def _chain():
    return {
        "oc": {
            "25000": {
                "ce": {
                    "strike": 25000,
                    "security_id": "CE1",
                    "last_price": 300,
                    "top_bid_price": 299,
                    "top_ask_price": 300,
                    "volume": 100000,
                    "oi": 500000,
                    "implied_volatility": 15,
                    "greeks": {"delta": 0.52, "gamma": 0.01, "theta": -2, "vega": 5},
                },
                "pe": {
                    "strike": 25000,
                    "security_id": "PE1",
                    "last_price": 300,
                    "top_bid_price": 299,
                    "top_ask_price": 300,
                    "volume": 100000,
                    "oi": 500000,
                    "implied_volatility": 15,
                    "greeks": {"delta": -0.48, "gamma": 0.01, "theta": -2, "vega": 5},
                },
            }
        }
    }


def test_replay_uses_only_information_available_at_each_bar():
    bars = _bars()
    chains = [_chain() for _ in bars]
    decisions = replay_autonomous_option_decisions(
        underlying={"symbol": "NIFTY", "capital": 300000},
        bars=bars,
        option_chain_snapshots=chains,
        lot_size=75,
    )

    assert decisions
    assert decisions[0]["bar_index"] == MIN_COMPLETED_BARS - 1
    assert decisions[-1]["bar_index"] == len(bars) - 1
    assert all(item["decision"]["underlying"]["replay_bar_index"] == item["bar_index"] for item in decisions)


def test_replay_rejects_mismatched_bar_and_chain_lengths():
    with pytest.raises(ValueError, match="same length"):
        replay_autonomous_option_decisions(
            underlying={"symbol": "NIFTY", "capital": 300000},
            bars=_bars(),
            option_chain_snapshots=[_chain()],
            lot_size=75,
        )


def test_future_bar_mutation_cannot_change_earlier_decisions():
    bars = _bars()
    chains = [_chain() for _ in bars]
    assert_replay_is_future_invariant(
        underlying={"symbol": "NIFTY", "capital": 300000},
        bars=bars,
        option_chain_snapshots=chains,
        lot_size=75,
    )


def test_replay_does_not_mutate_input_bars():
    bars = _bars()
    original = copy.deepcopy(bars)
    chains = [_chain() for _ in bars]
    replay_autonomous_option_decisions(
        underlying={"symbol": "NIFTY", "capital": 300000},
        bars=bars,
        option_chain_snapshots=chains,
        lot_size=75,
    )
    assert bars == original
