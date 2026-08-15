import type { ReactNode } from "react";

type Gate = { label: string; passed: boolean; detail: string };

export default function ReadinessPanel({ title = "Strategy readiness", status, gates, children }: { title?: string; status: string; gates: Gate[]; children?: ReactNode }) {
  const passed = gates.filter(g => g.passed).length;
  const percent = gates.length ? Math.round((passed / gates.length) * 100) : 0;
  const locked = status !== "LIVE_REVIEW";
  return <section className="rounded-2xl border bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Decision gate</p><h2 className="text-xl font-bold">{title}</h2><p className="mt-1 text-sm text-slate-500">Research, OOS and paper evidence are evaluated separately from live execution.</p></div>
      <span className={`rounded-full px-3 py-1.5 text-xs font-extrabold ${locked ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>{locked ? "🔒 LIVE LOCKED" : "REVIEW ONLY"}</span>
    </div>
    <div className="mt-5 grid gap-4 lg:grid-cols-[180px_1fr]">
      <div className="rounded-2xl bg-slate-950 p-5 text-white"><p className="text-xs text-slate-400">Current status</p><p className="mt-2 text-lg font-extrabold">{status}</p><div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-700"><div className="h-full rounded-full bg-emerald-400 transition-all duration-700" style={{ width: `${percent}%` }} /></div><p className="mt-2 text-xs text-slate-400">{passed}/{gates.length} gates passed</p></div>
      <div className="grid gap-2 sm:grid-cols-2">{gates.map(g => <div key={g.label} className="rounded-xl border p-3 transition hover:-translate-y-0.5"><div className="flex items-center justify-between gap-2"><span className="font-semibold text-sm">{g.label}</span><span className={g.passed ? "text-emerald-600" : "text-amber-600"}>{g.passed ? "✓" : "•"}</span></div><p className="mt-1 text-xs text-slate-500">{g.detail}</p></div>)}</div>
    </div>
    {children}
  </section>;
}
