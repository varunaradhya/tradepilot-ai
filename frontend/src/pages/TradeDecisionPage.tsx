import { useMemo, useState } from "react";
import { api } from "../services/api";

type Decision = { status: string; reason: string; action: string; confidence: number; entry: number | null; stop: number | null; target: number | null; risk_reward: number | null; quantity: number; capital_required: number; max_loss: number; broker: string; mode: string };

const demo = Array.from({ length: 30 }, (_, i) => 100 + i * 0.35);
const fmt = (value: number | null) => value == null ? "—" : `₹${value.toFixed(2)}`;

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
    try {
      const highs = closeValues.map(v => v + 0.5);
      const lows = closeValues.map(v => v - 0.5);
      const volumes = closeValues.map((_, i) => i === closeValues.length - 1 ? 1500 : 1000);
      const result = await api.post<Decision>("/trade-decision/paper", { symbol, session: new Date().toISOString().slice(0, 10), closes: closeValues, highs, lows, volumes, equity: Number(equity), broker: "DHAN", opening_high: Number(openingHigh) });
      setDecision(result);
    } catch (e) { setError(e instanceof Error ? e.message : "Decision failed"); }
    finally { setLoading(false); }
  }

  const ready = decision?.status === "PAPER_READY";
  return <main className="mx-auto max-w-7xl px-4 py-8">
    <div className="mb-7"><p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Intraday command center</p><h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950">Trade Decision Lab</h1><p className="mt-2 max-w-2xl text-sm text-slate-500">One auditable path from market evidence to position sizing and paper authorization. Live execution remains permanently locked.</p></div>
    <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
      <section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="font-bold">Market snapshot</h2><div className="mt-4 space-y-3"><label className="block text-sm font-semibold">Symbol<input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} className="mt-1 w-full rounded-xl border px-3 py-2" /></label><label className="block text-sm font-semibold">Account equity<input value={equity} onChange={e => setEquity(e.target.value)} className="mt-1 w-full rounded-xl border px-3 py-2" /></label><label className="block text-sm font-semibold">Opening high<input value={openingHigh} onChange={e => setOpeningHigh(e.target.value)} className="mt-1 w-full rounded-xl border px-3 py-2" /></label><label className="block text-sm font-semibold">Closing prices<input value={closes} onChange={e => setCloses(e.target.value)} className="mt-1 h-24 w-full rounded-xl border px-3 py-2 text-xs" /></label><button onClick={evaluate} disabled={loading || closeValues.length < 20} className="w-full rounded-xl bg-slate-950 px-4 py-3 font-bold text-white transition hover:-translate-y-0.5 disabled:opacity-50">{loading ? "Evaluating…" : "Evaluate paper setup →"}</button></div></section>
      <section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Decision</p><h2 className="mt-1 text-2xl font-black">{decision ? `${decision.action} ${symbol}` : "Awaiting market snapshot"}</h2></div>{decision && <span className={`rounded-full px-3 py-1.5 text-xs font-extrabold ${ready ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{ready ? "✓ PAPER READY" : decision.status.replaceAll("_", " ")}</span>}</div>{error && <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>}{decision && <><div className="mt-6 grid gap-3 sm:grid-cols-3">{[["Confidence", `${decision.confidence}%`],["Entry", fmt(decision.entry)],["Stop", fmt(decision.stop)],["Target", fmt(decision.target)],["R:R", decision.risk_reward ? `1 : ${decision.risk_reward.toFixed(2)}` : "—"],["Quantity", String(decision.quantity)]].map(([label,value]) => <div key={label} className="rounded-xl border p-4 transition hover:-translate-y-0.5"><p className="text-xs font-semibold text-slate-400">{label}</p><p className="mt-1 text-lg font-black">{value}</p></div>)}</div><div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="rounded-xl bg-slate-950 p-4 text-white"><p className="text-xs text-slate-400">Capital required</p><p className="mt-1 text-2xl font-black">{fmt(decision.capital_required)}</p></div><div className="rounded-xl bg-slate-950 p-4 text-white"><p className="text-xs text-slate-400">Maximum planned loss</p><p className="mt-1 text-2xl font-black">{fmt(decision.max_loss)}</p></div></div><div className="mt-4 flex items-center justify-between rounded-xl border p-4"><div><p className="font-bold">Reason</p><p className="text-sm text-slate-500">{decision.reason.replaceAll("_", " ")}</p></div><span className="text-xs font-extrabold text-slate-500">{decision.broker} · {decision.mode}</span></div></>}</section>
    </div>
  </main>;
}
