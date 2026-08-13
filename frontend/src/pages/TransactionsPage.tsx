import { FormEvent, useEffect, useState } from "react";

import {
  createTransaction,
  getTransactions,
  type Transaction,
  type TransactionListResponse,
} from "../services/transactions";


function money(value: number) {

  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

}


export default function TransactionsPage() {

  const [data, setData] =
    useState<TransactionListResponse | null>(null);

  const [symbol, setSymbol] =
    useState("");

  const [type, setType] =
    useState<"BUY" | "SELL">("BUY");

  const [quantity, setQuantity] =
    useState("");

  const [price, setPrice] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState("");


  async function loadTransactions() {

    try {

      setLoading(true);

      const result =
        await getTransactions();

      setData(result);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load transactions.",
      );

    } finally {

      setLoading(false);

    }

  }


  useEffect(() => {
    void loadTransactions();
  }, []);


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {

    event.preventDefault();

    setError("");
    setSaving(true);

    try {

      await createTransaction({
        symbol,
        transaction_type: type,
        quantity: Number(quantity),
        price: Number(price),
      });

      setSymbol("");
      setQuantity("");
      setPrice("");

      await loadTransactions();

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to create transaction.",
      );

    } finally {

      setSaving(false);

    }

  }


  const transactions: Transaction[] =
    data?.transactions ?? [];


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-7xl">

        <h1 className="text-3xl font-bold text-slate-900">
          Transactions
        </h1>

        <p className="mt-2 text-slate-600">
          Record your BUY and SELL transactions.
        </p>


        <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">

          <h2 className="text-xl font-semibold">
            Add Transaction
          </h2>

          <form
            onSubmit={handleSubmit}
            className="mt-5 grid gap-4 md:grid-cols-5"
          >

            <input
              value={symbol}
              onChange={(event) =>
                setSymbol(event.target.value)
              }
              placeholder="Symbol"
              required
              className="rounded-lg border border-slate-300 px-3 py-2"
            />

            <select
              value={type}
              onChange={(event) =>
                setType(
                  event.target.value as "BUY" | "SELL",
                )
              }
              className="rounded-lg border border-slate-300 px-3 py-2"
            >

              <option value="BUY">
                BUY
              </option>

              <option value="SELL">
                SELL
              </option>

            </select>

            <input
              type="number"
              min="0.0001"
              step="any"
              value={quantity}
              onChange={(event) =>
                setQuantity(event.target.value)
              }
              placeholder="Quantity"
              required
              className="rounded-lg border border-slate-300 px-3 py-2"
            />

            <input
              type="number"
              min="0.01"
              step="any"
              value={price}
              onChange={(event) =>
                setPrice(event.target.value)
              }
              placeholder="Price"
              required
              className="rounded-lg border border-slate-300 px-3 py-2"
            />

            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Add Transaction"}
            </button>

          </form>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-red-700">
              {error}
            </div>
          )}

        </section>


        <section className="mt-8 grid gap-4 md:grid-cols-3">

          <div className="rounded-xl border border-slate-200 bg-white p-5">

            <p className="text-sm text-slate-500">
              Transactions
            </p>

            <p className="mt-2 text-2xl font-bold">
              {data?.summary.total_transactions ?? 0}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5">

            <p className="text-sm text-slate-500">
              Total BUY Value
            </p>

            <p className="mt-2 text-2xl font-bold">
              â‚¹{money(
                data?.summary.total_buy_value ?? 0
              )}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5">

            <p className="text-sm text-slate-500">
              Total SELL Value
            </p>

            <p className="mt-2 text-2xl font-bold">
              â‚¹{money(
                data?.summary.total_sell_value ?? 0
              )}
            </p>

          </div>

        </section>


        <section className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 p-5">

            <h2 className="text-xl font-semibold">
              Transaction History
            </h2>

          </div>


          {loading ? (

            <div className="p-6 text-slate-500">
              Loading transactions...
            </div>

          ) : transactions.length === 0 ? (

            <div className="p-8 text-center text-slate-500">
              No transactions yet.
            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-left text-sm">

                <thead className="bg-slate-50 text-slate-500">

                  <tr>

                    <th className="px-5 py-3">
                      Date
                    </th>

                    <th className="px-5 py-3">
                      Symbol
                    </th>

                    <th className="px-5 py-3">
                      Type
                    </th>

                    <th className="px-5 py-3">
                      Quantity
                    </th>

                    <th className="px-5 py-3">
                      Price
                    </th>

                    <th className="px-5 py-3">
                      Value
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {transactions.map(
                    (transaction) => (

                      <tr
                        key={transaction.id}
                        className="border-t border-slate-100"
                      >

                        <td className="px-5 py-4">
                          {new Date(
                            transaction.transaction_date
                          ).toLocaleString()}
                        </td>

                        <td className="px-5 py-4 font-semibold">
                          {transaction.symbol}
                        </td>

                        <td className="px-5 py-4 font-semibold">
                          {transaction.transaction_type}
                        </td>

                        <td className="px-5 py-4">
                          {transaction.quantity}
                        </td>

                        <td className="px-5 py-4">
                          â‚¹{money(transaction.price)}
                        </td>

                        <td className="px-5 py-4">
                          â‚¹{money(
                            transaction.quantity
                            * transaction.price
                          )}
                        </td>

                      </tr>

                    )
                  )}

                </tbody>

              </table>

            </div>

          )}

        </section>

      </div>

    </main>
  );
}
