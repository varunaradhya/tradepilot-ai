import { useEffect, useState } from "react";
import { api } from "../services/api";
import ReadinessPanel from "../components/ReadinessPanel";
import StockSearch, { type StockInstrument } from "../components/StockSearch";

type Trade = { id: number; symbol: string; quantity: number; entry_price: number; stop_price: number; target_price: number; exit_price: number | null; pnl: number | null; status: "OPEN" | "CLOSED"; strategy_version: string; reason: string | null; created_at: string; closed_at: string | null };
type Dashboard = { mode: string; summary: { trades: number; open_trades: number; closed_trades: number; realized_pnl: number; win_rate_percent: number }; live: { open_position?: { symbol?: string; entry: number; stop: number; target: number; last_price: number; trailing_stop: number | null; quantity: number; bars_held: number }; unrealized_net_pnl: number; total_pnl: number }; open_positions: Array<{ id: number; symbol: string; quantity: number; entry_price: number; stop_price: number; target_price: number; pnl: number; strategy_version: string }>; risk: { trade_direction: string; broker_orders_enabled: boolean; max_daily_loss_enforced: boolean; strategy_version_filter: string } };
type Readiness = { status: string; live_trading_allowed: boolean; paper_trading_allowed: boolean; checks: Record<string, boolean>; reasons: string[]; paper: { trades: number; profit_factor: number | null; max_drawdown_percent: number; max_consecutive_losses: number }; cross_stock: { robust_percent: number; symbols_tested: number } };
type DhanResult = { mode: string; symbol: string; interval: string; processed_bars: number; buy_entries: number; persisted_trades: number; dataset_valid: boolean };
type LiveQuote = { market_connected: boolean; symbol?: string; ltp?: number; updated_at?: string; paper?: { unrealized_net_pnl: number; total_pnl: number; open_position?: { symbol?: string; entry: number; stop: number; target: number; last_price: number; trailing_stop: number | null; quantity: number; bars_held: number } }; execution?: { last_event?: string } };

function money(v: number) { return `₹${v.toFixed(2)}`; }

