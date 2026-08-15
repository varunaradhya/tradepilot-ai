import { useEffect, useMemo, useState } from "react";

import { connectDhan, getBrokers, syncDhan, type BrokerConnection } from "../services/brokers";

type BrokerCard = {
  name: string;
  key: string;
  description: string;
  phase: "READY" | "FOUNDATION";
  capabilities: string[];
};

const BROKERS: BrokerCard[] = [
  { name: "Dhan", key: "DHAN", description: "Portfolio synchronization and historical-data foundation.", phase: "READY", capabilities: ["Portfolio", "Transactions", "Historical data"] },
  { name: "Groww", key: "GROWW", description: "Broker adapter foundation is ready; account connectivity is the next integration step.", phase: "FOUNDATION", capabilities: ["Adapter", "Capability model", "Live orders locked"] },
  { name: "Angel One", key: "ANGELONE", description: "SmartAPI adapter foundation is ready; account connectivity is the next integration step.", phase: "FOUNDATION", capabilities: ["Adapter", "Capability model", "Live orders locked"] },
];

export default function BrokerPage() {
  const [brokers, setBrokers] = useState<BrokerConnection[]>([]);
  const [clientId, setClientId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadBrokers() {
    try {
      setBrokers(await getBrokers());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load brokers.");
    }
  }

  useEffect(() => { void loadBrokers(); }, []);

  async function connect() {
    if (!clientId || !accessToken) {
      setMessage("Enter Dhan Client ID and Access Token.");
      return;
    }
    try {
      setLoading(true);
      setMessage("");
      await connectDhan(clientId, accessToken);
      setAccessToken("");
      setMessage("Dhan connected successfully.");
      await loadBrokers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Dhan connection failed.");
    } finally { setLoading(false); }
  }

  async function synchronize() {
    try {
      setLoading(true);
      setMessage("");
      const result = await syncDhan();
      setMessage(`${result.message} Holdings: ${result.holdings_updated}. Transactions imported: ${result.transactions_imported}.`);
      await loadBrokers();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Synchronization failed.");
    } finally { setLoading(false); }
  }

  const dhan = brokers.find(broker => broker.broker_name === "DHAN");
  const connectedCount = brokers.filter(broker => broker.status === "CONNECTED" || broker.status === "ACTIVE").length;
  const cards = useMemo(() => BROKERS.map(card => ({ ...card, connection: brokers.find(b => b.broker_name === card.key) })), [brokers]);

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto max-w-6xl">
        <header className="rounded-3xl bg-slate-950 p-6 text-white shadow-lg sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Broker control center</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight">Broker Connections</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">Connect market and portfolio providers without coupling TradePilot's strategy engine to any single broker.</p>
            </div>
            <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-right">
              <p className="text-xs text-emerald-200">Execution safety</p>
              <p className="mt-1 font-extrabold text-emerald-300">🔒 LIVE ORDERS LOCKED</p>
            </div>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-white/5 p-4"><p className="text-xs text-slate-400">Connected accounts</p><p className="mt-1 text-2xl font-black">{connectedCount}</p></div>
            <div className="rounded-2xl bg-white/5 p-4"><p className="text-xs text-slate-400">Broker adapters</p><p className="mt-1 text-2xl font-black">3</p></div>
            <div className="rounded-2xl bg-white/5 p-4"><p className="text-xs text-slate-400">Live execution</p><p className="mt-1 text-2xl font-black text-emerald-300">BLOCKED</p></div>
          </div>
        </header>

        {message && <div className="mt-5 animate-pulse rounded-xl border border-slate-200 bg-white p-4 text-sm font-medium shadow-sm">{message}</div>}

        <section className="mt-6 grid gap-4 md:grid-cols-3">
          {cards.map(card => {
            const connected = Boolean(card.connection);
            return <article key={card.key} className="group rounded-2xl border bg-white p-5 shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-lg">
              <div className="flex items-start justify-between gap-3">
                <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">{card.key}</p><h2 className="mt-1 text-xl font-black">{card.name}</h2></div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-extrabold ${card.phase === "READY" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{card.phase}</span>
              </div>
              <p className="mt-3 min-h-12 text-sm leading-5 text-slate-500">{card.description}</p>
              <div className="mt-4 flex flex-wrap gap-1.5">{card.capabilities.map(cap => <span key={cap} className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">{cap}</span>)}</div>
              <div className="mt-5 flex items-center justify-between border-t pt-4 text-xs">
                <span className={connected ? "font-bold text-emerald-700" : "text-slate-500"}>{connected ? "● Connected" : "○ Not connected"}</span>
                <span className="font-bold text-slate-400">Live 🔒</span>
              </div>
            </article>;
          })}
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Account connection</p><h2 className="mt-1 text-xl font-black">Dhan</h2><p className="mt-1 text-sm text-slate-500">Read-only portfolio synchronization. Your access token is never displayed after submission.</p></div>{dhan && <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">{dhan.status}</span>}</div>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="text-xs font-bold text-slate-600">Client ID<input value={clientId} onChange={e => setClientId(e.target.value)} placeholder="Dhan Client ID" autoComplete="off" className="mt-1 w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:ring-2 focus:ring-slate-200" /></label>
              <label className="text-xs font-bold text-slate-600">Access token<input type="password" value={accessToken} onChange={e => setAccessToken(e.target.value)} placeholder="Dhan Access Token" autoComplete="new-password" className="mt-1 w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition focus:ring-2 focus:ring-slate-200" /></label>
            </div>
            <div className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={loading} onClick={() => void connect()} className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50">{loading ? "Working…" : dhan ? "Reconnect Dhan" : "Connect Dhan"}</button>{dhan && <button type="button" disabled={loading} onClick={() => void synchronize()} className="rounded-xl border px-5 py-2.5 text-sm font-bold transition hover:-translate-y-0.5 disabled:opacity-50">Sync Portfolio</button>}</div>
            {dhan && <div className="mt-5 rounded-xl bg-slate-50 p-4 text-xs text-slate-500"><p>Client: <span className="font-bold text-slate-700">{dhan.client_id}</span></p>{dhan.last_sync_at && <p className="mt-1">Last sync: {dhan.last_sync_at} · {dhan.last_sync_status ?? "unknown"}</p>}</div>}
          </div>

          <aside className="rounded-2xl border bg-white p-6 shadow-sm"><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Safety model</p><h2 className="mt-1 text-xl font-black">Connection is not execution</h2><div className="mt-5 space-y-3 text-sm">{["Credentials stay server-side", "Broker capability is tracked separately", "Strategy readiness is independent", "Paper trading remains the default", "Live orders remain globally locked"].map((item, i) => <div key={item} className="flex gap-2"><span className="font-bold text-emerald-600">{i < 4 ? "✓" : "🔒"}</span><span className="text-slate-600">{item}</span></div>)}</div><div className="mt-5 rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-900"><strong>Security:</strong> Never commit broker tokens, encryption keys, or secrets to GitHub.</div></aside>
        </section>
      </div>
    </main>
  );
}
