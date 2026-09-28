from app.services.strategy_registry import get_strategy,list_strategies
def test_registry_exposes_existing_strategies():
    versions={item["version"] for item in list_strategies()}
    assert {"V1","V2"} <= versions
def test_unknown_strategy_fails_closed():
    try: get_strategy("LIVE")
    except ValueError: return
    assert False
