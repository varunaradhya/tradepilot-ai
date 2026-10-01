import { useState } from "react";
import { api } from "../services/api";

type Metrics = { return_percent:number; trades:number; win_rate_percent:number; profit_factor:number|null; expectancy:number; max_drawdown_percent:number };
type Candidate = { candidate_id:string; parameters:Record<string,number|string|boolean>; symbols_tested:number; symbols_with_minimum_test_trades:number; robust_fraction_percent:number; average_test_return_percent:number; median_test_profit_factor:number|null; worst_test_drawdown_percent:number; average_screening_score:number };
type Discovery = { status:string; method:string; research_only:boolean; candidate_count:number; candidates:Candidate[]; warning:string; missing_symbols:string[] };

const base = { trade_direction:"LONG_ONLY", initial_capital:100000, brokerage_rate:.0003, slippage_rate:.0005, max_daily_loss_percent:1, max_trades_per_session:3, opening_bars:3, fast_period:9, slow_period:20, volume_period:20, min_volume_ratio:1.5, max_gap_percent:3, risk_per_trade:.005, max_position_percent:.2, atr_period:14, atr_stop_multiple:1.5, reward_multiple:2, min_trades:30, min_profit_factor:1.1, min_positive_sensitivity_percent:60, min_stable_profit_factor_percent:60, max_drawdown_percent:15, min_walk_forward_success_percent:55 };

