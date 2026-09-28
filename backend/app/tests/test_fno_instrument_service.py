from app.services.fno_instrument_service import FNOInstrumentMaster, FNOUnderlying


def test_search_returns_index_matches_without_option_master():
    master = FNOInstrumentMaster()
    master.items = [
        FNOUnderlying("13", "IDX_I", "NIFTY", "Nifty 50"),
        FNOUnderlying("25", "IDX_I", "BANKNIFTY", "Nifty Bank"),
    ]
    master.loaded_at = 10**12
    master.option_rows = []
    master.option_loaded_at = 10**12
    master._load_options = lambda force=False: []

    results = master.search("BANK")
    assert [item.symbol for item in results] == ["BANKNIFTY"]


def test_search_adds_unique_stock_option_underlyings():
    master = FNOInstrumentMaster()
    master.items = [
        FNOUnderlying("13", "IDX_I", "NIFTY", "Nifty 50"),
    ]
    master.loaded_at = 10**12
    master.option_rows = [
        {
            "INSTRUMENT": "OPTSTK",
            "UNDERLYING_SYMBOL": "RELIANCE",
            "UNDERLYING_SECURITY_ID": "2885",
            "UNDERLYING_CUSTOM_SYMBOL": "Reliance Industries",
        },
        {
            "INSTRUMENT": "OPTSTK",
            "UNDERLYING_SYMBOL": "RELIANCE",
            "UNDERLYING_SECURITY_ID": "2885",
            "UNDERLYING_CUSTOM_SYMBOL": "Reliance Industries",
        },
        {
            "INSTRUMENT": "OPTIDX",
            "UNDERLYING_SYMBOL": "NIFTY",
            "UNDERLYING_SECURITY_ID": "13",
        },
    ]
    master.option_loaded_at = 10**12

    results = master.search("REL")
    assert len(results) == 1
    assert results[0] == FNOUnderlying(
        "2885", "NSE_EQ", "RELIANCE", "Reliance Industries"
    )


def test_search_does_not_return_stock_option_without_underlying_security_id():
    master = FNOInstrumentMaster()
    master.items = []
    master.loaded_at = 10**12
    master.option_rows = [
        {
            "INSTRUMENT": "OPTSTK",
            "UNDERLYING_SYMBOL": "TCS",
            "UNDERLYING_CUSTOM_SYMBOL": "Tata Consultancy Services",
        }
    ]
    master.option_loaded_at = 10**12

    assert master.search("TCS") == []
