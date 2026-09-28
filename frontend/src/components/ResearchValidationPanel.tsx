import { useState } from "react";
import { api } from "../services/api";

type Quality = { valid: boolean; bars: number; sessions: number; duplicates: number; invalid_ohlc: number; non_chronological: number; missing_volume: number; message: string };
type Walk = { windows: number; v1: { summary: { total_validation_trades: number; average_return_percent: number; worst_return_percent: number; max_drawdown_percent: number } }; v2: { summary: { total_validation_trades: number; average_return_percent: number; worst_return_percent: number; max_drawdown_percent: number } } };

export default function ResearchValidationPanel({ symbol, interval }: { symbol: string; interval: string }) {
  const [quality, setQuality] = useState<Quality | null>(null);
  const [walk, setWalk] = useState<Walk | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function run() {
    if (!symbol.trim()) return;
    setLoading(true); setError("");
    try {
      const q = await api.get<Quality>(`/research/intraday/data-quality?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}`);
      const w = await api.get<Walk>(`/research/intraday/walk-forward?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}`);
      setQuality(q); setWalk(w);
    } catch (err) { setError(err instanceof Error ? err.message : "Research validation is unavailable."); } finally { setLoading(false); }
  }
  return <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">Research validation</h2><p className="mt-1 text-sm text-slate-500">Data-quality checks and chronological out-of-sample evidence. No automatic strategy winner is selected.</p></div><button type="button" onClick={() => void run()} disabled={loading || !symbol.trim()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{loading ? "Validating…" : "Validate dataset"}</button></div>
    {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {quality && <div className="mt-4 grid gap-3 sm:grid-cols-4">
      <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Data status</p><p className="mt-1 font-bold">{quality.valid ? "VALID" : "REVIEW"}</p></div>
      <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Bars / sessions</p><p className="mt-1 font-bold">{quality.bars} / {quality.sessions}</p></div>
      <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Duplicates / bad OHLC</p><p className="mt-1 font-bold">{quality.duplicates} / {quality.invalid_ohlc}</p></div>
      <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Chronology issues</p><p className="mt-1 font-bold">{quality.non_chronological}</p></div>
    </div>}
    {walk && <div className="mt-4 grid gap-3 md:grid-cols-2">{(["V1", "V2"] as const).map(name => { const value = walk[name.toLowerCase() as "v1" | "v2"]; return <div key={name} className="rounded-xl border p-4"><p className="font-semibold">{name} walk-forward</p><div className="mt-3 grid grid-cols-2 gap-2 text-sm"><span>Windows: <b>{walk.windows}</b></span><span>Trades: <b>{value.summary.total_validation_trades}</b></span><span>Avg return: <b>{value.summary.average_return_percent}%</b></span><span>Worst return: <b>{value.summary.worst_return_percent}%</b></span><span>Max DD: <b>{value.summary.max_drawdown_percent}%</b></span></div></div>; })}</div>}
  </section>;
}