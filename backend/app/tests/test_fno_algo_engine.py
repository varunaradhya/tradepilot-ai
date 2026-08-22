from datetime import datetime
from zoneinfo import ZoneInfo

from app.api.v1.fno import _historical_rows, _quote_from_response
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
                "ce": {"strike": 25000, "security_id": "CE1", "last_price": 300, "top_bid_price": 299, "top_ask_price": 300, "volume": 100000, "oi": 500000, "implied_volatility": 15, "greeks": {"delta": 0.52, "gamma": 0.01, "theta": -2, "vega": 5}},
                "pe": {"strike": 25000, "security_id": "PE1", "last_price": 300, "top_bid_price": 299, "top_ask_price": 300, "volume": 100000, "oi": 500000, "implied_volatility": 15, "greeks": {"delta": -0.48, "gamma": 0.01, "theta": -2, "vega": 5}},
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
        underlying={"symbol": "NIFTY", "capital": 300000},
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


def test_quote_parser_prefers_best_bid_for_executable_long_exit():
    response = {"data": {"NSE_FNO": {"123": {"last_price": 105.0, "depth": {"buy": [{"price": 103.5, "quantity": 100}], "sell": [{"price": 106.0, "quantity": 100}]}}}}}
    quote = _quote_from_response(response, "123")
    assert quote == {"bid": 103.5, "ask": 106.0, "ltp": 105.0}


class _HistoricalClient:
    def __init__(self, rows):
        self.rows = rows
        self.call = None

    def historical_intraday(self, security_id, segment, instrument, interval, from_date, to_date):
        self.call = (security_id, segment, instrument, interval, from_date, to_date)
        return self.rows


class _FixedDateTime:
    @classmethod
    def now(cls, tz=None):
        fixed = datetime(2026, 8, 22, 10, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
        return fixed.astimezone(tz) if tz else fixed


def test_historical_rows_requests_current_session_with_ist_timestamps_and_filters_incomplete_bars(monkeypatch):
    monkeypatch.setattr("app.api.v1.fno.datetime", _FixedDateTime)
    now = _FixedDateTime.now(ZoneInfo("Asia/Kolkata"))
    timestamps = [now.timestamp() - 600, now.timestamp() - 300, now.timestamp() - 60]
    payload = {
        "data": {
            "open": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
            "close": [100.5, 101.5, 102.5],
            "volume": [1000, 1100, 1200],
            "timestamp": timestamps,
        }
    }
    client = _HistoricalClient(payload)
    rows = _historical_rows(client, 13, "IDX_I", "5")

    assert client.call is not None
    assert client.call[0:4] == ("13", "IDX_I", "INDEX", "5")
    assert " 09:15:00" in client.call[4]
    assert client.call[5].count(":") == 2
    assert len(rows) == 2
    assert rows == sorted(rows, key=lambda row: row["timestamp"])


def test_historical_rows_deduplicates_timestamps_and_rejects_invalid_ohlc(monkeypatch):
    monkeypatch.setattr("app.api.v1.fno.datetime", _FixedDateTime)
    now = _FixedDateTime.now(ZoneInfo("Asia/Kolkata")).timestamp()
    timestamp = now - 600
    payload = {
        "data": {
            "open": [100, 100, 100],
            "high": [101, 101, 99],
            "low": [99, 99, 101],
            "close": [100.5, 100.5, 100.5],
            "volume": [1000, 1100, 1200],
            "timestamp": [timestamp, timestamp, now - 300],
        }
    }
    rows = _historical_rows(_HistoricalClient(payload), 13, "IDX_I", "5")
    assert len(rows) == 1
    assert rows[0]["timestamp"] == timestamp
