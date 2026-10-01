import { useEffect, useState } from "react";
import { api } from "../services/api";

type PaperDashboard = {
  mode: string;
  summary: { trades: number; open_trades: number; closed_trades: number; realized_pnl: number; win_rate_percent: number };
  performance: { summary?: { profit_factor?: number | null; max_drawdown_percent?: number; max_consecutive_losses?: number } };
  risk: { trade_direction: string; broker_orders_enabled: boolean; max_daily_loss_enforced: boolean; strategy_version_filter: string };
};

const money = (v: number) => `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function DashboardPageStable() {
  const [data, setData] = useState<PaperDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      setData(await api.get<PaperDashboard>("/paper-trading/dashboard"));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load algo dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  if (loading) {
    return <main className="tp-page"><div className="grid gap-4 md:grid-cols-4">{[1,2,3,4].map(i => <div key={i} className="h-28 animate-pulse rounded-2xl bg-white/[.03]" />)}</div></main>;
  }

  return <main className="tp-page">
    <header className="flex flex-wrap items-end justify-between gap-5">
      <div>
        <div className="tp-live-line">Algorithm workspace · paper execution only</div>
        <h1 className="tp-page-title mt-2 text-4xl font-black">Algo Command Center</h1>
        <p className="tp-page-subtitle mt-2 max-w-3xl text-sm">One focused workflow: define the strategy, backtest it, find signals, validate them and run the algorithm in paper mode.</p>
      </div>
      <button type="button" onClick={() => void load()} className="tp-button-primary">Refresh</button>
    </header>

    {error && <div role="alert" className="mt-5 tp-error">{error}</div>}

    <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {[
        ["Paper P&L", money(data?.summary.realized_pnl ?? 0)],
        ["Win rate", `${data?.summary.win_rate_percent ?? 0}%`],
        ["Closed trades", String(data?.summary.closed_trades ?? 0)],
        ["Open positions", String(data?.summary.open_trades ?? 0)],
      ].map(([label, value]) => <article key={label} className="tp-kpi"><p className="tp-section-label">{label}</p><p className="mt-3 text-2xl font-black text-white">{value}</p><p className="mt-1 text-xs text-slate-500">Paper simulation</p></article>)}
    </section>

    <section className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[
        ["01", "Strategy Lab", "Define rules and run backtests.", "strategy"],
        ["02", "Signal Scanner", "Find setups that satisfy the algorithm.", "scanner"],
        ["03", "Trade Decision", "Inspect entry, stop, target and risk.", "decision"],
        ["04", "Paper Trading", "Run the strategy without real orders.", "paper"],
      ].map(([step, title, detail, target]) => <button key={target} type="button" onClick={() => { window.location.hash = `#/${target}`; }} className="tp-premium-card group rounded-2xl p-5 text-left transition hover:-translate-y-1 hover:border-violet-400/30">
        <span className="text-xs font-black text-violet-300">{step}</span>
        <h2 className="mt-3 text-lg font-black text-white">{title}</h2>
        <p className="mt-2 text-sm text-slate-500">{detail}</p>
        <span className="mt-5 block text-xs font-bold text-violet-300">Open →</span>
      </button>)}
    </section>

    <section className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_.8fr]">
      <article className="tp-premium-card rounded-2xl p-6">
        <p className="tp-section-label">Algorithm status</p>
        <h2 className="mt-2 text-2xl font-black text-white">Paper execution protected</h2>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl bg-white/[.03] p-4"><p className="text-xs text-slate-500">Execution</p><p className="mt-1 font-black text-emerald-300">PAPER ONLY</p></div>
          <div className="rounded-xl bg-white/[.03] p-4"><p className="text-xs text-slate-500">Direction</p><p className="mt-1 font-black text-white">{data?.risk.trade_direction ?? "LONG_ONLY"}</p></div>
          <div className="rounded-xl bg-white/[.03] p-4"><p className="text-xs text-slate-500">Daily loss gate</p><p className="mt-1 font-black text-emerald-300">{data?.risk.max_daily_loss_enforced ? "ENFORCED" : "OFF"}</p></div>
        </div>
      </article>
      <article className="tp-premium-card rounded-2xl p-6">
        <p className="tp-section-label">Evidence</p>
        <h2 className="mt-2 text-xl font-black text-white">Performance snapshot</h2>
        <div className="mt-5 space-y-3 text-sm">
          <div className="flex justify-between"><span className="text-slate-500">Profit factor</span><b className="text-white">{data?.performance.summary?.profit_factor ?? "—"}</b></div>
          <div className="flex justify-between"><span className="text-slate-500">Max drawdown</span><b className="text-white">{data?.performance.summary?.max_drawdown_percent ?? 0}%</b></div>
          <div className="flex justify-between"><span className="text-slate-500">Max loss streak</span><b className="text-white">{data?.performance.summary?.max_consecutive_losses ?? 0}</b></div>
        </div>
      </article>
    </section>
  </main>;
}
