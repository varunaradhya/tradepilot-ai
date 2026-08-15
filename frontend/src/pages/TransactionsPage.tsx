import { FormEvent, useEffect, useState } from "react";

import {
  createTransaction,
  getTransactions,
  type Transaction,
  type TransactionListResponse,
} from "../services/transactions";


type TransactionsPageProps = {
  onBack: () => void;
};

function money(value: number) {
  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function TransactionsPage({ onBack }: TransactionsPageProps) {
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [symbol, setSymbol] = useState("");
  const [type, setType] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function loadTransactions() {
    try {
      setLoading(true);
      setError("");
      setData(await getTransactions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load transactions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTransactions();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const normalizedSymbol = symbol.trim().toUpperCase();
    const parsedQuantity = Number(quantity);
    const parsedPrice = Number(price);

    if (!normalizedSymbol) {
      setError("Enter a stock symbol.");
      return;
    }
    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) {
      setError("Quantity must be greater than zero.");
      return;
    }
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) {
      setError("Price must be greater than zero.");
      return;
    }

    try {
      setSaving(true);
      await createTransaction({
        symbol: normalizedSymbol,
        transaction_type: type,
        quantity: parsedQuantity,
        price: parsedPrice,
      });
      setSymbol("");
      setQuantity("");
      setPrice("");
      setSuccess(`${type} transaction added for ${normalizedSymbol}.`);
      await loadTransactions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create transaction.");
    } finally {
      setSaving(false);
    }
  }

  const transactions: Transaction[] = data?.transactions ?? [];

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Transactions</h1>
            <p className="mt-2 text-slate-600">Record your BUY and SELL transactions.</p>
          </div>
          <button type="button" onClick={onBack} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-700">
            Back to Dashboard
          </button>
        </div>

        <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">Add Transaction</h2>
          <p className="mt-1 text-sm text-slate-500">Adding a BUY or SELL immediately updates your holding balance.</p>
          <form onSubmit={handleSubmit} className="mt-5 grid gap-4 md:grid-cols-5">
            <label className="text-sm text-slate-600">
              Symbol
              <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="TCS" required maxLength={20} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 uppercase" />
            </label>
            <label className="text-sm text-slate-600">
              Type
              <select value={type} onChange={(event) => setType(event.target.value as "BUY" | "SELL")} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>
            </label>
            <label className="text-sm text-slate-600">
              Quantity
              <input type="number" min="0.0001" step="any" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="10" required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </label>
            <label className="text-sm text-slate-600">
              Price (₹)
              <input type="number" min="0.01" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} placeholder="3000" required className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </label>
            <button type="submit" disabled={saving} className="self-end rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50">
              {saving ? "Saving..." : "Add Transaction"}
            </button>
          </form>
          {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-red-700">{error}</div>}
          {success && <div className="mt-4 rounded-lg bg-green-50 p-3 text-green-700">{success}</div>}
        </section>

        <section className="mt-8 grid gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Transactions</p><p className="mt-2 text-2xl font-bold">{data?.summary.total_transactions ?? 0}</p></div>
          <div className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Total BUY Value</p><p className="mt-2 text-2xl font-bold">₹{money(data?.summary.total_buy_value ?? 0)}</p></div>
          <div className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Total SELL Value</p><p className="mt-2 text-2xl font-bold">₹{money(data?.summary.total_sell_value ?? 0)}</p></div>
          <div className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Realized P/L</p><p className="mt-2 text-2xl font-bold">₹{money(data?.summary.realized_profit_loss ?? 0)}</p></div>
        </section>

        <section className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-5"><h2 className="text-xl font-semibold">Transaction History</h2></div>
          {loading ? (
            <div className="p-6 text-slate-500">Loading transactions...</div>
          ) : transactions.length === 0 ? (
            <div className="p-8 text-center text-slate-500">No transactions yet. Add your first trade above.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500"><tr><th className="px-5 py-3">Date</th><th className="px-5 py-3">Symbol</th><th className="px-5 py-3">Type</th><th className="px-5 py-3">Quantity</th><th className="px-5 py-3">Price</th><th className="px-5 py-3">Value</th></tr></thead>
                <tbody>
                  {transactions.map((transaction) => (
                    <tr key={transaction.id} className="border-t border-slate-100">
                      <td className="px-5 py-4">{new Date(transaction.transaction_date).toLocaleString("en-IN")}</td>
                      <td className="px-5 py-4 font-semibold">{transaction.symbol}</td>
                      <td className={`px-5 py-4 font-semibold ${transaction.transaction_type === "BUY" ? "text-green-700" : "text-red-700"}`}>{transaction.transaction_type}</td>
                      <td className="px-5 py-4">{transaction.quantity}</td>
                      <td className="px-5 py-4">₹{money(transaction.price)}</td>
                      <td className="px-5 py-4">₹{money(transaction.quantity * transaction.price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
