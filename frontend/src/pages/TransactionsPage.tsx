import { FormEvent, useEffect, useState } from "react";

import StockSearch from "../components/StockSearch";
import {
  createTransaction,
  deleteTransaction,
  getTransactions,
  updateTransaction,
  type Transaction,
  type TransactionListResponse,
} from "../services/transactions";

type TransactionsPageProps = { onBack: () => void };

function money(value: number) { return value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function localDateTimeValue(date = new Date()) {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
}

export default function TransactionsPage({ onBack }: TransactionsPageProps) {
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [symbol, setSymbol] = useState("");
  const [type, setType] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [transactionDate, setTransactionDate] = useState(localDateTimeValue());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [filter, setFilter] = useState("");

  async function loadTransactions() {
    try { setLoading(true); setError(""); setData(await getTransactions()); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load transactions."); }
    finally { setLoading(false); }
  }

  useEffect(() => { void loadTransactions(); }, []);

  function resetForm() {
    setSymbol(""); setType("BUY"); setQuantity(""); setPrice(""); setTransactionDate(localDateTimeValue()); setEditingId(null);
  }

  function startEdit(transaction: Transaction) {
    setEditingId(transaction.id);
    setSymbol(transaction.symbol);
    setType(transaction.transaction_type);
    setQuantity(String(transaction.quantity));
    setPrice(String(transaction.price));
    setTransactionDate(localDateTimeValue(new Date(transaction.transaction_date)));
    setError(""); setSuccess("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSuccess("");
    const normalizedSymbol = symbol.trim().toUpperCase();
    const parsedQuantity = Number(quantity); const parsedPrice = Number(price);
    if (!normalizedSymbol) return setError("Select or enter a stock symbol.");
    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) return setError("Quantity must be greater than zero.");
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) return setError("Price must be greater than zero.");
    try {
      setSaving(true);
      const payload = { symbol: normalizedSymbol, transaction_type: type, quantity: parsedQuantity, price: parsedPrice, transaction_date: new Date(transactionDate).toISOString() };
      if (editingId === null) {
        await createTransaction(payload);
        setSuccess(`${type} transaction added for ${normalizedSymbol}. Portfolio P/L recalculated.`);
      } else {
        await updateTransaction(editingId, payload);
        setSuccess(`Transaction #${editingId} was updated and portfolio P/L recalculated.`);
      }
      resetForm(); await loadTransactions();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save transaction."); }
    finally { setSaving(false); }
  }

  async function remove(transaction: Transaction) {
    if (!window.confirm(`Delete ${transaction.transaction_type} ${transaction.quantity} ${transaction.symbol}? This will rebuild your portfolio from the remaining transaction history.`)) return;
    try { setError(""); setSuccess(""); await deleteTransaction(transaction.id); setSuccess(`Transaction #${transaction.id} deleted. Portfolio recalculated.`); if (editingId === transaction.id) resetForm(); await loadTransactions(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to delete transaction."); }
  }

  const transactions: Transaction[] = data?.transactions ?? [];
  const visibleTransactions = transactions.filter((transaction) => !filter || transaction.symbol.toLowerCase().includes(filter.toLowerCase()) || transaction.transaction_type.toLowerCase() === filter.toLowerCase());

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-3xl font-bold">Transactions</h1><p className="mt-2 text-slate-600">Broker-style trade entry with exact historical dates.</p></div><button type="button" onClick={onBack} className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-medium text-slate-700 hover:bg-slate-50">Back to Dashboard</button></div>
        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">{editingId === null ? "Add Transaction" : `Edit Transaction #${editingId}`}</h2><p className="mt-1 text-sm text-slate-500">{editingId === null ? "Search the instrument, enter the executed quantity and price, and preserve the actual trade time." : "Correct any entered field. The portfolio is rebuilt from the complete transaction ledger after saving."}</p></div><div className="flex gap-2"><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">FIFO P/L enabled</span>{editingId !== null && <button type="button" onClick={resetForm} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700">Cancel</button>}</div></div>
          <form onSubmit={handleSubmit} className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <label className="text-sm font-medium text-slate-700 xl:col-span-2">Stock<StockSearch value={symbol} onChange={setSymbol} placeholder="Search TCS, INFY, Reliance..." /></label>
            <label className="text-sm font-medium text-slate-700">Type<select value={type} onChange={(event) => setType(event.target.value as "BUY" | "SELL")} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900"><option value="BUY">BUY</option><option value="SELL">SELL</option></select></label>
            <label className="text-sm font-medium text-slate-700">Quantity<input type="number" min="0.0001" step="any" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="10" required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label>
            <label className="text-sm font-medium text-slate-700">Execution price<input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="3000" required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label>
            <label className="text-sm font-medium text-slate-700">Trade date & time<input type="datetime-local" value={transactionDate} onChange={(event) => setTransactionDate(event.target.value)} required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label>
            <button type="submit" disabled={saving} className="self-end rounded-lg bg-slate-950 px-4 py-2.5 font-semibold text-white hover:bg-slate-800 disabled:opacity-50">{saving ? "Saving..." : editingId === null ? "Add Trade" : "Save Changes"}</button>
          </form>
          {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-medium text-red-700">{error}</div>}{success && <div className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm font-medium text-emerald-700">{success}</div>}
        </section>
        <section className="mt-6 grid gap-4 md:grid-cols-4"><div className="rounded-xl border bg-white p-5"><p className="text-sm text-slate-500">Transactions</p><p className="mt-2 text-2xl font-bold">{data?.summary.total_transactions ?? 0}</p></div><div className="rounded-xl border bg-white p-5"><p className="text-sm text-slate-500">BUY value</p><p className="mt-2 text-2xl font-bold text-slate-900">₹{money(data?.summary.total_buy_value ?? 0)}</p></div><div className="rounded-xl border bg-white p-5"><p className="text-sm text-slate-500">SELL value</p><p className="mt-2 text-2xl font-bold text-slate-900">₹{money(data?.summary.total_sell_value ?? 0)}</p></div><div className="rounded-xl border bg-white p-5"><p className="text-sm text-slate-500">Realized P/L</p><p className={`mt-2 text-2xl font-bold ${(data?.summary.realized_profit_loss ?? 0) >= 0 ? "text-emerald-700" : "text-red-700"}`}>₹{money(data?.summary.realized_profit_loss ?? 0)}</p></div></section>
        <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5"><div><h2 className="text-xl font-semibold">Trade History</h2><p className="text-sm text-slate-500">Search and audit every imported or manually entered trade.</p></div><input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter symbol or BUY/SELL" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" /></div>{loading ? <div className="p-6 text-slate-500">Loading transactions...</div> : visibleTransactions.length === 0 ? <div className="p-8 text-center text-slate-500">No matching transactions.</div> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-slate-600"><tr><th className="px-5 py-3">Date</th><th className="px-5 py-3">Symbol</th><th className="px-5 py-3">Type</th><th className="px-5 py-3">Qty</th><th className="px-5 py-3">Price</th><th className="px-5 py-3">Value</th><th className="px-5 py-3">Actions</th></tr></thead><tbody>{visibleTransactions.map((transaction) => <tr key={transaction.id} className="border-t border-slate-100 hover:bg-slate-50"><td className="px-5 py-4 text-slate-600">{new Date(transaction.transaction_date).toLocaleString("en-IN")}</td><td className="px-5 py-4 font-bold text-slate-950">{transaction.symbol}</td><td className={`px-5 py-4 font-bold ${transaction.transaction_type === "BUY" ? "text-emerald-700" : "text-red-700"}`}>{transaction.transaction_type}</td><td className="px-5 py-4">{transaction.quantity}</td><td className="px-5 py-4">₹{money(transaction.price)}</td><td className="px-5 py-4 font-medium">₹{money(transaction.quantity * transaction.price)}</td><td className="px-5 py-4"><div className="flex gap-3"><button type="button" onClick={() => startEdit(transaction)} className="font-semibold text-slate-700 hover:underline">Edit</button><button type="button" onClick={() => void remove(transaction)} className="font-semibold text-red-600 hover:underline">Delete</button></div></td></tr>)}</tbody></table></div>}</section>
      </div>
    </main>
  );
}
