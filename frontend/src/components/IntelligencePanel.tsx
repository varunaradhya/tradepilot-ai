import { useEffect, useState } from "react";

import { getAdvancedAnalytics, getReconciliation, getTechnicalSignal, type AdvancedAnalytics, type ReconciliationResponse, type SignalResponse } from "../services/intelligence";

export function IntelligencePanel() {
  const [analytics, setAnalytics] = useState<AdvancedAnalytics | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconciliationResponse | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { void Promise.all([getAdvancedAnalytics(), getReconciliation()]).then(([a, r]) => { setAnalytics(a); setReconciliation(r); }).catch(() => setError("Intelligence data is unavailable.")); }, []);
  async function loadSignal() { if (!symbol.trim()) return; try { setSignal(await getTechnicalSignal(symbol)); } catch { setError("Technical signal is unavailable."); } }

  return <section className="mt-8 grid gap-4 lg:grid-cols-2">
    <div className="rounded-xl border bg-white p-5"><h2 className="text-xl font-semibold">Portfolio risk</h2>{analytics ? <p className="mt-3 text-sm">{analytics.risk_summary} · Concentration {analytics.concentration_percent.toFixed(1)}% · Diversification {analytics.diversification_score.toFixed(1)}</p> : <p className="mt-3 text-sm text-slate-500">Loading risk analytics…</p>}</div>
    <div className="rounded-xl border bg-white p-5"><h2 className="text-xl font-semibold">Reconciliation</h2>{reconciliation ? <p className="mt-3 text-sm">{reconciliation.summary.matched} matched, {reconciliation.summary.quantity_mismatches} quantity differences.</p> : <p className="mt-3 text-sm text-slate-500">No broker reconciliation available.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">Technical signal</h2><div className="mt-3 flex gap-2"><input className="rounded border px-3 py-2" placeholder="TCS" value={symbol} onChange={(event) => setSymbol(event.target.value)} /><button className="rounded bg-slate-900 px-4 py-2 text-white" onClick={() => void loadSignal()} type="button">Analyze</button></div>{signal && <div className="mt-4 text-sm"><strong>{signal.symbol}: {signal.signal}</strong> ({signal.confidence.toFixed(0)}%)<p className="mt-1">{signal.reasons.join(" ")}</p><p className="mt-1 text-slate-500">RSI: {String(signal.indicators.rsi ?? "n/a")} · Trend: {String(signal.indicators.trend ?? "n/a")}</p></div>}{error && <p className="mt-3 text-sm text-red-600">{error}</p>}</div>
  </section>;
}
