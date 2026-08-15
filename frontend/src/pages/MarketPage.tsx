import { useState } from "react";
import StockSearch from "../components/StockSearch";
import { getHistory, getQuote, type HistoryResponse, type Quote } from "../services/market";

function money(value: number | null | undefined) { return value == null ? "-" : value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function MarketPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [range, setRange] = useState("1mo");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(nextSymbol = symbol) {
    const normalized = nextSymbol.trim().toUpperCase();
    if (!normalized) { setError("Select a stock symbol."); return; }
    setSymbol(normalized); setLoading(true); setError("");
    try {
      const [result, historyResult] = await Promise.all([getQuote(normalized), getHistory(normalized, range, "1d")]);
      setQuote(result); setHistory(historyResult);
    } catch (err) { setQuote(null); setHistory(null); setError(err instanceof Error ? err.message : "Unable to load market data."); }
    finally { setLoading(false); }
  }

  const points = (history?.data ?? []).filter((item) => item.close != null).slice(-90);
  const values = points.map((item) => item.close as number);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const width = 900;
  const height = 260;
  const path = values.map((value, index) => `${index === 0 ? "M" : "L"} ${(index / Math.max(values.length - 1, 1)) * width} ${height - ((value - min) / Math.max(max - min, 0.000001)) * (height - 20)}`).join(" ");

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900"><div className="mx-auto max-w-6xl">
      <div><h1 className="text-3xl font-bold">Markets</h1><p className="mt-2 text-slate-600">Search a stock, inspect its live quote and review recent price action.</p></div>
      <div className="mt-6 flex flex-col gap-3 md:flex-row"><div className="w-full md:max-w-xl"><StockSearch value={symbol} onChange={setSymbol} onSelect={(instrument) => void search(instrument.symbol)} placeholder="Search company or ticker..." /></div><button type="button" onClick={() => void search()} disabled={loading} className="rounded-lg bg-slate-950 px-5 py-2.5 font-semibold text-white disabled:opacity-50">{loading ? "Loading..." : "Search"}</button><div className="flex rounded-lg border bg-white p-1">{["1mo", "3mo", "6mo", "1y"].map((item) => <button key={item} type="button" onClick={() => { setRange(item); void search(symbol); }} className={`rounded px-3 py-2 text-sm font-semibold ${range === item ? "bg-slate-950 text-white" : "text-slate-600"}`}>{item}</button>)}</div></div>
      {error && <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 font-medium text-red-700">{error}</div>}
      {quote && <section className="mt-8 rounded-2xl border bg-white p-6 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-6"><div><p className="text-sm font-semibold text-slate-500">{quote.exchange ?? "Market"}</p><h2 className="mt-1 text-3xl font-bold">{quote.symbol}</h2><p className="mt-1 text-slate-500">{quote.name ?? ""}</p></div><div className="text-right"><p className="text-4xl font-bold">{money(quote.price)}</p><p className={`mt-1 font-bold ${(quote.change_percent ?? 0) >= 0 ? "text-emerald-700" : "text-red-700"}`}>{(quote.change ?? 0) >= 0 ? "+" : ""}{money(quote.change)} ({(quote.change_percent ?? 0) >= 0 ? "+" : ""}{(quote.change_percent ?? 0).toFixed(2)}%)</p></div></div><div className="mt-6 grid gap-4 sm:grid-cols-3"><div><p className="text-sm text-slate-500">Previous Close</p><p className="mt-1 text-lg font-semibold">{money(quote.previous_close)}</p></div><div><p className="text-sm text-slate-500">Currency</p><p className="mt-1 text-lg font-semibold">{quote.currency ?? "-"}</p></div><div><p className="text-sm text-slate-500">Market Time</p><p className="mt-1 text-sm font-semibold">{quote.market_time ? new Date(quote.market_time).toLocaleString("en-IN") : "-"}</p></div></div></section>}
      <section className="mt-6 rounded-2xl border bg-white p-6 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="text-xl font-semibold">Price chart</h2><p className="text-sm text-slate-500">{symbol} · {range}</p></div>{values.length > 0 && <span className="text-sm font-semibold text-slate-500">Low ₹{money(min)} · High ₹{money(max)}</span>}</div>{values.length === 0 ? <div className="mt-10 text-center text-slate-500">Search a supported symbol to load historical prices.</div> : <div className="mt-5 overflow-x-auto"><svg viewBox={`0 0 ${width} ${height}`} className="h-72 min-w-[700px] w-full" role="img" aria-label={`${symbol} price chart`}><path d={path} fill="none" stroke="currentColor" strokeWidth="3" className="text-slate-900" /><line x1="0" y1={height - 1} x2={width} y2={height - 1} stroke="currentColor" className="text-slate-200" /></svg></div>}</section>
    </div></main>
  );
}