export default function PaperTradingPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<DhanResult | null>(null);
  const [live, setLive] = useState<LiveQuote | null>(null);
  const [filter, setFilter] = useState<"ALL" | "V1" | "V2">("ALL");
  const [closing, setClosing] = useState<number | null>(null);
  const [exitPrices, setExitPrices] = useState<Record<number, string>>({});
  const [instrument, setInstrument] = useState<StockInstrument | null>(null);
  const [symbolInput, setSymbolInput] = useState("");
  const [session, setSession] = useState("");
  const [interval, setIntervalValue] = useState("5");

  async function load(silent = false) {
    if (!silent) setLoading(true);
    try {
      const query = filter === "ALL" ? "" : `?strategy_version=${filter}`;
      const [dashboard, gate] = await Promise.all([api.get<Dashboard>(`/paper-trading/dashboard${query}`), api.get<Readiness>(`/paper-trading/readiness${query}`)]);
      setData(dashboard); setReadiness(gate); setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load paper trading."); }
    finally { setLoading(false); }
  }

  async function pollLive() {
    try { const result = await api.post<LiveQuote>("/paper-trading/session/live-ltp", {}); setLive(result); if (result.execution?.last_event === "EXIT") await load(true); }
    catch { setLive(null); }
  }

  useEffect(() => { void load(); const id = window.setInterval(() => void load(true), 10000); return () => window.clearInterval(id); }, [filter]);
  useEffect(() => { const id = window.setInterval(() => void pollLive(), 2000); return () => window.clearInterval(id); }, []);

  async function closeTrade(trade: Trade) {
    const raw = exitPrices[trade.id]?.trim();
    const exit = Number(raw);
    if (!raw || !Number.isFinite(exit) || exit <= 0) { setError(`Enter a valid positive exit price for ${trade.symbol}.`); return; }
    setClosing(trade.id);
    try { await api.post(`/paper-trading/trades/${trade.id}/close`, { exit_price: exit, reason: "MANUAL" }); setExitPrices((p) => ({ ...p, [trade.id]: "" })); await load(true); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to close trade."); }
    finally { setClosing(null); }
  }

  async function runDhan() {
    if (!instrument) { setError("Select an NSE stock from the suggestions."); return; }
    if (!session) { setError("Select a trading date."); return; }
    if (new Date(`${session}T00:00:00`) > new Date()) { setError("Trading date cannot be in the future."); return; }
    setSyncing(true); setError(""); setSyncResult(null);
    try { setSyncResult(await api.post<DhanResult>("/paper-trading/session/dhan", { symbol: instrument.symbol, session, interval })); await load(true); }
    catch (e) { setError(e instanceof Error ? e.message : "Unable to run Dhan paper session."); }
    finally { setSyncing(false); }
  }

  const summary = data?.summary;
  const livePnl = live?.paper?.unrealized_net_pnl ?? data?.live?.unrealized_net_pnl ?? 0;
  const livePos = live?.paper?.open_position ?? data?.live?.open_position;
  const gates = readiness ? Object.entries(readiness.checks).map(([key, passed]) => ({ label: key.replaceAll("_", " "), passed, detail: passed ? "Gate passed" : "Evidence required or gate not satisfied" })) : [];

  return <main className="min-h-screen bg-slate-50 p-6 text-slate-900"><div className="mx-auto max-w-7xl">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold uppercase tracking-wider text-slate-500">Simulation control center</p><h1 className="text-3xl font-bold">Paper Trading</h1><p className="mt-2 text-slate-600">Long-first virtual execution with read-only Dhan LTP. No broker order is sent.</p></div><div className="flex items-center gap-2"><span className="rounded-full bg-emerald-100 px-4 py-2 text-xs font-bold text-emerald-700">● SIMULATION ONLY</span>{live?.market_connected && <span className="rounded-full bg-sky-100 px-4 py-2 text-xs font-bold text-sky-700">● DHAN LIVE LTP</span>}<select value={filter} onChange={(e) => setFilter(e.target.value as "ALL" | "V1" | "V2")} className="rounded-full border bg-white px-3 py-2 text-xs font-bold"><option value="ALL">All strategies</option><option value="V1">V1 only</option><option value="V2">V2 only</option></select></div></header>
    {error && <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">{error}</div>}
    {readiness && <div className="mt-6"><ReadinessPanel status={readiness.status} gates={gates}><div className="mt-4 rounded-xl bg-slate-50 p-4 text-xs text-slate-600"><b>Evidence boundary:</b> {readiness.reasons.length ? readiness.reasons.join(" · ") : "All configured gates currently pass."} Cross-stock evidence: {readiness.cross_stock.symbols_tested} symbols / {readiness.cross_stock.robust_percent}% robust.</div></ReadinessPanel></div>}
    {livePos && <section className="mt-6 overflow-hidden rounded-2xl border border-sky-200 bg-white shadow-sm"><div className="flex flex-wrap items-center justify-between gap-4 bg-sky-950 p-5 text-white"><div><p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-300">Live paper position</p><h2 className="mt-1 text-2xl font-bold">{live?.symbol || livePos.symbol || "Position"} · {money(live?.ltp ?? livePos.last_price)}</h2><p className="mt-1 text-sm text-sky-200">Read-only Dhan LTP · updates every 2 seconds</p></div><div className={`rounded-full px-4 py-2 text-sm font-bold ${livePnl >= 0 ? "bg-emerald-400/20 text-emerald-200" : "bg-rose-400/20 text-rose-200"}`}>Net P&L {money(livePnl)}</div></div><div className="grid gap-3 p-5 sm:grid-cols-5">{[["Entry", money(livePos.entry)], ["LTP", money(live?.ltp ?? livePos.last_price)], ["Stop loss", money(livePos.stop)], ["Target", money(livePos.target)], ["Trailing stop", livePos.trailing_stop ? money(livePos.trailing_stop) : "Not active"]].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{label}</p><p className="font-bold">{value}</p></div>)}</div></section>}

    <section className="mt-6 overflow-hidden rounded-2xl border bg-white shadow-sm"><div className="bg-slate-950 p-5 text-white"><p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Historical replay</p><h2 className="mt-1 text-xl font-bold">Dhan → Strategy → Virtual Order</h2><p className="mt-1 text-sm text-slate-300">Select an NSE instrument; arbitrary symbols cannot be submitted.</p></div><div className="grid gap-3 p-5 sm:grid-cols-4"><label className="text-xs font-semibold text-slate-600 sm:col-span-2">Symbol<StockSearch value={symbolInput} onChange={setSymbolInput} onSelectionChange={setInstrument} onSelect={setInstrument} placeholder="Select NSE stock..." className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" /></label><label className="text-xs font-semibold text-slate-600">Trading date<input type="date" value={session} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setSession(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" /></label><label className="text-xs font-semibold text-slate-600">Interval<select value={interval} onChange={(e) => setIntervalValue(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"><option value="1">1 min</option><option value="5">5 min</option><option value="15">15 min</option><option value="25">25 min</option><option value="60">60 min</option></select></label><button type="button" disabled={!instrument || instrument.symbol !== symbolInput.trim().toUpperCase() || !session || syncing} onClick={() => void runDhan()} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white ring-1 ring-slate-700 disabled:cursor-not-allowed disabled:opacity-50 sm:col-start-4">{syncing ? "Replaying…" : "Run paper session"}</button></div>{syncResult && <div className="mx-5 mb-5 grid gap-2 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-4"><span><b>{syncResult.symbol}</b> · {syncResult.processed_bars} bars</span><span>{syncResult.buy_entries} BUY entries</span><span><b>{syncResult.persisted_trades}</b> trades persisted</span><span>dataset {syncResult.dataset_valid ? "valid" : "needs review"}</span></div>}</section>

    {loading && !data ? <div className="mt-6 grid gap-4 md:grid-cols-4">{[1, 2, 3, 4].map((i) => <div key={i} className="h-28 animate-pulse rounded-2xl bg-white shadow-sm" />)}</div> : data && <>
      <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[["Realized P&L", money(summary?.realized_pnl ?? 0)], ["Live Net P&L", money(livePnl)], ["Win rate", `${summary?.win_rate_percent ?? 0}%`], ["Open positions", String(summary?.open_trades ?? 0)]].map(([label, value]) => <div key={label} className="rounded-2xl border bg-white p-5 shadow-sm"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>)}</section>
      <section className="mt-4 grid gap-4 lg:grid-cols-3"><div className="rounded-2xl border bg-white p-5 shadow-sm lg:col-span-2"><div className="flex items-center justify-between"><div><h2 className="font-bold">Risk guardrails</h2><p className="text-xs text-slate-500">The paper environment blocks real execution.</p></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">Protected</span></div><div className="mt-4 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Direction</p><p className="mt-1 font-bold">{data.risk.trade_direction}</p></div><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Daily loss gate</p><p className="mt-1 font-bold">{data.risk.max_daily_loss_enforced ? "ENFORCED" : "OFF"}</p></div><div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">Broker orders</p><p className="mt-1 font-bold">{data.risk.broker_orders_enabled ? "ENABLED" : "BLOCKED"}</p></div></div></div><div className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="font-bold">Evidence progress</h2><p className="mt-2 text-sm text-slate-500">Closed trades contribute to the readiness sample.</p><div className="mt-4"><div className="flex justify-between text-xs font-semibold"><span>Paper sample</span><span>{summary?.closed_trades ?? 0} / 30</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, ((summary?.closed_trades ?? 0) / 30) * 100)}%` }} /></div></div></div></section>
      <section className="mt-4 rounded-2xl border bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="font-bold">Virtual positions</h2><p className="text-xs text-slate-500">Dhan LTP is marked separately from persisted trade history.</p></div><button type="button" onClick={() => void load()} className="rounded-lg border px-3 py-2 text-sm font-semibold">Refresh</button></div><div className="mt-4 overflow-x-auto">{data.open_positions.length === 0 ? <div className="rounded-xl bg-slate-50 p-8 text-center text-sm text-slate-500">No persisted open paper positions.</div> : <table className="w-full min-w-[900px] text-sm"><thead><tr className="border-b text-left text-xs uppercase text-slate-500"><th className="py-3">Symbol</th><th>Strategy</th><th>Entry</th><th>SL</th><th>Target</th><th>Qty</th><th>P&L</th><th>Manual exit</th></tr></thead><tbody>{data.open_positions.map((t) => <tr key={t.id} className="border-b"><td className="py-3 font-bold">{t.symbol}</td><td>{t.strategy_version}</td><td>{money(t.entry_price)}</td><td>{money(t.stop_price)}</td><td>{money(t.target_price)}</td><td>{t.quantity}</td><td className={t.pnl >= 0 ? "font-semibold text-emerald-700" : "font-semibold text-red-700"}>{money(t.pnl)}</td><td><div className="flex gap-2"><input value={exitPrices[t.id] ?? ""} onChange={(e) => setExitPrices((p) => ({ ...p, [t.id]: e.target.value }))} inputMode="decimal" placeholder="price" className="w-24 rounded-lg border px-2 py-1.5 text-xs"/><button type="button" disabled={closing === t.id} onClick={() => void closeTrade(t as unknown as Trade)} className="rounded-lg border px-2 py-1.5 text-xs font-semibold">{closing === t.id ? "…" : "Close"}</button></div></td></tr>)}</tbody></table>}</div></section>
    </>}
  </div></main>;
}
