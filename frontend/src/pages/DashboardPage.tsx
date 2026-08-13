import { useEffect, useState } from "react";

import {
  getPortfolioValuation,
  type PortfolioValuation,
} from "../services/valuation";


function money(value: number) {
  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}


export default function DashboardPage() {

  const [portfolio, setPortfolio] =
    useState<PortfolioValuation | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  async function loadDashboard() {

    setLoading(true);
    setError("");

    try {

      const result =
        await getPortfolioValuation();

      setPortfolio(result);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load portfolio.",
      );

    } finally {

      setLoading(false);

    }
  }


  useEffect(() => {
    void loadDashboard();
  }, []);


  if (loading) {

    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <p className="text-slate-600">
            Loading portfolio...
          </p>
        </div>
      </main>
    );

  }


  if (error) {

    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">

          <h1 className="text-3xl font-bold text-slate-900">
            Portfolio Dashboard
          </h1>

          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>

        </div>
      </main>
    );

  }


  if (!portfolio) {
    return null;
  }


  const {
    summary,
    holdings,
  } = portfolio;


  const profitPositive =
    summary.profit_loss >= 0;


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-7xl">

        <div className="flex items-center justify-between">

          <div>

            <h1 className="text-3xl font-bold text-slate-900">
              Portfolio Dashboard
            </h1>

            <p className="mt-2 text-slate-600">
              Track your investments and current performance.
            </p>

          </div>

          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
          >
            Refresh
          </button>

        </div>


        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Invested
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              â‚¹{money(summary.total_invested)}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Current Value
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              â‚¹{money(summary.current_value)}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Profit / Loss
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              {profitPositive ? "+" : ""}
              â‚¹{money(summary.profit_loss)}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Return
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              {profitPositive ? "+" : ""}
              {summary.profit_loss_percent.toFixed(2)}%
            </p>

          </div>

        </section>


        <section className="mt-8 rounded-xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 p-5">

            <h2 className="text-xl font-semibold text-slate-900">
              Holdings
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              {summary.holdings_count} position
              {summary.holdings_count === 1 ? "" : "s"}
            </p>

          </div>


          {holdings.length === 0 ? (

            <div className="p-8 text-center text-slate-500">
              No holdings yet.
            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-left text-sm">

                <thead className="bg-slate-50 text-slate-500">

                  <tr>

                    <th className="px-5 py-3">
                      Symbol
                    </th>

                    <th className="px-5 py-3">
                      Qty
                    </th>

                    <th className="px-5 py-3">
                      Avg. Price
                    </th>

                    <th className="px-5 py-3">
                      Current
                    </th>

                    <th className="px-5 py-3">
                      Invested
                    </th>

                    <th className="px-5 py-3">
                      Value
                    </th>

                    <th className="px-5 py-3">
                      P/L
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {holdings.map((holding) => (

                    <tr
                      key={holding.id}
                      className="border-t border-slate-100"
                    >

                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {holding.symbol}
                      </td>

                      <td className="px-5 py-4">
                        {holding.quantity}
                      </td>

                      <td className="px-5 py-4">
                        â‚¹{money(holding.average_buy_price)}
                      </td>

                      <td className="px-5 py-4">
                        â‚¹{money(holding.current_price)}
                      </td>

                      <td className="px-5 py-4">
                        â‚¹{money(holding.invested_amount)}
                      </td>

                      <td className="px-5 py-4">
                        â‚¹{money(holding.current_value)}
                      </td>

                      <td className="px-5 py-4">

                        <div>
                          {holding.profit_loss >= 0 ? "+" : ""}
                          â‚¹{money(holding.profit_loss)}
                        </div>

                        <div className="text-xs text-slate-500">
                          {holding.profit_loss_percent >= 0 ? "+" : ""}
                          {holding.profit_loss_percent.toFixed(2)}%
                        </div>

                      </td>

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
