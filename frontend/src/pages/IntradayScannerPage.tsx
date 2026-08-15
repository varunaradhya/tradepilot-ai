import { useState } from "react";
import { apiRequest } from "../services/api";

type Row = { symbol:string; score:number; robustness:{status:string;reasons:string[]}; metrics:Record<string,unknown> };
type Response = { status:string; interval:string; missing_datasets:string[]; assumptions:Record<string,unknown>; ranked:Row[] };
function n(v: unknown, digits=2) { return typeof v === "number" ? v.toFixed(digits) : "—"; }

export default function IntradayScannerPage() {
  const [symbols,setSymbols] = useState("TCS,INFY,RELIANCE,HDFCBANK,ICICIBANK,SBIN");
  const [interval,setInterval] = useState("5");
  const [result,setResult] = useState<Response|null>(null);
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState("");
  async function scan() {
    setLoading(true); setError("");
    try { setResult(await apiRequest<Response>(`/research/intraday/scorecard?symbols=${encodeURIComponent(symbols)}&interval=${interval}`)); }
    catch (e) { setResult(null); setError(e instanceof Error ? e.message : "Scanner unavailable."); }
    finally { setLoading(false); }
  }
  return <main className="min-h-screen bg-slate-50 p-6 text-slate-900"><div className="mx-auto max-w-7xl">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-wider text-slate-500">Intraday</p><h1 className="text-3xl font-bold">Opportunity Scanner</h1><p className="mt-2 text-slate-600">Ranks stored NSE datasets using fixed assumptions. It does not optimize the strategy or place orders.</p></div><div className="flex gap-2"><select value={interval} onChange={e=>setInterval(e.target.value)} className="rounded-lg border bg-white px-3 py-2"><option value="5">5 min</option><option value="15">15 min</option><option value="1">1 min</option><option value="25">25 min</option><option value="60">60 min</option></select><button onClick={()=>void scan()} disabled={loading} className="rounded-lg bg-slate-950 px-5 py-2 font-semibold text-white disabled:opacity-60">{loading?"Scanning…":"Scan NSE"}</button></div></div>
    <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm"><label className="text-sm font-semibold">Symbols</label><textarea value={symbols} onChange={e=>setSymbols(e.target.value)} className="mt-2 h-20 w-full rounded-xl border p-3 text-sm outline-none focus:ring-2 focus:ring-slate-300" placeholder="TCS,INFY,RELIANCE,HDFCBANK" /><p className="mt-2 text-xs text-slate-500">Only downloaded datasets are evaluated. Missing symbols are reported, not silently ignored.</p></section>
    {error && <div className="mt-4 rounded-xl bg-red-50 p-4 text-sm font-medium text-red-700">{error}</div>}
    {loading && <div className="mt-6 h-64 animate-pulse rounded-2xl border bg-white" />}
    {result && <><section className="mt-6 grid gap-4 sm:grid-cols-3"><div className="rounded-2xl border bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">Tested</p><p className="mt-1 text-3xl font-bold">{result.ranked.length}</p></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">Robust candidates</p><p className="mt-1 text-3xl font-bold">{result.ranked.filter(x=>x.robustness.status==="ROBUST").length}</p></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">Missing datasets</p><p className="mt-1 text-3xl font-bold">{result.missing_datasets.length}</p></div></section>
    <section className="mt-4 overflow-hidden rounded-2xl border bg-white shadow-sm"><div className="border-b p-5"><h2 className="font-semibold">Evidence ranking</h2><p className="mt-1 text-xs text-slate-500">Fixed 0.10% slippage assumption • no parameter selection</p></div><div className="divide-y">{result.ranked.map((row,i)=><div key={row.symbol} className="grid gap-4 p-5 md:grid-cols-[48px_1fr_auto] md:items-center"><div className="text-lg font-bold text-slate-400">#{i+1}</div><div><div className="flex flex-wrap items-center gap-2"><span className="text-lg font-bold">{row.symbol}</span><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${row.robustness.status==="ROBUST"?"bg-emerald-50 text-emerald-700":"bg-amber-50 text-amber-700"}`}>{row.robustness.status}</span></div><div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600"><span>PF <b>{n(row.metrics.profit_factor)}</b></span><span>Win <b>{n(row.metrics.win_rate_percent,1)}%</b></span><span>Return <b>{n(row.metrics.return_percent,1)}%</b></span><span>Trades <b>{String(row.metrics.trades ?? "—")}</b></span><span>DD <b>{n(row.metrics.max_drawdown_percent,1)}%</b></span></div>{row.robustness.reasons.length>0&&<p className="mt-2 text-xs text-amber-700">{row.robustness.reasons.join(" • ")}</p>}</div><div className="text-right"><p className="text-xs text-slate-500">Robustness</p><p className="text-2xl font-bold">{n(row.score,0)}</p></div></div>)}</div></section>
    {result.missing_datasets.length>0&&<section className="mt-4 rounded-2xl border bg-white p-5"><h3 className="font-semibold">Data still required</h3><p className="mt-2 text-sm text-slate-500">{result.missing_datasets.join(", ")}</p></section>}</>}
  </div></main>;
}
