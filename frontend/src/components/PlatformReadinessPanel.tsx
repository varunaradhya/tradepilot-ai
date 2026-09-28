import { useState } from "react";
import { api } from "../services/api";

type BrokerCaps=Record<string,{integration_status:string;historical_data:boolean;market_data:boolean;portfolio:boolean;live_orders:boolean}>;
type Cloud={status:string;database_dialect:string;postgres_ready:boolean;migrations_managed_by_alembic:boolean;live_execution_enabled:boolean};

export default function PlatformReadinessPanel(){
  const [cloud,setCloud]=useState<Cloud|null>(null);
  const [brokers,setBrokers]=useState<BrokerCaps|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  async function load(){
    setLoading(true);setError("");
    try{const [c,b]=await Promise.all([api.get<Cloud>("/observability/cloud-readiness"),api.get<BrokerCaps>("/brokers/capabilities")]);setCloud(c);setBrokers(b);}
    catch(e){setError(e instanceof Error?e.message:"Platform readiness is unavailable.");}
    finally{setLoading(false);}
  }
  return <section className="mt-6 rounded-2xl border bg-white p-5 shadow-sm">
    <div className="flex items-center justify-between gap-3"><div><h2 className="font-semibold">Platform readiness</h2><p className="mt-1 text-sm text-slate-500">Deployment and broker integration status; live order execution remains hard locked.</p></div><button onClick={()=>void load()} disabled={loading} className="rounded-lg border px-4 py-2 text-sm font-semibold disabled:opacity-50">{loading?"Checking…":"Check readiness"}</button></div>
    {error&&<p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {cloud&&<div className="mt-4 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Cloud status</p><p className="font-bold">{cloud.status}</p></div><div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Database</p><p className="font-bold">{cloud.database_dialect}</p></div><div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Live orders</p><p className="font-bold">DISABLED</p></div></div>}
    {brokers&&<div className="mt-4 grid gap-3 md:grid-cols-3">{Object.entries(brokers).map(([name,c])=><div key={name} className="rounded-xl border p-4"><p className="font-semibold">{name}</p><p className="mt-1 text-xs text-slate-500">{c.integration_status}</p><div className="mt-3 text-xs space-y-1"><p>Historical: {c.historical_data?"available":"—"}</p><p>Market data: {c.market_data?"available":"—"}</p><p>Portfolio: {c.portfolio?"available":"—"}</p><p>Live orders: disabled</p></div></div>)}</div>}
  </section>
}
