from app.services.fno_cost_service import FNOCostConfig, estimate_fno_option_costs, estimate_net_pnl


def test_option_costs_charge_brokerage_on_both_legs_and_stt_on_sell_only():
    costs = estimate_fno_option_costs(100.0, 120.0, 75)
    assert costs["brokerage"] == 40.0
    assert costs["stt"] == 9.0
    assert costs["stamp_duty"] == 0.23
    assert costs["total"] > costs["brokerage"]


def test_option_net_pnl_is_below_gross_pnl():
    net, costs = estimate_net_pnl(100.0, 120.0, 75)
    assert net < 1500.0
    assert net == round(1500.0 - costs["total"], 2)


def test_cost_model_is_configurable():
    config = FNOCostConfig(brokerage_per_order=0.0, stt_sell_rate=0.0, stamp_buy_rate=0.0)
    costs = estimate_fno_option_costs(100.0, 100.0, 75, config)
    assert costs["brokerage"] == 0.0
    assert costs["stt"] == 0.0
    assert costs["stamp_duty"] == 0.0
    assert costs["total"] > 0.0
