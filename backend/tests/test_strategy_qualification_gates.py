from app.services.strategy_qualification import QualificationPolicy, qualify_strategy


def _strong_backtest():
    return {"trades": 60, "profit_factor": 1.4, "max_drawdown_percent": 8.0}


def _strong_robustness():
    return {"summary": {"positive_return_percent": 80.0, "profit_factor_above_1_percent": 80.0}}


def _walk_forward(windows):
    return {
        "windows": len(windows),
        "v2": {
            "windows": windows,
            "summary": {
                "success_rate_percent": round(sum(w["return_percent"] > 0 for w in windows) / len(windows) * 100, 2) if windows else 0.0,
                "max_drawdown_percent": max((w["max_drawdown_percent"] for w in windows), default=0.0),
            },
        },
    }


def _window(number, trades=10, return_percent=1.0, drawdown=5.0):
    return {"window": number, "trades": trades, "return_percent": return_percent, "max_drawdown_percent": drawdown}


def test_qualification_rejects_single_profitable_validation_window():
    result = qualify_strategy(_strong_backtest(), _strong_robustness(), _walk_forward([_window(1)]))

    assert result["status"] == "NOT_QUALIFIED"
    assert not result["paper_trading_allowed"]
    assert any(check["name"] == "walk_forward_window_count" and not check["passed"] for check in result["checks"])


def test_qualification_rejects_too_few_validation_trades_even_with_good_returns():
    windows = [_window(1, trades=2), _window(2, trades=2), _window(3, trades=2), _window(4, trades=2)]
    result = qualify_strategy(_strong_backtest(), _strong_robustness(), _walk_forward(windows))

    assert result["status"] == "NOT_QUALIFIED"
    assert any(check["name"] == "walk_forward_trade_count" and not check["passed"] for check in result["checks"])
    assert any(check["name"] == "walk_forward_window_trade_floor" and not check["passed"] for check in result["checks"])


def test_qualification_accepts_multiple_meaningful_oos_windows():
    windows = [_window(1), _window(2), _window(3), _window(4)]
    policy = QualificationPolicy(min_walk_forward_windows=3, min_validation_trades_total=30)
    result = qualify_strategy(_strong_backtest(), _strong_robustness(), _walk_forward(windows), policy)

    assert result["status"] == "PAPER_CANDIDATE"
    assert result["paper_trading_allowed"]
