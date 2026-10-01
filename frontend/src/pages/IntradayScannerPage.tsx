import { useEffect, useState } from "react";
import { api } from "../services/api";

type Result = {
  symbol:string; action:string; reason:string; session?:string; timestamp?:string;
  signal?: { entry?:number; stop?:number; target?:number; quality_score?:number; volume_ratio?:number; regime?:string };
};
type ScanResponse = {
  status:string; interval:string; strategy_version:string; strategy:Record<string,unknown>;
  strategy_fingerprint:string; results:Result[]; missing_symbols:string[]; warning:string;
};
type SelectedStrategy = {
  candidate_id?:string; parameters:Record<string,unknown>;
};

const defaultStrategy: Record<string,unknown> = {
  trade_direction:"LONG_ONLY", initial_capital:100000, brokerage_rate:.0003, slippage_rate:.0005,
  max_daily_loss_percent:1, max_trades_per_session:3, opening_bars:3, fast_period:9, slow_period:20,
  volume_period:20, min_volume_ratio:1.5, max_gap_percent:3, risk_per_trade:.005,
  max_position_percent:.2, atr_period:14, atr_stop_multiple:1.5, reward_multiple:2,
  min_trades:30, min_profit_factor:1.1, min_positive_sensitivity_percent:60,
  min_stable_profit_factor_percent:60, max_drawdown_percent:15, min_walk_forward_success_percent:55
};

function n(v: unknown, digits=2) { return typeof v === "number" ? v.toFixed(digits) : "—"; }

