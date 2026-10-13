import { useState } from "react";
import StockSearch from "../components/StockSearch";
import TechnicalChart from "../components/TechnicalChart";
import { getHistory,getQuote,getTechnicalAnalysis,type HistoryResponse,type Quote,type TechnicalAnalysis } from "../services/market";

function money(value:number|null|undefined){return value==null?"—":value.toLocaleString("en-IN",{minimumFractionDigits:2,maximumFractionDigits:2});}
function signed(value:number|null|undefined){return value==null?"—":(value>=0?"+":"−")+"₹"+money(Math.abs(value));}

export default function MarketPage(){
  const [symbol,setSymbol]=useState("TCS"),[quote,setQuote]=useState<Quote|null>(null),[history,setHistory]=useState<HistoryResponse|null>(null),[analysis,setAnalysis]=useState<TechnicalAnalysis|null>(null);
  const [range,setRange]=useState("1y"),[loading,setLoading]=useState(false),[error,setError]=useState("");
  async function search(nextSymbol=symbol,nextRange=range){
    const normalized=nextSymbol.trim().toUpperCase(); if(!normalized){setError("Enter an Indian stock symbol or select a company from search.");return;}
    setSymbol(normalized);setRange(nextRange);setLoading(true);setError("");
    const [q,h,a]=await Promise.allSettled([getQuote(normalized),getHistory(normalized,nextRange,"1d"),getTechnicalAnalysis(normalized,nextRange,"1d")]);
    setQuote(q.status==="fulfilled"?q.value:null);setHistory(h.status==="fulfilled"?h.value:null);setAnalysis(a.status==="fulfilled"?a.value:null);
    const failures=[q,h,a].filter(x=>x.status==="rejected");
    if(failures.length===3){const reason=failures[0].reason;setError(reason instanceof Error?reason.message:"Unable to load Indian market data.");}
    else if(failures.length){setError("Some market-analysis data is temporarily unavailable. The available panels remain usable.");}
    setLoading(false);
  }
  const signal=analysis?.signal.direction??"neutral";
  const signalClass=signal==="bullish"?"text-emerald-300 bg-emerald-400/10":signal==="bearish"?"text-rose-300 bg-rose-400/10":"text-amber-300 bg-amber-400/10";
  const latest=analysis?.latest??{};
  return <main className="tp-page min-h-screen">
    <header className="flex flex-wrap items-end justify-between gap-5">
      <div><div className="tp-live-line">NSE / BSE market terminal</div><h1 className="tp-page-title mt-2 text-4xl font-black">Markets & Technical Analysis</h1><p className="tp-page-subtitle mt-2 max-w-3xl text-sm">Interactive OHLCV research with deterministic indicators. Signals are analytical scenarios, not guaranteed outcomes or financial advice.</p></div>
      <div className="rounded-xl border border-emerald-400/15 bg-emerald-400/[.05] px-4 py-2.5 text-right"><p className="tp-section-label">Data scope</p><p className="mt-1 text-xs font-black text-emerald-300">INDIA · NSE FIRST</p></div>
    </header>
    <section className="tp-premium-card mt-6 rounded-2xl p-5">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <div className="min-w-0 flex-1"><StockSearch value={symbol} onChange={setSymbol} onSelect={item=>void search(item.symbol)} placeholder="Search any Indian company or NSE ticker..." className="w-full rounded-xl border border-white/10 bg-white/[.03] px-4 py-3 text-sm font-semibold text-white outline-none placeholder:text-slate-600 focus:border-violet-400/40 focus:ring-2 focus:ring-violet-400/10"/></div>
        <button type="button" onClick={()=>void search()} disabled={loading} className="rounded-xl bg-white px-6 py-3 text-xs font-black text-slate-950 disabled:opacity-50">{loading?"Loading…":"Analyse Indian Stock"}</button>
        <div className="flex shrink-0 rounded-xl border border-white/10 bg-white/[.02] p-1">{["1mo","3mo","6mo","1y"].map(item=><button key={item} type="button" onClick={()=>void search(symbol,item)} className={"rounded-lg px-3 py-2 text-xs font-black "+(range===item?"bg-violet-500/20 text-violet-200":"text-slate-600 hover:text-white")}>{item}</button>)}</div>
      </div>
      <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Provider status is shown from the backend. Cached, delayed, historical and unavailable data must not be interpreted as live quotes.</p>
    </section>
    {error&&<div className="mt-4 rounded-xl border border-amber-400/15 bg-amber-400/[.05] p-4 text-sm font-semibold text-amber-200">{error}</div>}
    {quote&&<section className="tp-premium-card mt-6 rounded-2xl p-5"><div className="flex flex-wrap items-start justify-between gap-6"><div><div className="flex gap-2"><span className="rounded-full bg-violet-400/10 px-2.5 py-1 text-[10px] font-black text-violet-200">{quote.exchange??"NSE"}</span><span className="rounded-full bg-white/[.04] px-2.5 py-1 text-[10px] font-black text-slate-500">{quote.data_status??"UNKNOWN"}</span></div><h2 className="mt-3 text-3xl font-black text-white">{quote.symbol}</h2><p className="mt-1 text-sm font-semibold text-slate-500">{quote.name??"Indian listed equity"}</p></div><div className="text-right"><p className="tp-number text-4xl font-black text-white">₹{money(quote.price)}</p><p className={"mt-1 text-sm font-black "+((quote.change_percent??0)>=0?"text-emerald-300":"text-rose-300")}>{signed(quote.change)} ({quote.change_percent==null?"—":(quote.change_percent>=0?"+":"")+quote.change_percent.toFixed(2)+"%"})</p></div></div></section>}
    {history&&<section className="tp-premium-card mt-5 rounded-2xl p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><p className="tp-section-label">Candlestick chart</p><h2 className="mt-1 text-xl font-black text-white">{symbol} · {range} · {history.data_status}</h2></div><div className={"rounded-full px-3 py-1 text-xs font-black uppercase "+signalClass}>{signal} · {analysis?.bar_count??history.data.length} bars</div></div><TechnicalChart data={history.data} analysis={analysis}/></section>}
    {analysis&&<section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[["SMA 20",latest.sma20],["SMA 50",latest.sma50],["EMA 21",latest.ema21],["RSI 14",latest.rsi14],["ATR 14",latest.atr14]].map(([label,value])=><div key={String(label)} className="tp-premium-card rounded-xl p-4"><p className="tp-section-label">{label}</p><p className="mt-2 text-lg font-black text-white">{typeof value==="number"?money(value):"—"}</p></div>)}</section>}
    {analysis&&<section className="mt-5 grid gap-4 lg:grid-cols-2"><div className="tp-premium-card rounded-2xl p-5"><p className="tp-section-label">Deterministic signal evidence</p><h2 className="mt-2 text-2xl font-black text-white">{signal.toUpperCase()}</h2><ul className="mt-4 space-y-2 text-sm text-slate-400">{analysis.signal.conditions.length?analysis.signal.conditions.map(x=><li key={x} className="rounded-lg bg-white/[.03] p-3">{x}</li>):<li>No sufficient indicator conditions.</li>}</ul></div><div className="tp-premium-card rounded-2xl p-5"><p className="tp-section-label">Data quality boundary</p><h2 className="mt-2 text-xl font-black text-white">{analysis.data_status}</h2><p className="mt-3 text-sm leading-6 text-slate-400">Analysis timestamp: {new Date(analysis.analysis_timestamp).toLocaleString("en-IN")}. Indicators become available only after their required history exists. The signal uses the latest provider bar and does not claim that the bar is a confirmed candle close.</p><p className="mt-3 text-xs text-slate-600">SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP and relative volume are calculated deterministically on the backend.</p></div></section>}
    {!history&&!loading&&<section className="tp-premium-card mt-6 rounded-2xl p-10 text-center text-sm text-slate-600">Search an Indian stock to load verified OHLCV data and technical analysis.</section>}
  </main>;
}
