from datetime import date

from app.services.fno_instrument_service import parse_fno_instrument_csv


def test_parser_uses_derivative_underlying_ids_and_excludes_non_option_indices():
    csv = """EXCH_ID,SEGMENT,INSTRUMENT,UNDERLYING_SECURITY_ID,UNDERLYING_SYMBOL,EXPIRY_DATE\nNSE,D,OPTIDX,13,NIFTY,2026-08-20\nNSE,D,OPTIDX,813,NIFTY MIDCAP 150,2026-08-20\nNSE,D,OPTIDX,25,MIDCPNIFTY,2026-08-20\nNSE,D,OPTSTK,11536,TCS,2026-08-25\nNSE,E,INDEX,813,NIFTY MIDCAP 150,2026-08-20\nNSE,D,OPTIDX,99,OLDINDEX,2026-01-01\n"""

    items = parse_fno_instrument_csv(csv, today=date(2026, 8, 17))
    by_symbol = {item.symbol: item for item in items}

    assert by_symbol["NIFTY"].security_id == "13"
    assert by_symbol["NIFTY"].exchange_segment == "IDX_I"
    assert by_symbol["MIDCPNIFTY"].name == "Nifty Midcap Select"
    assert by_symbol["TCS"].security_id == "11536"
    assert by_symbol["TCS"].exchange_segment == "NSE_EQ"
    assert "NIFTY MIDCAP 150" not in by_symbol
    assert "OLDINDEX" not in by_symbol
