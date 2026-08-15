type Broker = { name: string; code: string; status: "AVAILABLE" | "FOUNDATION" | "PLANNED"; marketData: boolean; orders: boolean; note: string };

const brokers: Broker[] = [
  { name: "Dhan", code: "DHAN", status: "AVAILABLE", marketData: true, orders: true, note: "Primary broker integration. Live execution remains locked by TradePilot." },
  { name: "Groww", code: "GROWW", status: "FOUNDATION", marketData: false, orders: false, note: "Broker adapter foundation is present; provider connectivity is not enabled yet." },
  { name: "Angel One", code: "ANGELONE", status: "FOUNDATION", marketData: false, orders: false, note: "SmartAPI adapter foundation is planned; live connectivity remains disabled." },
];

export default function BrokerConnectionPanel() {
  return <section className="rounded-2xl border bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Broker connections</p><h2 className="text-xl font-bold">Connect your broker</h2><p className="mt-1 text-sm text-slate-500">One TradePilot strategy layer, multiple broker adapters. Credentials should never be stored in the frontend.</p></div>
      <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-extrabold text-amber-700">🔒 LIVE ORDERS LOCKED</span>
    </div>
    <div className="mt-5 grid gap-3 md:grid-cols-3">{brokers.map(b => <article key={b.code} className="group rounded-2xl border p-4 transition duration-300 hover:-translate-y-1 hover:shadow-md">
      <div className="flex items-center justify-between"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-sm font-black text-white">{b.code.slice(0,2)}</div><span className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold ${b.status === "AVAILABLE" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{b.status}</span></div>
      <h3 className="mt-4 text-lg font-bold">{b.name}</h3><p className="mt-1 min-h-10 text-xs leading-5 text-slate-500">{b.note}</p>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs"><div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-400">Market data</span><div className="font-bold">{b.marketData ? "READY" : "FOUNDATION"}</div></div><div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-400">Live orders</span><div className="font-bold">{b.orders ? "LOCKED" : "NOT ENABLED"}</div></div></div>
      <button disabled={b.status !== "AVAILABLE"} className="mt-4 w-full rounded-xl border px-3 py-2 text-sm font-bold transition group-hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50">{b.status === "AVAILABLE" ? "Connect / manage" : "Coming in adapter phase"}</button>
    </article>)}</div>
    <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600"><b>Safety boundary:</b> broker connectivity does not grant live-trading permission. Every order must still pass strategy readiness, risk controls and the global live-execution lock.</div>
  </section>;
}
