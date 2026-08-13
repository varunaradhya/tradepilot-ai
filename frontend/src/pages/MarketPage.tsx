import { useState } from "react";
import { getQuote, type Quote } from "../services/market";

export default function MarketPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search() {
    const normalized = symbol.trim().toUpperCase();

    if (!normalized) {
      setError("Enter a stock symbol.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await getQuote(normalized);
      setQuote(result);
    } catch (err) {
      setQuote(null);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load market data.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-bold text-slate-900">
          Market Data
        </h1>

        <p className="mt-2 text-slate-600">
          Search a stock symbol and view its latest market price.
        </p>

        <div className="mt-6 flex gap-3">
          <input
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                void search();
              }
            }}
            placeholder="AAPL"
            className="rounded-lg border border-slate-300 bg-white px-4 py-3 uppercase outline-none focus:border-slate-500"
          />

          <button
            type="button"
            onClick={() => void search()}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-5 py-3 font-medium text-white disabled:opacity-50"
          >
            {loading ? "Loading..." : "Search"}
          </button>
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {quote && (
          <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500">
                  {quote.exchange ?? "Market"}
                </p>

                <h2 className="mt-1 text-2xl font-bold text-slate-900">
                  {quote.symbol}
                </h2>

                {quote.name && (
                  <p className="mt-1 text-slate-500">
                    {quote.name}
                  </p>
                )}
              </div>

              <div className="text-right">
                <p className="text-3xl font-bold text-slate-900">
                  {quote.price.toFixed(2)}
                </p>

                {quote.change_percent !== null && (
                  <p className="mt-1 text-sm text-slate-600">
                    {quote.change_percent >= 0 ? "+" : ""}
                    {quote.change_percent.toFixed(2)}%
                  </p>
                )}
              </div>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-sm text-slate-500">
                  Previous Close
                </p>
                <p className="mt-1 font-semibold">
                  {quote.previous_close?.toFixed(2) ?? "-"}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-500">
                  Change
                </p>
                <p className="mt-1 font-semibold">
                  {quote.change !== null
                    ? `${quote.change >= 0 ? "+" : ""}${quote.change.toFixed(2)}`
                    : "-"}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-500">
                  Currency
                </p>
                <p className="mt-1 font-semibold">
                  {quote.currency ?? "-"}
                </p>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