export default function IntradayScannerPage() {
  const [symbols,setSymbols] = useState("TCS,INFY,RELIANCE,HDFCBANK,ICICIBANK,SBIN");
  const [selected,setSelected] = useState<SelectedStrategy|null>(null);
  const [result,setResult] = useState<ScanResponse|null>(null);
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState("");

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("tradepilot:selectedStrategy");
      if (raw) setSelected(JSON.parse(raw) as SelectedStrategy);
    } catch { setSelected(null); }
  }, []);

  async function scan() {
    setLoading(true); setError("");
    try {
      const strategy = { ...defaultStrategy, ...(selected?.parameters ?? {}) };
      const data = await api.post<ScanResponse>(
        `/strategy-builder/signal-scan?symbols=${encodeURIComponent(symbols)}&interval=5`,
        strategy
      );
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Signal scanner unavailable.");
    } finally { setLoading(false); }
  }

  const buyCount = result?.results.filter(x => x.action === "BUY").length ?? 0;

  return <main className="tp-page">
    <header className="flex flex-wrap items-end justify-between gap-5">
      <div>
        <div className="tp-live-line">NSE · 5-minute algorithm</div>
        <h1 className="tp-page-title mt-2 text-4xl font-black">Signal Scanner</h1>
        <p className="tp-page-subtitle mt-2 max-w-3xl">Run the selected Strategy Lab configuration across the NSE research basket and turn the latest completed session into explicit BUY / WAIT decisions.</p>
      </div>
      <button onClick={()=>void scan()} disabled={loading} className="tp-button-primary">{loading?"Scanning…":"Scan with this strategy →"}</button>
    </header>

    <section className="tp-premium-card mt-6 rounded-2xl p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="tp-section-label">Active algorithm</p>
          <h2 className="mt-1 text-xl font-black text-white">{selected?.candidate_id ?? "Baseline ORB"}</h2>
          <p className="mt-1 text-xs text-slate-500">5-minute · V1 · research signal generation</p>
        </div>
        <div className="rounded-xl border border-amber-400/15 bg-amber-400/[.04] px-4 py-3 text-xs text-amber-200">No broker order is created by scanning.</div>
      </div>
      <textarea value={symbols} onChange={e=>setSymbols(e.target.value.toUpperCase())} className="mt-5 h-20 w-full rounded-xl border p-3 text-sm outline-none" placeholder="TCS,INFY,RELIANCE,HDFCBANK" />
      {selected && <div className="mt-4 flex flex-wrap gap-2 text-[10px] font-bold text-slate-500">
        <span className="rounded-full bg-white/[.04] px-3 py-1.5">ORB {String(selected.parameters.opening_bars ?? 3)} bars</span>
        <span className="rounded-full bg-white/[.04] px-3 py-1.5">EMA {String(selected.parameters.fast_period ?? 9)}/{String(selected.parameters.slow_period ?? 20)}</span>
        <span className="rounded-full bg-white/[.04] px-3 py-1.5">ATR {String(selected.parameters.atr_stop_multiple ?? 1.5)}×</span>
        <span className="rounded-full bg-white/[.04] px-3 py-1.5">R {String(selected.parameters.reward_multiple ?? 2)}×</span>
      </div>}
    </section>

    {error && <div className="mt-4 rounded-xl border border-red-400/20 bg-red-400/10 p-4 text-sm font-medium text-red-200">{error}</div>}

    {result && <>
      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        <article className="tp-kpi"><p className="tp-section-label">SYMBOLS</p><p className="tp-number mt-2 text-3xl font-black text-white">{result.results.length}</p></article>
        <article className="tp-kpi"><p className="tp-section-label">BUY SETUPS</p><p className="tp-number mt-2 text-3xl font-black text-emerald-300">{buyCount}</p></article>
        <article className="tp-kpi"><p className="tp-section-label">WAIT</p><p className="tp-number mt-2 text-3xl font-black text-white">{result.results.length-buyCount}</p></article>
      </section>

      <section className="tp-premium-card mt-5 overflow-hidden rounded-2xl">
        <div className="border-b border-white/10 p-5">
          <p className="tp-section-label">Latest stored session</p>
          <h2 className="mt-1 text-xl font-black text-white">Algorithm decisions</h2>
        </div>
        <div className="divide-y divide-white/5">
          {result.results.map(row => <div key={row.symbol} className="grid gap-4 p-5 md:grid-cols-[1fr_120px_1fr] md:items-center">
            <div><p className="text-lg font-black text-white">{row.symbol}</p><p className="mt-1 text-xs text-slate-600">{row.session ?? "—"} · {row.timestamp ?? "—"}</p></div>
            <span className={`rounded-full px-3 py-2 text-center text-xs font-black ${row.action==="BUY"?"bg-emerald-400/10 text-emerald-300":"bg-white/[.05] text-slate-400"}`}>{row.action}</span>
            <div>
              <p className="text-xs font-bold text-slate-400">{row.reason.replaceAll("_"," ")}</p>
              {row.signal?.entry && <div className="mt-2 flex flex-wrap items-center gap-3"><div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500"><span>Entry <b className="text-white">{n(row.signal.entry)}</b></span><span>SL <b className="text-rose-300">{n(row.signal.stop)}</b></span><span>Target <b className="text-emerald-300">{n(row.signal.target)}</b></span><span>Quality <b className="text-white">{n(row.signal.quality_score,0)}</b></span></div>{row.action==="BUY"&&<button onClick={()=>{sessionStorage.setItem("tradepilot:generatedSignal",JSON.stringify({symbol:row.symbol,session:row.session,action:row.action,confidence:row.signal?.quality_score??0,entry:row.signal?.entry,stop:row.signal?.stop,target:row.signal?.target,strategy_fingerprint:result.strategy_fingerprint}));window.location.hash="#/decision";}} className="rounded-lg bg-violet-500/15 px-3 py-1.5 text-[10px] font-black text-violet-200">Trade Decision →</button>}</div>}
            </div>
          </div>)}
        </div>
      </section>

      {result.missing_symbols.length>0 && <div className="mt-4 rounded-xl border border-amber-400/15 bg-amber-400/[.04] p-4 text-sm text-amber-200">Missing datasets: {result.missing_symbols.join(", ")}</div>}
      <div className="mt-5 rounded-xl border border-white/5 bg-white/[.02] p-4 text-xs text-slate-500"><b className="text-slate-300">Research boundary:</b> these are signals generated from stored historical data. They do not authorize live execution.</div>
    </>}
  </main>;
}