export default function StrategyBuilderPage(){
 const [symbols,setSymbols]=useState("TCS,INFY,RELIANCE,HDFCBANK,ICICIBANK,SBIN"),[result,setResult]=useState<Discovery|null>(null),[selected,setSelected]=useState<Candidate|null>(null),[backtest,setBacktest]=useState<Metrics|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState("");
 async function discover(){
  setLoading(true);setError("");setBacktest(null);
  try{
   const q=`?symbols=${encodeURIComponent(symbols)}&interval=5&train_fraction=0.70&min_test_trades=10`;
   const data=await api.post<Discovery>(`/strategy-builder/discover${q}`,base);
   setResult(data);setSelected(data.candidates[0]??null);
  }catch(e){setError(e instanceof Error?e.message:"Strategy discovery failed.");}finally{setLoading(false);}
 }
 function useInScanner(candidate: Candidate){
  let fingerprint: string | undefined;
  try { fingerprint = (JSON.parse(sessionStorage.getItem("tradepilot:selectedStrategy") || "{}") as {strategy_fingerprint?:string}).strategy_fingerprint; } catch { fingerprint = undefined; }
  sessionStorage.setItem("tradepilot:selectedStrategy", JSON.stringify({...candidate, ...(fingerprint ? {strategy_fingerprint:fingerprint} : {})}));
  window.location.hash = "#/scanner";
}

async function authorizePaper(candidate:Candidate){
  setLoading(true); setError("");
  try {
    const data = await api.post<{authorized:boolean;fingerprint:string;qualification:{status:string;paper_trading_allowed?:boolean}}>(`/strategy-builder/authorize-paper?symbol=TCS&interval=5&train_size=60&validation_size=20`,{...base,...candidate.parameters});
    sessionStorage.setItem("tradepilot:selectedStrategy", JSON.stringify({...candidate, strategy_fingerprint:data.fingerprint}));
    setSelected(candidate);
  } catch(e) { setError(e instanceof Error ? e.message : "Paper authorization failed."); }
  finally { setLoading(false); }
 }

async function runBacktest(candidate:Candidate){
  setLoading(true);setError("");
  try{
   const data=await api.post<Metrics>(`/strategy-builder/backtest?symbol=TCS&interval=5`,{...base,...candidate.parameters});
   setSelected(candidate);setBacktest(data);
  }catch(e){setError(e instanceof Error?e.message:"Backtest failed.");}finally{setLoading(false);}
 }
 return <main className="tp-page">
  <header className="flex flex-wrap items-end justify-between gap-5">
   <div><p className="tp-live-line">Algorithm research · 5-minute NSE</p><h1 className="tp-page-title mt-2 text-4xl font-black">Strategy Lab</h1><p className="tp-page-subtitle mt-2 max-w-3xl">Use the historical data already available to discover interpretable ORB configurations, then validate a candidate before paper trading.</p></div>
   <button onClick={()=>void discover()} disabled={loading} className="tp-button-primary">{loading?"Running research…":"Discover strategies →"}</button>
  </header>

  <section className="mt-7 tp-premium-card rounded-2xl p-5">
   <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
    <label className="block"><span className="tp-section-label">NSE universe</span><input value={symbols} onChange={e=>setSymbols(e.target.value.toUpperCase())} className="tp-field mt-2 w-full" placeholder="TCS,INFY,RELIANCE,HDFCBANK..." /></label>
    <div className="rounded-xl border border-amber-400/15 bg-amber-400/[.04] px-4 py-3 text-xs text-amber-200">5-minute · Intraday · ORB family · chronological holdout</div>
   </div>
   <div className="mt-5 grid gap-3 sm:grid-cols-3">
    {[
      ["01","Train","70% historical sequence"],
      ["02","Holdout","30% unseen sequence"],
      ["03","Screen","Return + PF + drawdown + robustness"],
    ].map(([n,t,d])=><div key={n} className="rounded-xl bg-white/[.025] p-4"><span className="text-xs font-black text-violet-300">{n}</span><p className="mt-2 font-black text-white">{t}</p><p className="mt-1 text-xs text-slate-500">{d}</p></div>)}
   </div>
  </section>

  {error&&<div role="alert" className="mt-5 tp-error">{error}</div>}

  {result&&<section className="mt-6 tp-premium-card rounded-2xl p-5">
   <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="tp-section-label">Discovery result</p><h2 className="mt-1 text-2xl font-black text-white">{result.candidate_count} configurations evaluated</h2><p className="mt-2 text-sm text-slate-500">These are historical screening candidates, not promises and not live-authorized strategies.</p></div><span className="rounded-full bg-amber-400/10 px-3 py-1.5 text-xs font-black text-amber-300">RESEARCH ONLY</span></div>
   <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead><tr className="border-b border-white/10 text-xs uppercase tracking-wider text-slate-500"><th className="py-3">Candidate</th><th>Symbols</th><th>Holdout return</th><th>Holdout PF</th><th>Robust</th><th>Worst DD</th><th></th></tr></thead><tbody>{result.candidates.map(c=><tr key={c.candidate_id} className={selected?.candidate_id===c.candidate_id?"bg-violet-500/[.05]":""}><td className="py-4"><button onClick={()=>setSelected(c)} className="font-black text-white hover:text-violet-300">{c.candidate_id}</button><p className="mt-1 text-[10px] text-slate-500">{String(c.parameters.opening_bars)} opening bars · EMA {String(c.parameters.fast_period)}/{String(c.parameters.slow_period)} · ATR {String(c.parameters.atr_stop_multiple)} · R {String(c.parameters.reward_multiple)}</p></td><td>{c.symbols_with_minimum_test_trades}/{c.symbols_tested}</td><td>{c.average_test_return_percent}%</td><td>{c.median_test_profit_factor??"—"}</td><td>{c.robust_fraction_percent}%</td><td>{c.worst_test_drawdown_percent}%</td><td><div className="flex gap-2"><button onClick={()=>void runBacktest(c)} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-black text-white">Backtest TCS</button><button onClick={()=>void authorizePaper(c)} disabled={loading} className="rounded-lg border border-emerald-400/15 bg-emerald-400/10 px-3 py-2 text-xs font-black text-emerald-200">Validate for Paper</button><button onClick={()=>useInScanner(c)} className="rounded-lg bg-violet-500/15 px-3 py-2 text-xs font-black text-violet-200">Use in Scanner →</button></div></td></tr>)}</tbody></table></div>
   {selected&&<div className="mt-5 grid gap-4 lg:grid-cols-2">
    <div className="rounded-2xl bg-white/[.025] p-5"><p className="tp-section-label">{selected.candidate_id} parameters</p><div className="mt-4 grid grid-cols-2 gap-3 text-sm">{Object.entries(selected.parameters).filter(([k])=>["opening_bars","fast_period","slow_period","atr_stop_multiple","reward_multiple"].includes(k)).map(([k,v])=><div key={k}><span className="text-slate-500">{k.replaceAll("_"," ")}</span><b className="ml-2 text-white">{String(v)}</b></div>)}</div></div>
    <div className="rounded-2xl border border-emerald-400/10 bg-emerald-400/[.03] p-5"><p className="tp-section-label">Next validation</p><p className="mt-2 text-sm leading-6 text-slate-300">Run walk-forward and paper trading on the selected configuration. Live execution stays locked until the validation gates are satisfied.</p></div>
   </div>}
  </section>}

  {backtest&&<section className="mt-6 tp-premium-card rounded-2xl p-5"><p className="tp-section-label">TCS 5-minute backtest</p><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[["Return",`${backtest.return_percent}%`],["Profit factor",backtest.profit_factor??"—"],["Win rate",`${backtest.win_rate_percent}%`],["Expectancy",backtest.expectancy],["Max drawdown",`${backtest.max_drawdown_percent}%`]].map(([l,v])=><div key={l} className="tp-kpi"><p className="tp-section-label">{l}</p><p className="mt-2 text-xl font-black text-white">{String(v)}</p></div>)}</div></section>}

  <p className="mt-6 text-xs text-slate-600">{result?.warning??"Discovery uses only the configured historical datasets and never sends broker orders."}</p>
 </main>
}
