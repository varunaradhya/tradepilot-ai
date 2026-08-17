import { useState } from "react";
import { api } from "../services/api";
import ResearchDataPanel from "./ResearchDataPanel";

type Ranking = { symbol: string; score?: number; robustness?: { status?: string }; metrics?: { return_percent?: number; profit_factor?: number; max_drawdown_percent?: number; trades?: number } };
type Evidence = { status: string; interval: string; missing_symbols: string[]; summary: { symbols_tested: number; robust_symbols: number; robust_percent: number; average_return_percent: number; median_profit_factor: number; worst_drawdown_percent: number }; ranking: Ranking[] };

function n(value: unknown) { return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "—"; }

export default function IntradayEvidencePanel() {
  const [symbols, setSymbols] = useState("TCS,INFY,RELIANCE,HDFCBANK,ICICIBANK,SBIN");
  const [interval, setInterval] = useState("5");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Evidence | null>(null);

  async function run() {
    if (!symbols.trim()) return;
    setLoading(true); setError("");
    try {
      const query = new URLSearchParams({ symbols, interval });
      setResult(await api.get<Evidence>(`/research/intraday/evidence?${query.toString()}`));
    } catch (err) { setResult(null); setError(err instanceof Error ? err.message : "Evidence scan failed."); }
    finally { setLoading(false); }
  }

  return <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm">
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Intraday evidence</p><h2 className="mt-1 text-2xl font-bold">Multi-stock strategy scorecard</h2><p className="mt-1 max-w-2xl text-sm text-slate-500">Compare the same fixed strategy across stocks. No per-stock parameter tuning is performed.</p></div>
      <button type="button" onClick={() => void run()} disabled={loading} className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-bold text-white transition hover:-translate-y-0.5 disabled:opacity-50">{loading ? "Scanning…" : "Run evidence scan"}</button>
    </div>
    <div className="mt-4 grid gap-3 md:grid-cols-[1fr_120px]">
      <input value={symbols} onChange={e => setSymbols(e.target.value)} className="rounded-xl border px-4 py-3 text-sm outline-none focus:ring-2" placeholder="TCS, INFY, RELIANCE..." />
      <select value={interval} onChange={e => setInterval(e.target.value)} className="rounded-xl border px-4 py-3 text-sm"><option value="1">1 min</option><option value="5">5 min</option><option value="15">15 min</option><option value="25">25 min</option><option value="60">60 min</option></select>
    </div>
    {error && <div className="mt-3 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>}
    {loading && <div className="mt-5 grid gap-3 md:grid-cols-5">{Array.from({length: 5}, (_, i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-100" />)}</div>}
    {result && !loading && <>
      <div className="mt-5 grid gap-3 md:grid-cols-5">
        {[['Stocks', result.summary.symbols_tested], ['Robust', result.summary.robust_percent + "%"], ['Avg return', result.summary.average_return_percent + "%"], ['Median PF', n(result.summary.median_profit_factor)], ['Worst DD', result.summary.worst_drawdown_percent + "%"]].map(([label, value]) => <div key={String(label)} className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-xl font-bold">{value}</p></div>)}
      </div>
      <ResearchDataPanel missingSymbols={result.missing_symbols} interval={interval} onComplete={() => void run()} />
      <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-wide text-slate-400"><th className="p-3">Rank</th><th className="p-3">Symbol</th><th className="p-3">Status</th><th className="p-3">Score</th><th className="p-3">Return</th><th className="p-3">PF</th><th className="p-3">Drawdown</th></tr></thead><tbody>{result.ranking.map((item, index) => <tr key={item.symbol} className="border-b last:border-0"><td className="p-3 font-bold">#{index + 1}</td><td className="p-3 font-bold">{item.symbol}</td><td className="p-3"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${item.robustness?.status === "ROBUST" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{item.robustness?.status ?? "REVIEW"}</span></td><td className="p-3">{n(item.score)}</td><td className="p-3">{n(item.metrics?.return_percent)}%</td><td className="p-3">{n(item.metrics?.profit_factor)}</td><td className="p-3">{n(item.metrics?.max_drawdown_percent)}%</td></tr>)}</tbody></table></div>
    </>}
  </section>;
}
