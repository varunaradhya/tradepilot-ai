import { useState } from "react";
import { api } from "../services/api";

type Report = {
  status: string;
  symbols: string[];
  progress: { required_sessions: number; completed_sessions: number; remaining_sessions: number; complete: boolean };
  symbol_evidence: Array<{ date: string; symbol: string; status: string; bars: number; trades: number; net_pnl: number }>;
};

export default function MultiSymbolValidationPanel() {
  const [start, setStart] = useState(() => new Date().toISOString().slice(0, 10));
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setReport(await api.get<Report>(`/paper-validation/report?start=${encodeURIComponent(start)}`)); }
    catch (err) { setReport(null); setError(err instanceof Error ? err.message : "Paper validation evidence is unavailable."); }
    finally { setLoading(false); }
  }

  return <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><h2 className="font-semibold">30-session multi-stock validation</h2><p className="mt-1 text-sm text-slate-500">Descriptive paper evidence across a controlled NSE equity universe. This panel does not rank symbols or approve live execution.</p></div>
      <div className="flex gap-2"><input aria-label="Validation start date" type="date" value={start} onChange={e => setStart(e.target.value)} className="rounded-lg border px-3 py-2 text-sm" /><button type="button" onClick={() => void load()} disabled={loading || !start} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{loading ? "Loading…" : "Load evidence"}</button></div>
    </div>
    {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {report && <><div className="mt-4 grid gap-3 sm:grid-cols-4">{[
      ["Status", report.status], ["Symbols", String(report.symbols.length)], ["Completed sessions", `${report.progress.completed_sessions}/${report.progress.required_sessions}`], ["Remaining", String(report.progress.remaining_sessions)]
    ].map(([key, value]) => <div key={key} className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{key}</p><p className="mt-1 font-bold">{value}</p></div>)}</div>
    <div className="mt-4 flex flex-wrap gap-2">{report.symbols.map(symbol => <span key={symbol} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold">{symbol}</span>)}</div>
    {report.symbol_evidence.length > 0 && <div className="mt-4 overflow-x-auto"><table className="min-w-full text-left text-sm"><thead><tr className="border-b text-xs uppercase text-slate-500"><th className="px-3 py-2">Date</th><th className="px-3 py-2">Symbol</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Bars</th><th className="px-3 py-2">Trades</th><th className="px-3 py-2">Net P&L</th></tr></thead><tbody>{report.symbol_evidence.slice(-20).map((row, index) => <tr key={`${row.date}-${row.symbol}-${index}`} className="border-b last:border-0"><td className="px-3 py-2">{row.date}</td><td className="px-3 py-2 font-semibold">{row.symbol}</td><td className="px-3 py-2">{row.status}</td><td className="px-3 py-2">{row.bars}</td><td className="px-3 py-2">{row.trades}</td><td className="px-3 py-2">{Number(row.net_pnl).toFixed(2)}</td></tr>)}</tbody></table></div>}</>}
  </section>;
}
