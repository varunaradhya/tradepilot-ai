from app.services.fno_algo_engine import build_autonomous_option_decision, infer_direction


def _bars(direction="up", count=80):
    rows = []
    price = 100.0
    for i in range(count):
        if direction == "up":
            price += 0.5
        elif direction == "down":
            price -= 0.5
        else:
            price += 0.05 if i % 2 else -0.05
        rows.append({"open": price - 0.1, "high": price + 0.3, "low": price - 0.3, "close": price, "volume": 1000 + (500 if i == count - 1 else 0)})
    return rows


def _chain():
    return {
        "oc": {
            "25000": {
                "ce": {"strike": 25000, "security_id": "CE1", "last_price": 180, "top_bid_price": 179, "top_ask_price": 181, "volume": 100000, "oi": 500000, "implied_volatility": 15, "greeks": {"delta": 0.52, "gamma": 0.01, "theta": -2, "vega": 5}},
                "pe": {"strike": 25000, "security_id": "PE1", "last_price": 180, "top_bid_price": 179, "top_ask_price": 181, "volume": 100000, "oi": 500000, "implied_volatility": 15, "greeks": {"delta": -0.48, "gamma": 0.01, "theta": -2, "vega": 5}},
            }
        }
    }


def test_direction_engine_fails_closed_on_ambiguous_data():
    result = infer_direction(_bars("flat"))
    assert result.direction == "NO_TRADE"


def test_direction_engine_detects_bullish_trend():
    result = infer_direction(_bars("up"))
    assert result.direction == "BULLISH"
    assert result.confidence >= 65
    assert result.atr > 0


def test_direction_engine_detects_bearish_trend():
    result = infer_direction(_bars("down"))
    assert result.direction == "BEARISH"
    assert result.confidence >= 65


def test_autonomous_decision_sizes_in_exchange_lots_and_accounts_for_costs():
    result = build_autonomous_option_decision(
        underlying={"symbol": "NIFTY", "capital": 100000},
        bars=_bars("up"),
        option_chain=_chain(),
        lot_size=75,
    )
    assert result["direction"] == "BULLISH"
    assert result["decision"] == "QUALIFIED"
    assert result["quantity"] % 75 == 0
    assert result["lots"] >= 1
    assert result["risk_reward"] >= 1.8
    assert result["stop"] < result["entry"] < result["target"]
    assert result["estimated_stop_costs"]["total"] > 0
    assert result["estimated_target_costs"]["total"] > 0
    assert result["risk_amount"] <= result["risk_budget"]


def test_autonomous_decision_rejects_capital_that_cannot_fund_one_lot():
    result = build_autonomous_option_decision(
        underlying={"symbol": "NIFTY", "capital": 1000},
        bars=_bars("up"),
        option_chain=_chain(),
        lot_size=75,
    )
    assert result["decision"] == "NO_TRADE"
    assert result["reason"] == "RISK_BUDGET_TOO_SMALL_FOR_ONE_LOT"
