import pytest

from app.providers.market_data import MarketDataProviderError, YahooFinanceProvider


def test_nse_symbol_is_added_for_plain_indian_symbol():
    assert YahooFinanceProvider._provider_symbol("tcs") == "TCS.NS"


def test_existing_exchange_suffix_is_preserved():
    assert YahooFinanceProvider._provider_symbol("TCS.NS") == "TCS.NS"
    assert YahooFinanceProvider._provider_symbol("tcs.bo") == "TCS.BO"


def test_empty_market_symbol_is_rejected():
    with pytest.raises(MarketDataProviderError, match="Symbol is required"):
        YahooFinanceProvider._provider_symbol("   ")
