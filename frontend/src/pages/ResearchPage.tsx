import { useState } from "react";
import StockSearch from "../components/StockSearch";
import { getStockIntelligence, type IntelligenceResponse } from "../services/intelligence";

function number(value: unknown, digits = 2) {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

export default function ResearchPage() {
  const [symbol, setSymbol] = useState("");
  const [result, setResult] = useState<IntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function analyse(requested = symbol.trim().toUpperCase()) {
    if (!requested) return;
    setSymbol(requested);
    setLoading(true);
    setError("");
    try {
      setResult(await getStockIntelligence(requested));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Stock analysis is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  const analysis = result?.analysis;
  const context = result?.context_summary;

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Research</p>
          <h1 className="mt-1 text-3xl font-bold">Stock Intelligence</h1>
          <p className="mt-2 max-w-3xl text-slate-600">A decision-support workspace for short-term research. TradePilot does not execute trades or guarantee outcomes.</p>
        </div>

        <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="min-w-0 flex-1">
              <StockSearch value={symbol} onChange={setSymbol} onSelect={(item) => void analyse(item.symbol)} placeholder="Search TCS, Reliance, Infosys..." />
            </div>
            <button type="button" onClick={() => void analyse()} disabled={loading} className="rounded-lg bg-slate-950 px-5 py-2.5 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
              {loading ? "Analysing…" : "Analyse stock"}
            </button>
          </div>
          {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-medium text-red-700">{error}</div>}
        </section>

        {!result && !loading && !error && (
          <section className="mt-6 rounded-2xl border border-dashed bg-white p-10 text-center shadow-sm">
            <h2 className="text-xl font-semibold">Start with a stock</h2>
            <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">Search an Indian equity to review its current intelligence signal, confidence, reasons, risk and indicator snapshot.</p>
          </section>
        )}

        {loading && <section className="mt-6 grid gap-4 md:grid-cols-3"><div className="h-32 animate-pulse rounded-2xl border bg-white" /><div className="h-32 animate-pulse rounded-2xl border bg-white" /><div className="h-32 animate-pulse rounded-2xl border bg-white" /></section>}

        {result && analysis && (
          <>
            <section className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border bg-white p-5 shadow-sm md:col-span-2">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><p className="text-sm text-slate-500">Research signal</p><h2 className="mt-1 text-3xl font-bold">{String(context?.symbol ?? symbol)}</h2></div>
                  <span className="rounded-full bg-slate-100 px-4 py-2 text-sm font-bold">{analysis.signal}</span>
                </div>
                <p className="mt-5 text-lg font-semibold">{analysis.summary}</p>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Confidence</p><p className="mt-1 text-2xl font-bold">{number(analysis.confidence, 0)}%</p></div>
                  <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Risk</p><p className="mt-1 text-2xl font-bold">{String(analysis.risk_level ?? "—")}</p></div>
                  <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Data status</p><p className="mt-1 text-2xl font-bold">Live</p></div>
                </div>
              </div>
              <div className="rounded-2xl border bg-white p-5 shadow-sm">
                <h3 className="font-semibold">Decision levels</h3>
                <dl className="mt-4 space-y-4 text-sm">
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Entry</dt><dd className="font-bold">₹{number(analysis.entry_price)}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Target</dt><dd className="font-bold">₹{number(analysis.target_price)}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Stop loss</dt><dd className="font-bold">₹{number(analysis.stop_loss)}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-slate-500">Risk / reward</dt><dd className="font-bold">{number(analysis.risk_reward)}</dd></div>
                </dl>
              </div>
            </section>

            <section className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Why this signal?</h3>{analysis.reasons?.length ? <ul className="mt-3 space-y-2 text-sm">{analysis.reasons.map((reason) => <li key={reason} className="rounded-lg bg-slate-50 p-3">{reason}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No explicit reasons returned.</p>}</div>
              <div className="rounded-2xl border bg-white p-5 shadow-sm"><h3 className="font-semibold">Indicator snapshot</h3><div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">{Object.entries(analysis.indicators ?? {}).map(([key, value]) => <div key={key} className="rounded-lg border p-3"><p className="truncate text-xs text-slate-500">{key.replaceAll("_", " ")}</p><p className="mt-1 font-semibold">{typeof value === "number" ? number(value) : String(value ?? "—")}</p></div>)}</div></div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
