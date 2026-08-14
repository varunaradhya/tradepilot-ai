import { useEffect, useState } from "react";

import { getAdvancedAnalytics, getAnalysisHistory, getDailyBriefing, getOpportunities, getPortfolioIntelligence, getReconciliation, getStockIntelligence, getTradingView, type AdvancedAnalytics, type DailyBriefing, type HistoryItem, type IntelligenceResponse, type OpportunityResponse, type ReconciliationResponse, type TradingViewResponse } from "../services/intelligence";
import { getAlerts, markAlertRead, markAllAlertsRead, type AlertItem } from "../services/alerts";

export function IntelligencePanel() {
  const [analytics, setAnalytics] = useState<AdvancedAnalytics | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconciliationResponse | null>(null);
  const [portfolio, setPortfolio] = useState<IntelligenceResponse | null>(null);
  const [opportunities, setOpportunities] = useState<OpportunityResponse | null>(null);
  const [tradingView, setTradingView] = useState<TradingViewResponse | null>(null);
  const [stock, setStock] = useState<IntelligenceResponse | null>(null);
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.allSettled([getAdvancedAnalytics(), getReconciliation(), getPortfolioIntelligence(), getOpportunities(), getTradingView(), getDailyBriefing(), getAnalysisHistory(), getAlerts()]).then((results) => {
      const [risk, broker, analysis, scanner, trading, daily, analysisHistory, alertItems] = results;
      if (risk.status === "fulfilled") setAnalytics(risk.value);
      if (broker.status === "fulfilled") setReconciliation(broker.value);
      if (analysis.status === "fulfilled") setPortfolio(analysis.value);
      if (scanner.status === "fulfilled") setOpportunities(scanner.value);
      if (trading.status === "fulfilled") setTradingView(trading.value);
      if (daily.status === "fulfilled") setBriefing(daily.value);
      if (analysisHistory.status === "fulfilled") setHistory(analysisHistory.value);
      if (alertItems.status === "fulfilled") setAlerts(alertItems.value);
      if (results.some((result) => result.status === "rejected")) setError("Some intelligence data is unavailable. Other dashboard sections remain available.");
    });
  }, []);

  async function analyseStock(requestedSymbol = symbol.trim().toUpperCase()) {
    if (!requestedSymbol) return;
    try { setError(""); setSymbol(requestedSymbol); setStock(await getStockIntelligence(requestedSymbol)); }
    catch { setError("Stock analysis is unavailable. Check the symbol and try again."); }
  }

  async function readAllAlerts() { await markAllAlertsRead(); setAlerts((items) => items.map((item) => ({ ...item, is_read: true }))); }
  async function readAlert(id: number) { await markAlertRead(id); setAlerts((items) => items.map((item) => item.id === id ? { ...item, is_read: true } : item)); }

  return <section className="mt-8 grid gap-4 lg:grid-cols-2">
    <div className="rounded-xl border bg-white p-5"><h2 className="text-xl font-semibold">Portfolio risk</h2>{analytics ? <p className="mt-3 text-sm">{analytics.risk_summary} · Concentration {analytics.concentration_percent.toFixed(1)}% · Diversification {analytics.diversification_score.toFixed(1)}</p> : <p className="mt-3 text-sm text-slate-500">Risk analytics are unavailable.</p>}</div>
    <div className="rounded-xl border bg-white p-5"><h2 className="text-xl font-semibold">Reconciliation</h2>{reconciliation ? <p className="mt-3 text-sm">{reconciliation.summary.matched} matched, {reconciliation.summary.quantity_mismatches} quantity differences.</p> : <p className="mt-3 text-sm text-slate-500">No broker reconciliation available.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">AI Portfolio Analysis</h2><p className="mt-1 text-xs text-slate-500">AI-generated analysis — informational only. It never executes trades or guarantees outcomes.</p>{portfolio ? <div className="mt-3 text-sm"><p><strong>{portfolio.analysis.signal}</strong> · Confidence {portfolio.analysis.confidence}%</p><p className="mt-2">{portfolio.analysis.summary}</p><p className="mt-2"><strong>Risks:</strong> {portfolio.analysis.risks.join(" ") || "No specific risks identified."}</p><p className="mt-2"><strong>Opportunities:</strong> {portfolio.analysis.opportunities.join(" ") || "No specific opportunities identified."}</p></div> : <p className="mt-3 text-sm text-slate-500">Preparing advisory portfolio analysis…</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">AI Daily Briefing</h2>{briefing ? <div className="mt-3 text-sm"><p>{briefing.headline}</p><p className="mt-2">{briefing.portfolio_summary}</p><p className="mt-2"><strong>Risk:</strong> {briefing.risk_summary}</p><p className="mt-2"><strong>Watch:</strong> {briefing.watch_items.join(", ") || "No priority watch items."}</p></div> : <p className="mt-3 text-sm text-slate-500">Daily briefing is unavailable.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">Stock Analysis</h2><div className="mt-3 flex gap-2"><input className="rounded border px-3 py-2" placeholder="TCS" value={symbol} onChange={(event) => setSymbol(event.target.value)} /><button className="rounded bg-slate-900 px-4 py-2 text-white" onClick={() => void analyseStock()} type="button">Analyze Stock</button></div>{stock && <div className="mt-4 text-sm"><strong>{String(stock.context_summary.symbol)}: {stock.analysis.signal}</strong> · {stock.analysis.confidence}%<p className="mt-1">{stock.analysis.summary}</p><p className="mt-1"><strong>Why:</strong> {stock.analysis.reasons.join(" ")}</p><p className="mt-1"><strong>Limitations:</strong> {stock.analysis.limitations.join(" ")}</p></div>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">Opportunity Scanner</h2>{opportunities?.opportunities.length ? <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-slate-500"><tr><th>Symbol</th><th>Score</th><th>Signal</th><th>Reason</th><th>Risk</th></tr></thead><tbody>{opportunities.opportunities.map((item) => <tr className="border-t" key={item.symbol}><td className="py-2"><button className="font-semibold underline" type="button" onClick={() => void analyseStock(item.symbol)}>{item.symbol}</button></td><td>{item.score}</td><td>{item.signal}</td><td>{item.reasons[0]}</td><td>{item.risks[0] ?? "—"}</td></tr>)}</tbody></table></div> : <p className="mt-3 text-sm text-slate-500">No symbols with sufficient technical data are available to scan.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">Short-Term Trading View</h2>{tradingView ? <div className="mt-3 text-sm"><p>Potential setups: {tradingView.market_candidates.length} · BUY {tradingView.buy_candidates.length} · HOLD {tradingView.hold_candidates.length} · SELL {tradingView.sell_candidates.length}</p><p className="mt-2">Strongest momentum: {tradingView.strongest_momentum?.symbol ?? "No available candidate"}. Highest risk: {tradingView.highest_risk?.symbol ?? "No available candidate"}.</p><p className="mt-2 text-slate-500">{tradingView.disclaimer}</p></div> : <p className="mt-3 text-sm text-slate-500">Trading view is unavailable.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Alerts ({alerts.filter((item) => !item.is_read).length})</h2><button className="text-sm underline" type="button" onClick={() => void readAllAlerts()}>Mark all read</button></div>{alerts.length ? <div className="mt-3 space-y-2 text-sm">{alerts.map((item) => <button className="block w-full rounded border p-3 text-left" key={item.id} onClick={() => void readAlert(item.id)} type="button"><strong>{item.severity}{item.symbol ? ` · ${item.symbol}` : ""}</strong><p>{item.message}</p><span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()} {item.is_read ? "· Read" : "· Unread"}</span></button>)}</div> : <p className="mt-3 text-sm text-slate-500">No alerts right now.</p>}</div>
    <div className="rounded-xl border bg-white p-5 lg:col-span-2"><h2 className="text-xl font-semibold">AI History</h2>{history.length ? <div className="mt-3 space-y-2 text-sm">{history.map((item) => <button className="block w-full rounded border p-3 text-left" key={item.id} onClick={() => item.symbol && void analyseStock(item.symbol)} type="button"><strong>{item.symbol ?? "Portfolio"} · {item.signal} ({item.confidence}%)</strong><p>{item.analysis_type} · {item.summary}</p><span className="text-xs text-slate-500">{new Date(item.generated_at).toLocaleString()}</span></button>)}</div> : <p className="mt-3 text-sm text-slate-500">No AI analyses have been stored yet.</p>}</div>
    {error && <p className="text-sm text-red-600 lg:col-span-2">{error}</p>}
  </section>;
}
