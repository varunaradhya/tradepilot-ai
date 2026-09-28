from app.services.paper_market_state_service import save_market_state, load_market_state


def test_market_state_round_trip(db_session):
    state={"opens":[100.0],"highs":[101.0],"lows":[99.0],"closes":[100.5],"volumes":[1000.0]}
    save_market_state(db_session,1,"2026-09-28","RELIANCE",state)
    assert load_market_state(db_session,1,"2026-09-28","RELIANCE")==state
