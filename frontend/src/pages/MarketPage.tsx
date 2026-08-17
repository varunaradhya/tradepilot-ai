import { useEffect, useRef, useState } from "react";
import StockSearch, { type StockInstrument } from "../components/StockSearch";
import { getHistory, getQuote, type HistoryResponse, type Quote } from "../services/market";

function money(value: number | null | undefined) {
  return value == null ? "—" : value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function signedMoney(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : "−"}₹${money(Math.abs(value))}`;
}

export default function MarketPage() {
  const [symbol, setSymbol] = useState("");
  const [selected, setSelected] = useState<StockInstrument | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [range, setRange] = useState("1mo");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef(0);

  async function search(next = selected, nextRange = range) {
    if (!next) {
      setError("Select an NSE stock from the suggestions before searching.");
      return;
    }
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError("");
    try {
      const [quoteResult, historyResult] = await Promise.all([getQuote(next.symbol), getHistory(next.symbol, nextRange, "1d")]);
      if (currentRequest !== requestId.current) return;
      setQuote(quoteResult);
      setHistory(historyResult);
    } catch (e) {
      if (currentRequest !== requestId.current) return;
      setQuote(null);
      setHistory(null);
      setError(e instanceof Error ? e.message : "Unable to load Indian market data.");
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }

  useEffect(() => {
    return () => { requestId.current += 1; };
  }, []);

  const points = (history?.data ?? []).filter((item) => item.close != null).slice(-120);
  const values = points.map((item) => item.close as number);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const width = 900;
  const height = 260;
  const spread = Math.max(max - min, 0.000001);
  const path = values.map((value, index) => `${index === 0 ? "M" : "L"} ${(index / Math.max(values.length - 1, 1)) * width} ${height - 20 - ((value - min) / spread) * (height - 40)}`).join(" ");
  const first = values[0];
  const last = values[values.length - 1];
  const chartChange = first != null && last != null ? last - first : null;
  const chartChangePercent = first ? ((last - first) / first) * 100 : null;
  const positive = (quote?.change_percent ?? chartChangePercent ?? 0) >= 0;

  return (
    <main className="tp-page min-h-screen">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="tp-live-line">NSE market terminal</div>
          <h1 className="tp-page-title mt-2 text-4xl font-black">Markets</h1>
          <p className="tp-page-subtitle mt-2 max-w-2xl text-sm">Search the authoritative NSE equity universe, then inspect the latest available quote and historical price action.</p>
        </div>
        <div className="rounded-xl border border-emerald-400/15 bg-emerald-400/[.05] px-4 py-2.5 text-right"><p className="tp-section-label">Data scope</p><p className="mt-1 text-xs font-black text-emerald-300">INDIA · NSE ONLY</p></div>
      </header>

      <section className="tp-premium-card mt-6 rounded-2xl p-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
          <div className="min-w-0 flex-1">
            <StockSearch
              value={symbol}
              onChange={setSymbol}
              onSelectionChange={setSelected}
              onSelect={(instrument) => { setSelected(instrument); void search(instrument, range); }}
              placeholder="Search any NSE company or ticker..."
              className="w-full rounded-xl border border-white/10 bg-white/[.03] px-4 py-3 text-sm font-semibold text-white outline-none placeholder:text-slate-600 focus:border-violet-400/40 focus:ring-2 focus:ring-violet-400/10"
            />
          </div>
          <button type="button" onClick={() => void search()} disabled={loading || !selected || selected.symbol !== symbol.trim().toUpperCase()} className="rounded-xl bg-white px-6 py-3 text-xs font-black text-slate-950 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50">{loading ? "Loading…" : "Load stock"}</button>
          <div className="flex shrink-0 rounded-xl border border-white/10 bg-white/[.02] p-1">
            {["1mo", "3mo", "6mo", "1y"].map((item) => <button key={item} type="button" disabled={loading || !selected} onClick={() => { setRange(item); void search(selected, item); }} className={`rounded-lg px-3 py-2 text-xs font-black disabled:cursor-not-allowed disabled:opacity-50 ${range === item ? "bg-violet-500/20 text-violet-200" : "text-slate-600 hover:text-white"}`}>{item}</button>)}
          </div>
        </div>
        <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-slate-600">A stock must be selected from the backend instrument suggestions. Manual symbol submission is intentionally disabled.</p>
      </section>

      {error && <div className="mt-4 rounded-xl border border-amber-400/15 bg-amber-400/[.05] p-4 text-sm font-semibold text-amber-200">{error}</div>}

      {quote && <section className="tp-premium-card mt-6 rounded-2xl p-5"><div className="flex flex-wrap items-start justify-between gap-6"><div><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-violet-400/10 px-2.5 py-1 text-[10px] font-black text-violet-200">NSE</span><span className="rounded-full bg-white/[.04] px-2.5 py-1 text-[10px] font-black text-slate-500">{quote.data_status ?? "LIVE"}</span></div><h2 className="mt-3 text-3xl font-black text-white">{quote.symbol}</h2><p className="mt-1 text-sm font-semibold text-slate-500">{quote.name ?? selected?.name ?? "NSE listed equity"}</p></div><div className="text-right"><p className="tp-number text-4xl font-black text-white">₹{money(quote.price)}</p><p className={`mt-1 text-sm font-black ${positive ? "text-emerald-300" : "text-rose-300"}`}>{signedMoney(quote.change)} ({quote.change_percent == null ? "—" : `${quote.change_percent >= 0 ? "+" : ""}${quote.change_percent.toFixed(2)}%`})</p></div></div><div className="mt-6 grid gap-3 sm:grid-cols-3">{[["PREVIOUS CLOSE", `₹${money(quote.previous_close)}`],["CURRENCY", quote.currency ?? "INR"],["MARKET TIME", quote.market_time ? new Date(quote.market_time).toLocaleString("en-IN") : "—"]].map(([label, value]) => <div key={label} className="rounded-xl border border-white/5 bg-white/[.025] p-4"><p className="tp-section-label">{label}</p><p className="mt-2 text-sm font-black text-slate-200">{value}</p></div>)}</div></section>}

      <section className="tp-premium-card mt-5 overflow-hidden rounded-2xl p-5">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="tp-section-label">Historical price action</p><h2 className="mt-1 text-xl font-black text-white">{selected?.symbol ?? "Select a stock"} · {range}</h2></div>{values.length > 0 && <div className="text-right text-xs font-semibold"><div className="text-slate-500">Low ₹{money(min)} · High ₹{money(max)}</div><div className={chartChange != null && chartChange >= 0 ? "text-emerald-300" : "text-rose-300"}>{chartChange != null ? `${signedMoney(chartChange)} (${chartChangePercent?.toFixed(2)}%)` : "—"}</div></div>}</div>
        {values.length === 0 ? <div className="mt-8 rounded-xl border border-white/5 bg-white/[.02] p-10 text-center text-sm text-slate-600">{loading ? "Loading historical prices…" : "Select an NSE stock to load historical prices."}</div> : <div className="mt-5 overflow-x-auto rounded-xl border border-white/5 bg-slate-950/40 p-3"><svg viewBox={`0 0 ${width} ${height}`} className="h-72 min-w-[700px] w-full" role="img" aria-label={`${selected?.symbol ?? "Stock"} NSE price chart`}><path d={path} fill="none" stroke="currentColor" strokeWidth="3" className={positive ? "text-emerald-300" : "text-rose-300"} vectorEffect="non-scaling-stroke"/><line x1="0" y1={height - 1} x2={width} y2={height - 1} stroke="currentColor" className="text-white/10"/></svg></div>}
      </section>
    </main>
  );
}
