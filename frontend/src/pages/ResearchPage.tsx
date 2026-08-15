import { useState } from "react";
import StockSearch from "../components/StockSearch";
import { getStockIntelligence, type IntelligenceResponse } from "../services/intelligence";

function number(value: unknown, digits = 2) { return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—"; }
function list(items: string[] | undefined, empty = "No specific items returned.") { return items?.length ? items : [empty]; }
function label(value: unknown) { return String(value ?? "—").replaceAll("_", " "); }

export default function ResearchPage() {
  const [symbol, setSymbol] = useState("");
  const [result, setResult] = useState<IntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyse(requested = symbol.trim().toUpperCase()) {
    if (!requested) return;
    setSymbol(requested); setLoading(true); setError("");
    try { setResult(await getStockIntelligence(requested)); }
    catch (err) { setResult(null); setError(err instanceof Error ? err.message : "Stock analysis is unavailable."); }
    finally { setLoading(false); }
  }

  const analysis = result?.analysis;
  const context = result?.context_summary ?? {};
  const signal = analysis?.signal ?? "NEUTRAL";
  const signalClass = signal === "BUY" ? "bg-emerald-100 text-emerald-800" : signal === "SELL" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800";
  const currentPrice = context.current_price ?? context.price ?? context.last_price;
  const indicators = analysis?.indicators ?? {};

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <header><p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Research</p><h1 className="mt-1 text-3xl font-bold">Stock Intelligence</h1><p className="mt-2 max-w-3xl text-slate-600">A structured decision-support workspace for short-term research. It does not execute trades, predict guaranteed returns, or replace your own risk management.</p></header>

        <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm"><div className="flex flex-col gap-3 md:flex-row"><div className="min-w-0 flex-1"><StockSearch value={symbol} onChange={setSymbol} onSelect={(item) => void analyse(item.symbol)} placeholder="Search TCS, Reliance, Infosys..." /></div><button type="button" onClick={() => void analyse()} disabled={loading || !symbol.trim()} className="rounded-lg bg-slate-950 px-5 py-2.5 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">{loading ? "Analysing…" : "Analyse stock"}</button></div>{error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-medium text-red-700">{error}</div>}</section>

        {!result && !loading && !error && <section className="mt-6 rounded-2xl border border-dashed bg-white p-10 text-center shadow-sm"><h2 className="text-xl font-semibold">Start with a stock</h2><p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">Search an Indian equity to review signal, market context, risk/reward, technical evidence and invalidation points.</p></section>}
        {loading && <section className="mt-6 grid gap-4 md:grid-cols-3"><div className="h-36 animate-pulse rounded-2xl border bg-white" /><div className="h-36 animate-pulse rounded-2xl border bg-white" /><div className="h-36 animate-pulse rounded-2xl border bg-white" /></section>}

        {result && analysis && <>
          <section className="mt-6 grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border bg-white p-5 shadow-sm lg:col-span-2"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm text-slate-500">Research signal</p><h2 className="mt-1 text-3xl font-bold">{String(context.symbol ?? symbol)}</h2>{currentPrice != null && <p className="mt-1 text-sm text-slate-500">Current price ₹{number(currentPrice)}</p>}</div><span className={`rounded-full px-4 py-2 text-sm font-bold ${signalClass}`}>{signal}</span></div><p className="mt-5 text-lg font-semibold">{analysis.summary}</p><div className="mt-5 grid gap-3 sm:grid-cols-4"><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Confidence</p><p className="mt-1 text-2xl font-bold">{number(analysis.confidence, 0)}%</p></div><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Risk</p><p className="mt-1 text-xl font-bold">{label(analysis.risk_level)}</p></div><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Data quality</p><p className="mt-1 text-sm font-bold">{analysis.data_quality || "—"}</p></div><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Updated</p><p className="mt-1 text-sm font-bold">{analysis.generated_at ? new Date(analysis.generated_at).toLocaleString() : "—"}</p></div></div></div>
            <div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Trade plan levels</h3><dl className="mt-4 space-y-4 text-sm"><div className="flex justify-between gap-4"><dt className="text-slate-500">Entry</dt><dd className="font-bold">₹{number(analysis.entry_price)}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Target</dt><dd className="font-bold">₹{number(analysis.target_price)}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Stop loss</dt><dd className="font-bold">₹{number(analysis.stop_loss)}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Risk / reward</dt><dd className="font-bold">{number(analysis.risk_reward)}</dd></div></dl><p className="mt-5 text-xs text-slate-500">Treat these as research levels only. Position sizing and final risk limits remain with you.</p></div>
          </section>

          <section className="mt-4 grid gap-4 lg:grid-cols-3"><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Market context</h3><p className="mt-3 text-sm leading-6">{analysis.market_view || "No market view returned."}</p></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">What is working</h3><ul className="mt-3 space-y-2 text-sm">{list(analysis.opportunities).map((x) => <li key={x} className="rounded-lg bg-emerald-50 p-3">{x}</li>)}</ul></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Key risks</h3><ul className="mt-3 space-y-2 text-sm">{list(analysis.risks).map((x) => <li key={x} className="rounded-lg bg-red-50 p-3">{x}</li>)}</ul></div></section>

          <section className="mt-4 grid gap-4 lg:grid-cols-2"><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Technical evidence</h3><div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">{Object.entries(indicators).length ? Object.entries(indicators).map(([key, value]) => <div key={key} className="rounded-lg border p-3"><p className="truncate text-xs capitalize text-slate-500">{label(key)}</p><p className="mt-1 font-semibold">{typeof value === "number" ? number(value) : String(value ?? "—")}</p></div>) : <p className="text-sm text-slate-500">No indicator snapshot returned.</p>}</div></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Why this signal?</h3><ul className="mt-3 space-y-2 text-sm">{list(analysis.reasons).map((x) => <li key={x} className="rounded-lg bg-slate-50 p-3">{x}</li>)}</ul></div></section>

          <section className="mt-4 grid gap-4 lg:grid-cols-2"><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">What could invalidate the idea?</h3><ul className="mt-3 space-y-2 text-sm">{list(analysis.limitations, "No explicit invalidation conditions returned.").map((x) => <li key={x} className="rounded-lg border-l-4 border-slate-300 bg-slate-50 p-3">{x}</li>)}</ul></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">What to watch next</h3><ul className="mt-3 space-y-2 text-sm">{list(analysis.watch_items).map((x) => <li key={x} className="rounded-lg bg-amber-50 p-3">{x}</li>)}</ul></div></section>

          <section className="mt-4 rounded-2xl border border-slate-200 bg-slate-100 p-5"><h3 className="font-semibold">Research quality & limitations</h3><p className="mt-2 text-sm text-slate-600">{analysis.data_quality || "Data quality information was not returned."}</p>{analysis.limitations?.length ? <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{analysis.limitations.map((x) => <li key={x}>{x}</li>)}</ul> : null}</section>
        </>}
      </div>
    </main>
  );
}
