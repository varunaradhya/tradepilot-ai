import { useEffect, useState } from "react";

import {
  getPortfolioAnalytics,
  type PortfolioAnalytics,
} from "../services/analytics";

import {
  addWatchlistSymbol,
  deleteWatchlistSymbol,
  getWatchlistQuotes,
  type WatchlistQuote,
} from "../services/watchlist";
import { IntelligencePanel } from "../components/IntelligencePanel";


function money(value: number) {

  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

}


type DashboardPageProps = {
  onLogout: () => void;
};


export default function DashboardPage({ onLogout }: DashboardPageProps) {

  const [analytics, setAnalytics] =
    useState<PortfolioAnalytics | null>(null);

  const [watchlist, setWatchlist] =
    useState<WatchlistQuote[]>([]);

  const [newSymbol, setNewSymbol] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  async function loadDashboard() {

    try {

      setLoading(true);
      setError("");

      const [
        analyticsData,
        watchlistData,
      ] = await Promise.all([
        getPortfolioAnalytics(),
        getWatchlistQuotes(),
      ]);

      setAnalytics(analyticsData);
      setWatchlist(watchlistData);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load dashboard.",
      );

    } finally {

      setLoading(false);

    }

  }


  useEffect(() => {
    void loadDashboard();
  }, []);


  async function addSymbol() {

    const symbol = newSymbol.trim();

    if (!symbol) {
      return;
    }

    try {

      await addWatchlistSymbol(symbol);

      setNewSymbol("");

      await loadDashboard();

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to add symbol.",
      );

    }

  }


  async function removeSymbol(id: number) {

    try {

      await deleteWatchlistSymbol(id);

      await loadDashboard();

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to remove symbol.",
      );

    }

  }


  if (loading) {

    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <p>Loading dashboard...</p>
        </div>
      </main>
    );

  }


  if (!analytics) {
    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-2xl rounded-xl border bg-white p-8 text-center shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">TradePilot AI</h1>
          <p className="mt-3 text-slate-600">We could not load your portfolio dashboard.</p>
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
          <button type="button" onClick={() => void loadDashboard()} className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-white">Try again</button>
        </div>
      </main>
    );
  }


  const profitPositive =
    analytics.total_profit_loss >= 0;


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-7xl">

        <div className="flex items-center justify-between">

          <div>

            <h1 className="text-3xl font-bold text-slate-900">
              TradePilot AI
            </h1>

            <p className="mt-2 text-slate-600">
              Portfolio intelligence dashboard
            </p>

          </div>

          <div className="flex gap-2">
            <button type="button" onClick={() => void loadDashboard()} className="rounded-lg bg-slate-900 px-4 py-2 text-white">Refresh</button>
            <button type="button" onClick={onLogout} className="rounded-lg border border-slate-300 px-4 py-2 text-slate-700">Logout</button>
          </div>

        </div>


        {error && (

          <div className="mt-5 rounded-lg bg-red-50 p-4 text-red-700">
            {error}
          </div>

        )}


        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Invested
            </p>

            <p className="mt-2 text-2xl font-bold">
              {"\u20B9"}{money(
                analytics.total_invested
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Current Value
            </p>

            <p className="mt-2 text-2xl font-bold">
              {"\u20B9"}{money(
                analytics.current_value
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Total P/L
            </p>

            <p className="mt-2 text-2xl font-bold">
              {profitPositive ? "+" : ""}
              {"\u20B9"}{money(
                analytics.total_profit_loss
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Return
            </p>

            <p className="mt-2 text-2xl font-bold">
              {profitPositive ? "+" : ""}
              {analytics.total_return_percent.toFixed(2)}%
            </p>

          </div>

        </section>


        <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Realized P/L
            </p>

            <p className="mt-2 text-xl font-semibold">
              {"\u20B9"}{money(
                analytics.realized_profit_loss
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Unrealized P/L
            </p>

            <p className="mt-2 text-xl font-semibold">
              {"\u20B9"}{money(
                analytics.unrealized_profit_loss
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Best Performer
            </p>

            <p className="mt-2 text-xl font-semibold">
              {analytics.best_performer ?? "-"}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Worst Performer
            </p>

            <p className="mt-2 text-xl font-semibold">
              {analytics.worst_performer ?? "-"}
            </p>

          </div>

        </section>


        <section className="mt-8 rounded-xl border bg-white shadow-sm">

          <div className="border-b p-5">

            <h2 className="text-xl font-semibold">
              Holdings Performance
            </h2>

          </div>


          <div className="overflow-x-auto">

            <table className="w-full text-left text-sm">

              <thead className="bg-slate-50 text-slate-500">

                <tr>

                  <th className="px-5 py-3">
                    Symbol
                  </th>

                  <th className="px-5 py-3">
                    Quantity
                  </th>

                  <th className="px-5 py-3">
                    Invested
                  </th>

                  <th className="px-5 py-3">
                    Current
                  </th>

                  <th className="px-5 py-3">
                    P/L
                  </th>

                  <th className="px-5 py-3">
                    Return
                  </th>

                </tr>

              </thead>


              <tbody>

                {analytics.stocks.length === 0 && (
                  <tr className="border-t"><td className="px-5 py-6 text-center text-slate-500" colSpan={6}>No holdings yet.</td></tr>
                )}

                {analytics.stocks.map(
                  (stock) => (

                    <tr
                      key={stock.symbol}
                      className="border-t"
                    >

                      <td className="px-5 py-4 font-semibold">
                        {stock.symbol}
                      </td>

                      <td className="px-5 py-4">
                        {stock.quantity}
                      </td>

                      <td className="px-5 py-4">
                        {"\u20B9"}{money(
                          stock.invested_amount
                        )}
                      </td>

                      <td className="px-5 py-4">
                        {"\u20B9"}{money(
                          stock.current_value
                        )}
                      </td>

                      <td className="px-5 py-4">
                        {"\u20B9"}{money(
                          stock.unrealized_profit_loss
                        )}
                      </td>

                      <td className="px-5 py-4">
                        {stock.unrealized_profit_loss_percent.toFixed(2)}%
                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        </section>


        <section className="mt-8 rounded-xl border bg-white shadow-sm">

          <div className="flex flex-col gap-4 border-b p-5 md:flex-row md:items-center md:justify-between">

            <div>

              <h2 className="text-xl font-semibold">
                Watchlist
              </h2>

              <p className="text-sm text-slate-500">
                Track stocks before you buy.
              </p>

            </div>


            <div className="flex gap-2">

              <input
                value={newSymbol}
                onChange={(event) =>
                  setNewSymbol(
                    event.target.value
                  )
                }
                placeholder="TCS"
                className="rounded-lg border px-3 py-2"
              />

              <button
                type="button"
                onClick={() => void addSymbol()}
                className="rounded-lg bg-slate-900 px-4 py-2 text-white"
              >
                Add
              </button>

            </div>

          </div>


          {watchlist.length === 0 ? (

            <div className="p-8 text-center text-slate-500">
              Your watchlist is empty.
            </div>

          ) : (

            <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-4">

              {watchlist.map(
                (item) => (

                  <div
                    key={item.id}
                    className="rounded-lg border p-4"
                  >

                    <div className="flex items-center justify-between">

                      <span className="font-semibold">
                        {item.symbol}
                      </span>

                      <button
                        type="button"
                        onClick={() =>
                          void removeSymbol(
                            item.id
                          )
                        }
                        className="text-xs text-red-600"
                      >
                        Remove
                      </button>

                    </div>

                    <p className="mt-3 text-xl font-bold">
                      {"\u20B9"}{money(item.price)}
                    </p>

                    <p className="mt-1 text-sm">
                      {item.change >= 0 ? "+" : ""}
                      {money(item.change)}
                      {" "}
                      (
                      {item.change_percent >= 0 ? "+" : ""}
                      {item.change_percent.toFixed(2)}%
                      )
                    </p>

                  </div>

                )
              )}

            </div>

          )}

        </section>

        <IntelligencePanel />

      </div>

    </main>
  );
}
