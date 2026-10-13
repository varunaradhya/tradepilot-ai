from app.services.technical_indicators import atr,bollinger,calculate_indicators,ema,macd,relative_volume,rsi,sma,vwap

def test_sma_uses_only_completed_window():
    assert sma([1,2,3,4],3)==[None,None,2.0,3.0]

def test_ema_starts_from_period_sma():
    result=ema([1,2,3,4,5],3)
    assert result[:2]==[None,None]
    assert result[2]==2.0
    assert round(result[4],6)==4.0

def test_rsi_handles_zero_loss():
    assert rsi(list(range(1,20)),14)[-1]==100.0

def test_macd_and_bollinger_preserve_length():
    closes=list(range(1,60))
    line,signal,hist=macd(closes); middle,upper,lower=bollinger(closes)
    assert len(line)==len(signal)==len(hist)==len(closes)
    assert len(middle)==len(upper)==len(lower)==len(closes)

def test_atr_and_vwap_handle_ohlcv():
    high=[11,12,13,14,15]; low=[9,10,11,12,13]; close=[10,11,12,13,14]; volume=[100,100,200,200,400]
    assert atr(high,low,close,3)[-1] is not None
    assert vwap(high,low,close,volume)[-1] is not None

def test_relative_volume_uses_prior_window():
    result=relative_volume([100]*21,20)
    assert result[:20]==[None]*20 and result[20]==1.0

def test_indicator_bundle_is_deterministic():
    bars=[{"close":float(i),"high":float(i+1),"low":float(i-1),"volume":100} for i in range(1,80)]
    assert calculate_indicators(bars)==calculate_indicators(bars)

def test_short_history_does_not_emit_directional_signal():
    from app.services.technical_indicators import build_signal
    bars=[{"close":float(i),"high":float(i+1),"low":float(i-1),"volume":100} for i in range(1,25)]
    indicators=calculate_indicators(bars)
    signal=build_signal(bars,indicators)
    assert signal["direction"]=="neutral"
    assert signal["sufficient_data"] is False
