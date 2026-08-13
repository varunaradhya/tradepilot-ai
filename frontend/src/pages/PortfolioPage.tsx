import { useEffect, useState } from "react";
import {
  createHolding,
  getHoldings,
  type Holding,
} from "../services/portfolio";

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Temporary development token source.
  // Authentication UI will replace this in the next frontend batch.
  const token = localStorage.getItem("tradepilot_access_token") ?? "";

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setError("Please login first.");
      return;
    }

    getHoldings(token)
      .then(setHoldings)
      .catch((err) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load portfolio"
        );
      })
      .finally(() => setLoading(false));
  }, [token]);

  async function addDemoHolding() {
    if (!token) {
      setError("Please login first.");
      return;
    }

    try {
      const holding = await createHolding(
        token,
        {
          symbol: "RELIANCE",
          quantity: 1,
          average_buy_price: 2500,
        }
      );

      setHoldings((current) => [
        ...current,
        holding,
      ]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to add holding"
      );
    }
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            Portfolio
          </h1>

          <p className="mt-1 text-gray-500">
            Your stock holdings
          </p>
        </div>

        <button
          onClick={addDemoHolding}
          className="rounded-lg border px-4 py-2"
        >
          Add Demo Holding
        </button>
      </div>

      {loading && (
        <p>Loading portfolio...</p>
      )}

      {error && (
        <p className="mb-4 text-red-600">
          {error}
        </p>
      )}

      {!loading && holdings.length === 0 && !error && (
        <div className="rounded-xl border p-8 text-center">
          <h2 className="text-xl font-semibold">
            No holdings yet
          </h2>

          <p className="mt-2 text-gray-500">
            Add your first stock holding.
          </p>
        </div>
      )}

      {holdings.length > 0 && (
        <div className="overflow-hidden rounded-xl border">
          <table className="w-full text-left">
            <thead className="border-b">
              <tr>
                <th className="p-4">Symbol</th>
                <th className="p-4">Quantity</th>
                <th className="p-4">
                  Average Buy Price
                </th>
              </tr>
            </thead>

            <tbody>
              {holdings.map((holding) => (
                <tr
                  key={holding.id}
                  className="border-b last:border-b-0"
                >
                  <td className="p-4 font-semibold">
                    {holding.symbol}
                  </td>

                  <td className="p-4">
                    {holding.quantity}
                  </td>

                  <td className="p-4">
                    â‚¹{holding.average_buy_price}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
