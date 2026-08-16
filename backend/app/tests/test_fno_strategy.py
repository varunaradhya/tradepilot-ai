from app.services.fno_strategy import build_fno_decision,select_option_contracts

def chain():
 return {"oc":{"25000.000000":{"ce":{"security_id":1,"last_price":120,"top_bid_price":119,"top_ask_price":120,"volume":50000,"oi":200000,"implied_volatility":18,"greeks":{"delta":.52}},"pe":{"security_id":2,"last_price":110,"top_bid_price":109,"top_ask_price":111,"volume":40000,"oi":180000,"implied_volatility":20,"greeks":{"delta":-.48}}},"25200.000000":{"ce":{"security_id":3,"last_price":80,"top_bid_price":70,"top_ask_price":85,"volume":50,"oi":100,"implied_volatility":120,"greeks":{"delta":.2}}}}}

def test_bullish_selects_liquid_call():
 rows=select_option_contracts(chain(),"BULLISH"); assert rows and rows[0]["option_type"]=="CE" and rows[0]["strike"]==25000

def test_bearish_selects_put():
 rows=select_option_contracts(chain(),"BEARISH"); assert rows and rows[0]["option_type"]=="PE"

def test_risk_sizing_is_lot_aligned():
 rows=select_option_contracts(chain(),"BULLISH"); d=build_fno_decision({"symbol":"NIFTY","capital":100000,"lot_size":25},"BULLISH",rows); assert d["decision"]=="QUALIFIED" and d["quantity"]%25==0 and d["execution_mode"]=="PAPER_ONLY"

def test_no_trade_when_risk_budget_cannot_buy_lot():
 rows=select_option_contracts(chain(),"BULLISH"); d=build_fno_decision({"symbol":"NIFTY","capital":1000,"lot_size":25},"BULLISH",rows); assert d["decision"]=="NO_TRADE"
