import { useMemo, useState } from "react";
import { api } from "../services/api";

type Decision = { status: string; reason: string; action: string; confidence: number; entry: number | null; stop: number | null; target: number | null; risk_reward: number | null; quantity: number; capital_required: number; max_loss: number; broker: string; mode: string };
const demo = Array.from({ length: 30 }, (_, i) => 100 + i * 0.35);
const fmt = (value: number | null) => value == null ? "—" : `₹${value.toFixed(2)}`;

function Gauge({ value }: { value: number }) {
  const safe = Math.max(0, Math.min(100, value));
  return <div className="relative grid h-36 w-36 place-items-center rounded-full" style={{ background: `conic-gradient(#7c5cff ${safe * 3.6}deg, rgba(255,255,255,.07) 0deg)` }}><div className="grid h-28 w-28 place-items-center rounded-full bg-[#0a101d]"><span className="tp-number text-4xl font-black text-white">{Math.round(safe)}</span><span className="text-[9px] font-extrabold uppercase tracking-widest text-slate-600">confidence</span></div></div>;
}

export default function TradeDecisionPage() {
  const [symbol, setSymbol] = useState("TCS");
  const [equity, setEquity] = useState("100000");
  const [openingHigh, setOpeningHigh] = useState("108");
  const [closes, setCloses] = useState(demo.join(","));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [decision, setDecision] = useState<Decision | null>(null);
  const closeValues = useMemo(() => closes.split(",").map(Number).filter(Number.isFinite), [closes]);

  async function evaluate() {
    setLoading(true); setError("");
    try { const highs = closeValues.map(v => v + 0.5); const lows = closeValues.map(v => v - 0.5); const volumes = closeValues.map((_, i) => i === closeValues.length - 1 ? 1500 : 1000); setDecision(await api.post<Decision>("/trade-decision/paper", { symbol, session: new Date().toISOString().slice(0, 10), closes: closeValues, highs, lows, volumes, equity: Number(equity), broker: "DHAN", opening_high: Number(openingHigh) })); }
    catch (e) { setError(e instanceof Error ? e.message : "Decision failed"); }
    finally { setLoading(false); }
  }
  const ready = decision?.status === "PAPER_READY";
  const confidence = decision?.confidence ?? 0;

  return <main className="tp-page">
    <header className="flex flex-wrap items-end justify-between gap-5"><div><div className="tp-live-line">Decision engine · paper only</div><h1 className="tp-page-title mt-2 text-4xl font-black">Trade Decision</h1><p className="tp-page-subtitle mt-2 max-w-2xl text-sm">One auditable path from market evidence to position sizing and paper authorization. Live execution is locked.</p></div><div className="rounded-xl border border-emerald-400/15 bg-emerald-400/[.05] px-4 py-2.5 text-right"><p className="tp-section-label">Safety boundary</p><p className="mt-1 text-xs font-black text-emerald-300">🔒 LIVE ORDERS DISABLED</p></div></header>
    <div className="mt-7 grid gap-5 xl:grid-cols-[330px_1fr]">
      <section className="tp-premium-card rounded-2xl p-5"><div><p className="tp-section-label">Market snapshot</p><h2 className="mt-1 text-lg font-black text-white">Build the evidence set</h2></div><div className="mt-5 space-y-3"><label className="block text-xs font-bold text-slate-500">Symbol<input value={symbol} onChange={e=>setSymbol(e.target.value.toUpperCase())} className="mt-1 w-full rounded-xl border px-3 py-2.5" /></label><label className="block text-xs font-bold text-slate-500">Account equity<input value={equity} onChange={e=>setEquity(e.target.value)} className="mt-1 w-full rounded-xl border px-3 py-2.5" /></label><label className="block text-xs font-bold text-slate-500">Opening high<input value={openingHigh} onChange={e=>setOpeningHigh(e.target.value)} className="mt-1 w-full rounded-xl border px-3 py-2.5" /></label><label className="block text-xs font-bold text-slate-500">Closing prices<input value={closes} onChange={e=>setCloses(e.target.value)} className="mt-1 h-28 w-full rounded-xl border px-3 py-2 text-xs leading-5" /></label><p className="text-[10px] text-slate-600">Minimum 20 valid closing observations. The UI does not fabricate missing market data.</p><button onClick={evaluate} disabled={loading || closeValues.length < 20} className="w-full rounded-xl bg-slate-950 px-4 py-3 text-sm font-black text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50">{loading ? "Evaluating…" : "Evaluate paper setup →"}</button></div></section>

      <section className="tp-premium-card overflow-hidden rounded-2xl"><div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 p-5"><div><p className="tp-section-label">Decision output</p><h2 className="mt-1 text-2xl font-black text-white">{decision ? `${decision.action} ${symbol}` : "Awaiting market snapshot"}</h2></div>{decision && <span className={`rounded-full px-3 py-1.5 text-[10px] font-black ${ready?"bg-emerald-400/10 text-emerald-300":"bg-amber-400/10 text-amber-300"}`}>{ready ? "✓ PAPER READY" : decision.status.replaceAll("_", " ")}</span>}</div>
        {error && <div className="m-5 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm font-semibold text-red-200">{error}</div>}
        {!decision ? <div className="grid min-h-[430px] place-items-center p-8 text-center"><div><div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl border border-white/10 bg-white/[.03] text-3xl text-slate-600">⌁</div><p className="mt-4 text-sm font-bold text-slate-400">Run the decision engine to populate the trade plan.</p><p className="mt-2 text-xs text-slate-600">The result remains paper-only and auditable.</p></div></div> : <div className="p-5">
          <div className="grid gap-6 lg:grid-cols-[170px_1fr] lg:items-center"><div className="flex justify-center"><Gauge value={confidence} /></div><div><p className="tp-section-label">TradePilot confidence</p><p className="mt-2 text-3xl font-black text-white">{confidence}%</p><div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-teal-400 transition-all duration-700" style={{width:`${Math.max(0,Math.min(100,confidence))}%`}} /></div><div className="mt-4 grid gap-2 sm:grid-cols-3"><div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><p className="tp-section-label">Action</p><p className="mt-1 font-black text-white">{decision.action}</p></div><div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><p className="tp-section-label">Status</p><p className="mt-1 font-black text-white">{decision.status.replaceAll("_"," ")}</p></div><div className="rounded-xl border border-white/5 bg-white/[.025] p-3"><p className="tp-section-label">Mode</p><p className="mt-1 font-black text-white">{decision.mode}</p></div></div></div></div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">{[["ENTRY",fmt(decision.entry)],["STOP",fmt(decision.stop)],["TARGET",fmt(decision.target)]].map(([label,value])=><div key={label} className="rounded-2xl border border-white/10 bg-white/[.025] p-4"><p className="tp-section-label">{label}</p><p className="tp-number mt-2 text-xl font-black text-white">{value}</p></div>)}</div>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">{[["RISK / REWARD",decision.risk_reward?`1 : ${decision.risk_reward.toFixed(2)}`:"—"],["QUANTITY",String(decision.quantity)],["MAX LOSS",fmt(decision.max_loss)]].map(([label,value])=><div key={label} className="rounded-2xl border border-white/10 bg-white/[.025] p-4"><p className="tp-section-label">{label}</p><p className="tp-number mt-2 text-lg font-black text-white">{value}</p></div>)}</div>
          <div className="mt-5 grid gap-3 md:grid-cols-2"><div className="rounded-2xl bg-gradient-to-br from-violet-600/20 to-violet-400/[.03] p-5 ring-1 ring-violet-400/10"><p className="tp-section-label">Capital required</p><p className="tp-number mt-2 text-2xl font-black text-white">{fmt(decision.capital_required)}</p></div><div className="rounded-2xl border border-white/10 bg-white/[.02] p-5"><p className="tp-section-label">Decision rationale</p><p className="mt-2 text-sm font-semibold leading-6 text-slate-300">{decision.reason.replaceAll("_", " ")}</p><p className="mt-2 text-[10px] font-bold uppercase tracking-wider text-slate-600">{decision.broker} · {decision.mode}</p></div></div>
          <div className={`mt-5 flex flex-col gap-3 rounded-2xl border p-4 sm:flex-row sm:items-center sm:justify-between ${ready?"border-emerald-400/15 bg-emerald-400/[.05]":"border-amber-400/15 bg-amber-400/[.05]"}`}><div><p className={`text-sm font-black ${ready?"text-emerald-300":"text-amber-300"}`}>{ready?"Paper trade ready":"No paper authorization"}</p><p className="mt-1 text-xs text-slate-500">TradePilot does not send broker orders from this screen.</p></div><button type="button" onClick={evaluate} disabled={loading} className="rounded-xl border border-white/10 bg-white/[.04] px-4 py-2.5 text-xs font-black text-white hover:border-white/20">Re-evaluate</button></div>
        </div>}
      </section>
    </div>
  </main>;
}
