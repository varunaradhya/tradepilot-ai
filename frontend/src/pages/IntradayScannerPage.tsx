import { useMemo, useState } from "react";
import { apiRequest } from "../services/api";
import ResearchDataPanel from "../components/ResearchDataPanel";
import StockMultiSelect from "../components/StockMultiSelect";
import type { StockInstrument } from "../components/StockSearch";

type Row = { symbol: string; score: number; robustness: { status: string; reasons: string[] }; metrics: Record<string, unknown> };
type Response = { status: string; interval: string; missing_datasets: string[]; assumptions: Record<string, unknown>; ranked: Row[] };
type Filter = "ALL" | "ROBUST" | "POSITIVE" | "HIGH_PF";

const DEFAULT_SYMBOLS = [
  { symbol: "TCS", name: "Tata Consultancy Services", exchange: "NSE", security_id: "11536", exchange_segment: "NSE_EQ" },
  { symbol: "INFY", name: "Infosys", exchange: "NSE", security_id: "1594", exchange_segment: "NSE_EQ" },
  { symbol: "RELIANCE", name: "Reliance Industries", exchange: "NSE", security_id: "2885", exchange_segment: "NSE_EQ" },
  { symbol: "HDFCBANK", name: "HDFC Bank", exchange: "NSE", security_id: "1333", exchange_segment: "NSE_EQ" },
  { symbol: "ICICIBANK", name: "ICICI Bank", exchange: "NSE", security_id: "1330", exchange_segment: "NSE_EQ" },
  { symbol: "SBIN", name: "State Bank of India", exchange: "NSE", security_id: "3045", exchange_segment: "NSE_EQ" },
] as StockInstrument[];

function num(v: unknown) { return typeof v === "number" ? v : null; }

