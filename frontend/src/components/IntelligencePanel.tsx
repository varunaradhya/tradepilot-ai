import { useEffect, useState } from "react";

import { getAdvancedAnalytics, getPortfolioIntelligence, getReconciliation, getStockIntelligence, type AdvancedAnalytics, type IntelligenceResponse, type ReconciliationResponse } from "../services/intelligence";

export function IntelligencePanel() {
  const [analytics, setAnalytics] = useState<AdvancedAnalytics | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconciliationResponse | null>(null);
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<IntelligenceResponse | null>(null);
  const [stockAnalysis, setStockAnalysis] = useState<IntelligenceResponse | null>(null);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void Promise.all([getAdvancedAnalytics(), getReconciliation(), getPortfolioIntelligence()])
      .then(([risk, broker, analysis]) => { setAnalytics(risk); setReconciliation(broker); setPortfolioAnalysis(analysis); })
      .catch(() => setError("Intelligence data is unavailable. Please try again later."))
      .finally(() => setLoading(false));
  }, []);

  async function loadStockAnalysis() {
    const requestedSymbol = symbol.trim().toUpperCase();
    if (!requestedSymbol) return;
    try {
      setError("");
      setStockAnalysis(await getStockIntelligence(requestedSymbol));
    } catch {
      setError("Stock analysis is unavailable. Check the symbol and try again.");
    }
  }

  return <section className="mt-8 grid gap-4 lg:grid-cols-2">
    <div className="rounded-xl border bg-white p-5"><h2 className="text-xl font-semibold">Portfolio risk</h2>{analytics ? <p className="mt-3 text-sm">{analytics.risk_summary} · Concentration {analytics.concentration_percent.toFixed(1)}% · Diversification {analytics.diversification_score.toFixed(1)}</p> : <p className="mt-3 text-sm text-slate-500">Loading risk analytics…</p>}</div>
    <div className="rounded-xl border bg-white p-5"><h2 className="text-xl font-semibold">Reconciliation</h2>{reconciliation ? <p className="mt-3 text-sm">{reconciliation.summary.matched} matched, {reconciliation.summary.quantity_mismatches} quantity differences.</p> : <p className="mt-3 text-sm text-slate-500">No broker reconciliation available.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">AI Portfolio View</h2><p className="mt-1 text-xs text-slate-500">AI-generated analysis — informational only. It does not place trades or guarantee outcomes.</p>{loading ? <p className="mt-3 text-sm text-slate-500">Preparing advisory analysis…</p> : portfolioAnalysis ? <div className="mt-3 text-sm"><p><strong>{portfolioAnalysis.analysis.signal}</strong> · Confidence {portfolioAnalysis.analysis.confidence}%</p><p className="mt-2">{portfolioAnalysis.analysis.summary}</p><p className="mt-2"><strong>Why:</strong> {portfolioAnalysis.analysis.reasons.join(" ") || "No supporting data available."}</p><p className="mt-2"><strong>Risks:</strong> {portfolioAnalysis.analysis.risks.join(" ") || "No specific risks identified from available data."}</p><p className="mt-2"><strong>Opportunities:</strong> {portfolioAnalysis.analysis.opportunities.join(" ") || "No specific opportunities identified from available data."}</p><p className="mt-2"><strong>Watch:</strong> {portfolioAnalysis.analysis.watch_items.join(", ") || "No holdings require special attention."}</p></div> : <p className="mt-3 text-sm text-slate-500">Advisory analysis is currently unavailable.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">Analyze Stock</h2><div className="mt-3 flex gap-2"><input className="rounded border px-3 py-2" placeholder="TCS" value={symbol} onChange={(event) => setSymbol(event.target.value)} /><button className="rounded bg-slate-900 px-4 py-2 text-white" onClick={() => void loadStockAnalysis()} type="button">Analyze Stock</button></div>{stockAnalysis && <div className="mt-4 text-sm"><strong>{String(stockAnalysis.context_summary.symbol)}: {stockAnalysis.analysis.signal}</strong> ({stockAnalysis.analysis.confidence}%)<p className="mt-1">{stockAnalysis.analysis.summary}</p><p className="mt-1"><strong>Why:</strong> {stockAnalysis.analysis.reasons.join(" ")}</p><p className="mt-1"><strong>Risks:</strong> {stockAnalysis.analysis.risks.join(" ")}</p><p className="mt-1"><strong>Watch:</strong> {stockAnalysis.analysis.watch_items.join(", ") || "No additional watch items."}</p></div>}{error && <p className="mt-3 text-sm text-red-600">{error}</p>}</div>
  </section>;
}
