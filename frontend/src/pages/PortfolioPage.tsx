import { FormEvent, useEffect, useState } from "react";
import StockSearch from "../components/StockSearch";
import { createHolding, deleteHolding, getHoldings, type Holding } from "../services/portfolio";

function money(value: number) { return value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function load() {
    try {
      setLoading(true);
      setError("");
      setHoldings(await getHoldings());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load portfolio.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function addHolding(event: FormEvent) {
    event.preventDefault();
    setError(""); setSuccess("");
    const normalized = symbol.trim().toUpperCase();
    const parsedQuantity = Number(quantity);
    const parsedPrice = Number(price);
    if (!normalized) return setError("Select an Indian stock.");
    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) return setError("Quantity must be greater than zero.");
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) return setError("Average buy price must be greater than zero.");
    try {
      setSaving(true);
      await createHolding({ symbol: normalized, quantity: parsedQuantity, average_buy_price: parsedPrice });
      setSymbol(""); setQuantity(""); setPrice("");
      setSuccess(`${normalized} was added to your portfolio.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add holding.");
    } finally { setSaving(false); }
  }

  async function remove(id: number, stockSymbol: string) {
    if (!window.confirm(`Remove ${stockSymbol} from your portfolio?`)) return;
    try {
      setError("");
      await deleteHolding(id);
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to remove holding."); }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto max-w-6xl">
        <div><h1 className="text-3xl font-bold">Portfolio</h1><p className="mt-2 text-slate-600">Manage open positions separately from your transaction history.</p></div>

        <section className="mt-8 rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">Add Holding</h2>
          <p className="mt-1 text-sm text-slate-500">Use the current Indian stock autocomplete to avoid ticker mistakes.</p>
          <form onSubmit={addHolding} className="mt-5 grid gap-4 md:grid-cols-4">
            <div className="md:col-span-2"><label className="text-sm font-medium">Stock</label><StockSearch value={symbol} onChange={setSymbol} placeholder="Search TCS, IRFC, Infosys..." /></div>
            <label className="text-sm font-medium">Quantity<input type="number" min="0.0001" step="any" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="100" required className="mt-1 w-full rounded-lg border px-3 py-2.5" /></label>
            <label className="text-sm font-medium">Average buy price<input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="250" required className="mt-1 w-full rounded-lg border px-3 py-2.5" /></label>
            <button type="submit" disabled={saving} className="rounded-lg bg-slate-950 px-4 py-2.5 font-semibold text-white disabled:opacity-50 md:col-span-4 md:justify-self-end">{saving ? "Saving..." : "Add Holding"}</button>
          </form>
          {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-medium text-red-700">{error}</div>}
          {success && <div className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm font-medium text-emerald-700">{success}</div>}
        </section>

        <section className="mt-6 overflow-hidden rounded-2xl border bg-white shadow-sm">
          <div className="border-b p-5"><h2 className="text-xl font-semibold">Holdings</h2><p className="text-sm text-slate-500">Open positions used by portfolio analytics and AI features.</p></div>
          {loading ? <div className="p-8 text-slate-500">Loading holdings...</div> : holdings.length === 0 ? <div className="p-10 text-center text-slate-500">No holdings yet. Add your first stock above.</div> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr><th className="px-5 py-3">Symbol</th><th className="px-5 py-3">Quantity</th><th className="px-5 py-3">Average Buy</th><th className="px-5 py-3">Invested</th><th className="px-5 py-3">Action</th></tr></thead><tbody>{holdings.map((holding) => <tr key={holding.id} className="border-t"><td className="px-5 py-4 font-bold">{holding.symbol}</td><td className="px-5 py-4">{holding.quantity}</td><td className="px-5 py-4">₹{money(holding.average_buy_price)}</td><td className="px-5 py-4">₹{money(holding.quantity * holding.average_buy_price)}</td><td className="px-5 py-4"><button type="button" onClick={() => void remove(holding.id, holding.symbol)} className="font-semibold text-red-600 hover:underline">Remove</button></td></tr>)}</tbody></table></div>}
        </section>
      </div>
    </main>
  );
}