export default function IntradayScannerPage() {
  const [stocks, setStocks] = useState<StockInstrument[]>(DEFAULT_SYMBOLS);
  const [interval, setInterval] = useState("5");
  const [filter, setFilter] = useState<Filter>("ALL");
  const [result, setResult] = useState<Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function scan() {
    if (!stocks.length) { setError("Add at least one NSE stock from the suggestions before scanning."); return; }
    setLoading(true); setError("");
    try {
      const symbols = stocks.map((item) => item.symbol).join(",");
      setResult(await apiRequest<Response>(`/research/intraday/scorecard?symbols=${encodeURIComponent(symbols)}&interval=${interval}`));
    } catch (e) { setResult(null); setError(e instanceof Error ? e.message : "Scanner unavailable."); }
    finally { setLoading(false); }
  }

  const ranked = useMemo(() => {
    if (!result) return [];
    return result.ranked.filter((row) => filter === "ALL" || (filter === "ROBUST" && row.robustness.status === "ROBUST") || (filter === "POSITIVE" && (num(row.metrics.return_percent) ?? -Infinity) > 0) || (filter === "HIGH_PF" && (num(row.metrics.profit_factor) ?? 0) >= 1.2));
  }, [result, filter]);

  return <main className="tp-page">
    <header className="flex flex-wrap items-end justify-between gap-5"><div><div className="tp-live-line">NSE opportunity radar</div><h1 className="tp-page-title mt-2 text-4xl font-black">Opportunity Scanner</h1><p className="tp-page-subtitle mt-2 max-w-2xl text-sm">Ranks stored NSE datasets using fixed assumptions. It does not optimize the strategy or place orders.</p></div><div className="flex gap-2"><select value={interval} onChange={(e) => { setInterval(e.target.value); setResult(null); }} className="rounded-xl border px-3 py-2 text-xs font-bold"><option value="5">5 min</option><option value="15">15 min</option><option value="1">1 min</option><option value="25">25 min</option><option value="60">60 min</option></select><button type="button" onClick={() => void scan()} disabled={loading || !stocks.length} className="rounded-xl bg-violet-500 px-5 py-2.5 text-xs font-black text-white disabled:opacity-60">{loading ? "Scanning…" : "Scan NSE →"}</button></div></header>
    <section className="tp-premium-card mt-6 rounded-2xl p-5"><div className="flex items-center justify-between"><div><p className="tp-section-label">Research basket</p><h2 className="mt-1 text-lg font-black text-white">Symbols under observation</h2></div><span className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Fixed parameters · no optimization</span></div><div className="mt-4"><StockMultiSelect value={stocks} onChange={(items) => { setStocks(items); setResult(null); }} maxItems={20} /></div><p className="mt-2 text-xs text-slate-600">Only backend-verified NSE instruments can enter the basket. This prevents company-name/symbol typos from reaching the research API.</p></section>
    {error && <div className="mt-4 rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm font-medium text-red-200">{error}</div>}
    {loading && <div className="tp-premium-card mt-6 h-64 animate-pulse rounded-2xl" />}
    {result && <>
      <section className="mt-6 grid gap-4 sm:grid-cols-3">{[["TESTED", result.ranked.length], ["ROBUST", result.ranked.filter((x) => x.robustness.status === "ROBUST").length], ["MISSING", result.missing_datasets.length]].map(([label, value]) => <article key={String(label)} className="tp-kpi"><p className="tp-section-label">{label}</p><p className="tp-number mt-2 text-3xl font-black text-white">{value}</p></article>)}</section>
      <ResearchDataPanel missingSymbols={result.missing_datasets} interval={interval} onComplete={() => void scan()} />
      <section className="tp-premium-card mt-5 overflow-hidden rounded-2xl"><div className="flex flex-wrap items-end justify-between gap-3 border-b border-white/10 p-5"><div><p className="tp-section-label">Opportunity radar</p><h2 className="mt-1 text-xl font-black text-white">Strongest evidence first</h2></div><div className="flex flex-wrap gap-1 rounded-xl bg-white/[.03] p-1">{(["ALL", "ROBUST", "POSITIVE", "HIGH_PF"] as Filter[]).map((item) => <button key={item} type="button" onClick={() => setFilter(item)} className={`rounded-lg px-3 py-1.5 text-[10px] font-black ${filter === item ? "bg-violet-500/20 text-violet-200" : "text-slate-600 hover:text-white"}`}>{item === "HIGH_PF" ? "HIGH PF" : item}</button>)}</div></div>
        <div className="divide-y divide-white/5">{ranked.length === 0 ? <div className="p-10 text-center text-sm text-slate-500">No candidates match this filter.</div> : ranked.map((row, i) => { const score = Math.max(0, Math.min(100, row.score)); const positive = (num(row.metrics.return_percent) ?? 0) >= 0; return <div key={row.symbol} className="grid gap-4 p-5 transition hover:bg-violet-400/[.025] md:grid-cols-[44px_1fr_150px] md:items-center"><div className="text-sm font-black text-slate-600">{String(i + 1).padStart(2, "0")}</div><div><div className="flex flex-wrap items-center gap-2"><span className="text-lg font-black text-white">{row.symbol}</span><span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${row.robustness.status === "ROBUST" ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-400/10 text-amber-300"}`}>{row.robustness.status}</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-teal-400 transition-all duration-700" style={{ width: `${score}%` }} /></div><div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-slate-600"><span>PF <b className="text-slate-300">{num(row.metrics.profit_factor)?.toFixed(2) ?? "—"}</b></span><span>Win <b className="text-slate-300">{num(row.metrics.win_rate_percent)?.toFixed(1) ?? "—"}%</b></span><span>Return <b className={positive ? "text-emerald-300" : "text-rose-300"}>{num(row.metrics.return_percent)?.toFixed(1) ?? "—"}%</b></span><span>DD <b className="text-slate-300">{num(row.metrics.max_drawdown_percent)?.toFixed(1) ?? "—"}%</b></span></div>{row.robustness.reasons.length > 0 && <p className="mt-2 text-[10px] text-amber-300">{row.robustness.reasons.join(" • ")}</p>}</div><div className="text-right"><p className="tp-section-label">Score</p><p className="tp-number text-3xl font-black text-white">{row.score.toFixed(0)}</p><p className="text-[10px] text-slate-600">evidence score</p></div></div>; })}</div></section>
      <div className="mt-5 rounded-xl border border-white/5 bg-white/[.02] p-4 text-xs text-slate-500"><b className="text-slate-300">Research boundary:</b> this scanner ranks evidence; it does not optimize parameters or authorize live execution.</div>
    </>}
  </main>;
}
