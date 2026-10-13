from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.market import HistoryResponse, QuoteResponse, SearchInstrumentResponse, TechnicalAnalysisResponse
from app.services.market_service import IndianSymbolError, MarketDataNotFoundError, MarketDataProviderError, MarketSearchProviderError, get_history, get_quote, search_instruments
from app.services.technical_indicators import build_signal, calculate_indicators
from datetime import datetime, timezone

router=APIRouter(prefix="/market",tags=["Market Data"])

@router.get("/search",response_model=list[SearchInstrumentResponse])
def market_search(q:str=Query(min_length=2,max_length=80)):
    try: return [SearchInstrumentResponse(symbol=x.symbol,name=x.name,exchange=x.exchange) for x in search_instruments(q)]
    except MarketSearchProviderError as exc: raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,detail=str(exc)) from exc

@router.get("/quote/{symbol}",response_model=QuoteResponse)
def market_quote(symbol:str):
    try: quote=get_quote(symbol)
    except IndianSymbolError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except MarketDataNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except MarketDataProviderError as exc: raise HTTPException(status_code=503,detail=str(exc)) from exc
    return QuoteResponse(symbol=quote.symbol,name=quote.name,currency=quote.currency,exchange=quote.exchange,price=quote.price,previous_close=quote.previous_close,change=quote.change,change_percent=quote.change_percent,market_time=quote.market_time,data_status=quote.data_status)

@router.get("/history/{symbol}",response_model=HistoryResponse)
def market_history(symbol:str,range_:str=Query(default="1mo",alias="range"),interval:str=Query(default="1d")):
    allowed_ranges={"1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"}
    allowed_intervals={"1m","2m","5m","15m","30m","60m","90m","1h","1d","5d","1wk","1mo","3mo"}
    if range_ not in allowed_ranges: raise HTTPException(status_code=422,detail="Invalid range")
    if interval not in allowed_intervals: raise HTTPException(status_code=422,detail="Invalid interval")
    try: history=get_history(symbol=symbol,range_=range_,interval=interval)
    except IndianSymbolError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except MarketDataNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except MarketDataProviderError as exc: raise HTTPException(status_code=503,detail=str(exc)) from exc
    return HistoryResponse(symbol=history.symbol,currency=history.currency,interval=history.interval,range=history.range,data=history.data,data_status=history.data_status)

@router.get("/technical-analysis/{symbol}",response_model=TechnicalAnalysisResponse)
def technical_analysis(symbol:str,range_:str=Query(default="1y",alias="range"),interval:str=Query(default="1d")):
    allowed_ranges={"1mo","3mo","6mo","1y","2y","5y","10y","max"}
    allowed_intervals={"1d","1wk","1mo","5m","15m","30m","60m","1h"}
    if range_ not in allowed_ranges: raise HTTPException(status_code=422,detail="Invalid analysis range")
    if interval not in allowed_intervals: raise HTTPException(status_code=422,detail="Invalid analysis interval")
    try: history=get_history(symbol=symbol,range_=range_,interval=interval)
    except IndianSymbolError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except MarketDataNotFoundError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except MarketDataProviderError as exc: raise HTTPException(status_code=503,detail=str(exc)) from exc
    bars=[{"timestamp":b["timestamp"],"open":b.get("open"),"high":b.get("high"),"low":b.get("low"),"close":b.get("close"),"volume":b.get("volume")} for b in history.data]
    indicators=calculate_indicators(bars)
    if interval not in {"5m", "15m", "30m", "60m", "1h"}:
        indicators["vwap"] = [None] * len(bars)
    latest={key:next((v for v in reversed(values) if v is not None),None) for key,values in indicators.items()}
    signal=build_signal(bars,indicators)
    signal["symbol"]=history.symbol
    signal["exchange"]="NSE-first"
    signal["analysis_timestamp"]=datetime.now(timezone.utc)
    signal["timeframe"]=interval
    signal["data_status"]=history.data_status
    return TechnicalAnalysisResponse(symbol=history.symbol,interval=interval,range=range_,data_status=history.data_status,analysis_timestamp=signal["analysis_timestamp"],bar_count=len(bars),indicators=indicators,latest=latest,signal=signal)
