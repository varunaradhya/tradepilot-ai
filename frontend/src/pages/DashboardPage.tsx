import { useEffect, useState } from "react";

import { IntelligencePanel } from "../components/IntelligencePanel";
import StockSearch from "../components/StockSearch";
import { getPortfolioAnalytics, type PortfolioAnalytics } from "../services/analytics";
import { addWatchlistSymbol, deleteWatchlistSymbol, getWatchlistQuotes, type WatchlistQuote } from "../services/watchlist";

type DashboardPageProps = { onLogout: () => void; onTransactions: () => void };

function money(value: number) { return value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function DashboardPage({ onLogout, onTransactions }: DashboardPageProps) {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistQuote[]>([]);
  const [newSymbol, setNewSymbol] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    try {
      setLoading(true); setError("");
      const [analyticsData, watchlistData] = await Promise.all([getPortfolioAnalytics(), getWatchlistQuotes()]);
      setAnalytics(analyticsData); setWatchlist(watchlistData);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load dashboard."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadDashboard(); }, []);

  async function addSymbol() {
    const symbol = newSymbol.trim(); if (!symbol) return;
    try { await addWatchlistSymbol(symbol); setNewSymbol(""); await loadDashboard(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to add symbol."); }
  }
  async function removeSymbol(id: number) {
    try { await deleteWatchlistSymbol(id); await loadDashboard(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to remove symbol."); }
  }

  if (loading) return <main className="min-h-screen bg-slate-50 p-6 text-slate-900"><div className="mx-auto max-w-7xl"><p>Loading dashboard...</p></div></main>;
  if (!analytics) return <main className="min-h-screen bg-slate-50 p-6"><div className="mx-auto max-w-2xl rounded-xl border bg-white p-8 text-center shadow-sm"><h1 className="text-2xl font-bold text-slate-900">TradePilot AI</h1><p className="mt-3 text-slate-600">We could not load your portfolio dashboard.</p>{error && <p className="mt-3 text-sm text-red-700">{error}</p>}<button type="button" onClick={() => void loadDashboard()} className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-white">Try again</button></div></main>;

  const profitPositive = analytics.total_profit_loss >= 0;
  const unrealizedPositive = analytics.unrealized_profit_loss >= 0;

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-3xl font-bold">TradePilot AI</h1><p className="mt-2 text-slate-600">Portfolio intelligence dashboard</p></div><div className="flex flex-wrap gap-2"><button type="button" onClick={onTransactions} className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-700">Transactions</button><button type="button" onClick={() => void loadDashboard()} className="rounded-lg bg-slate-950 px-4 py-2 font-semibold text-white">Refresh</button><button type="button" onClick={onLogout} className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-700">Logout</button></div></div>
        {error && <div className="mt-5 rounded-lg bg-red-50 p-4 font-medium text-red-700">{error}</div>}

        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border bg-white p-5 shadow-sm"><p className="text-sm font-medium text-slate-500">Invested</p><p className="mt-2 text-2xl font-bold">₹{money(analytics.total_invested)}</p></div>
          <div className="rounded-xl border bg-white p-5 shadow-sm"><p className="text-sm font-medium text-slate-500">Current Value</p><p className="mt-2 text-2xl font-bold">₹{money(analytics.current_value)}</p></div>
          <div className="rounded-xl border bg-white p-5 shadow-sm"><p className="text-sm font-medium text-slate-500">Total P/L</p><p className={`mt-2 text-2xl font-bold ${profitPositive ? "text-emerald-700" : "text-red-700"}`}>{profitPositive ? "+" : ""}₹{money(analytics.total_profit_loss)}</p></div>
          <div className="rounded-xl border bg-white p-5 shadow-sm"><p className="text-sm font-medium text-slate-500">Return</p><p className={`mt-2 text-2xl font-bold ${profitPositive ? "text-emerald-700" : "text-red-700"}`}>{profitPositive ? "+" : ""}{analytics.total_return_percent.toFixed(2)}%</p></div>
        </section>
        <section className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border bg-white p-5"><p className="text-sm font-medium text-slate-500">Realized P/L</p><p className={`mt-2 text-xl font-bold ${analytics.realized_profit_loss >= 0 ? "text-emerald-700" : "text-red-700"}`}>₹{money(analytics.realized_profit_loss)}</p></div>
          <div className="rounded-xl border bg-white p-5"><p className="text-sm font-medium text-slate-500">Unrealized P/L</p><p className={`mt-2 text-xl font-bold ${unrealizedPositive ? "text-emerald-700" : "text-red-700"}`}>{unrealizedPositive ? "+" : ""}₹{money(analytics.unrealized_profit_loss)}</p></div>
          <div className="rounded-xl border bg-white p-5"><p className="text-sm font-medium text-slate-500">Holdings</p><p className="mt-2 text-xl font-bold">{analytics.holdings_count}</p><p className="text-xs text-slate-500">Open positions</p></div>
          <div className="rounded-xl border bg-white p-5"><p className="text-sm font-medium text-slate-500">Trades</p><p className="mt-2 text-xl font-bold">{analytics.transactions_count}</p><p className="text-xs text-slate-500">Recorded transactions</p></div>
        </section>

        <section className="mt-8 rounded-xl border bg-white shadow-sm"><div className="border-b p-5"><h2 className="text-xl font-semibold">Holdings Performance</h2><p className="mt-1 text-sm text-slate-500">Live market price is used to calculate current value and unrealized P/L.</p></div><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr><th className="px-5 py-3">Symbol</th><th className="px-5 py-3">Quantity</th><th className="px-5 py-3">Avg. Buy</th><th className="px-5 py-3">Current Price</th><th className="px-5 py-3">Current Value</th><th className="px-5 py-3">P/L</th><th className="px-5 py-3">Return</th></tr></thead><tbody>{analytics.stocks.length === 0 && <tr className="border-t"><td className="px-5 py-6 text-center text-slate-500" colSpan={7}>No holdings yet.</td></tr>}{analytics.stocks.map((stock) => { const currentPrice = stock.quantity > 0 ? stock.current_value / stock.quantity : 0; const positive = stock.unrealized_profit_loss >= 0; return <tr key={stock.symbol} className="border-t border-slate-200 hover:bg-slate-50"><td className="px-5 py-4 font-bold">{stock.symbol}</td><td className="px-5 py-4">{stock.quantity}</td><td className="px-5 py-4">₹{money(stock.invested_amount / stock.quantity)}</td><td className="px-5 py-4 font-semibold">₹{money(currentPrice)}</td><td className="px-5 py-4">₹{money(stock.current_value)}</td><td className={`px-5 py-4 font-bold ${positive ? "text-emerald-700" : "text-red-700"}`}>{positive ? "+" : ""}₹{money(stock.unrealized_profit_loss)}</td><td className={`px-5 py-4 font-bold ${positive ? "text-emerald-700" : "text-red-700"}`}>{positive ? "+" : ""}{stock.unrealized_profit_loss_percent.toFixed(2)}%</td></tr>; })}</tbody></table></div></section>

        <section className="mt-8 rounded-xl border bg-white shadow-sm"><div className="flex flex-col gap-4 border-b p-5 md:flex-row md:items-center md:justify-between"><div><h2 className="text-xl font-semibold">Watchlist</h2><p className="text-sm text-slate-500">Search by company name or ticker. Suggestions are available as you type.</p></div><div className="flex w-full max-w-md gap-2"><div className="flex-1"><StockSearch value={newSymbol} onChange={setNewSymbol} placeholder="Search TCS, Tata, Infosys..." /></div><button type="button" onClick={() => void addSymbol()} className="rounded-lg bg-slate-950 px-4 py-2 font-semibold text-white">Add</button></div></div>{watchlist.length === 0 ? <div className="p-8 text-center text-slate-500">Your watchlist is empty.</div> : <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-4">{watchlist.map((item) => <div key={item.id} className="rounded-xl border border-slate-200 p-4"><div className="flex items-center justify-between"><span className="font-bold">{item.symbol}</span><button type="button" onClick={() => void removeSymbol(item.id)} className="text-xs font-semibold text-red-600 hover:underline">Remove</button></div><p className="mt-3 text-xl font-bold">₹{money(item.price)}</p><p className={`mt-1 text-sm font-bold ${item.change >= 0 ? "text-emerald-700" : "text-red-700"}`}>{item.change >= 0 ? "+" : ""}{money(item.change)} ({item.change_percent >= 0 ? "+" : ""}{item.change_percent.toFixed(2)}%)</p></div>)}</div>}</section>
        <IntelligencePanel />
      </div>
    </main>
  );
}
