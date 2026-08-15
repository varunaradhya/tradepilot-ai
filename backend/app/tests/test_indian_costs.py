from app.services.indian_costs import IndianEquityCostModel


def test_indian_cost_model_is_positive_and_breaks_down_costs():
    result = IndianEquityCostModel().estimate_round_trip(100000, 110000)
    assert result["total"] > 0
    assert result["stt"] > 0
    assert result["gst"] > 0
    assert round(sum(result[key] for key in ("brokerage", "exchange_charges", "sebi_charges", "stt", "gst", "slippage")), 2) == result["total"]
