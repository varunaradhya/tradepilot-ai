from app.services.instrument_master_service import InstrumentMaster, parse_instrument_csv


CSV = """SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_TRADING_SYMBOL,SEM_CUSTOM_SYMBOL,SEM_INSTRUMENT_NAME,SEM_SERIES,ISIN
NSE,E,1333,TCS,TCS LTD,EQUITY,EQ,INE467B01029
NSE,E,11536,RELIANCE,RELIANCE LTD,EQUITY,EQ,INE002A01018
NSE,E,9999,TCS-TEST,TCS TEST LTD,EQUITY,EQ,
BSE,E,123,TCS,TCS BSE,EQUITY,A,
NSE,D,12345,NIFTY,NIFTY FUT,FUTIDX,,
"""


def test_parse_keeps_only_nse_cash_equities():
    items = parse_instrument_csv(CSV)
    assert [item.symbol for item in items] == ["TCS", "RELIANCE", "TCS-TEST"]
    assert all(item.exchange_segment == "NSE_EQ" for item in items)


def test_search_prefers_exact_then_prefix():
    master = InstrumentMaster(ttl_seconds=3600)
    master._items = parse_instrument_csv(CSV)
    results = master.search("TCS", limit=3)
    assert results[0].symbol == "TCS"
    assert results[1].symbol == "TCS-TEST"


def test_short_search_is_empty_without_network():
    master = InstrumentMaster()
    assert master.search("T") == []
