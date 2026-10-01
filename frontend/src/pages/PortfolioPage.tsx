import { FormEvent, useEffect, useMemo, useState } from "react";
import StockSearch from "../components/StockSearch";
import { getPortfolioAnalytics, type PortfolioAnalytics } from "../services/analytics";
import { createHolding, deleteHolding, getHoldings, updateHolding, type Holding } from "../services/portfolio";

const money = (value: number | null | undefined) =>
  value == null ? "—" : value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const signedMoney = (value: number | null | undefined) => {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : "−"}₹${money(Math.abs(value))}`;
};

function Metric({ label, value, tone = "text-white", detail }: { label: string; value: string; tone?: string; detail?: string }) {
  return (
    <div className="tp-kpi min-h-[132px]">
      <p className="tp-section-label">{label}</p>
      <p className={`tp-number mt-3 text-2xl font-black ${tone}`}>{value}</p>
      {detail && <p className="mt-2 text-[11px] font-semibold text-slate-600">{detail}</p>}
    </div>
  );
}

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [query, setQuery] = useState("");

  async function load(showSpinner = true) {
    try {
      if (showSpinner) setLoading(true);
      else setRefreshing(true);
      setError("");
      const [nextHoldings, nextAnalytics] = await Promise.all([getHoldings(), getPortfolioAnalytics()]);
      setHoldings(nextHoldings);
      setAnalytics(nextAnalytics);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load portfolio.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function resetForm() {
    setSymbol("");
    setQuantity("");
    setPrice("");
    setEditingId(null);
  }

  function startEdit(holding: Holding) {
    setEditingId(holding.id);
    setSymbol(holding.symbol);
    setQuantity(String(holding.quantity));
    setPrice(String(holding.average_buy_price));
    setError("");
    setSuccess("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function saveHolding(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");
    const normalized = symbol.trim().toUpperCase();
    const parsedQuantity = Number(quantity);
    const parsedPrice = Number(price);

    if (!normalized) return setError("Select an Indian stock.");
    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) return setError("Quantity must be greater than zero.");
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) return setError("Average buy price must be greater than zero.");

    try {
      setSaving(true);
      if (editingId === null) {
        await createHolding({ symbol: normalized, quantity: parsedQuantity, average_buy_price: parsedPrice });
        setSuccess(`${normalized} was added to your portfolio.`);
      } else {
        await updateHolding(editingId, { symbol: normalized, quantity: parsedQuantity, average_buy_price: parsedPrice });
        setSuccess(`${normalized} holding was updated.`);
      }
      resetForm();
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save holding.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: number, stockSymbol: string) {
    if (!window.confirm(`Remove ${stockSymbol} from your portfolio?`)) return;
    try {
      setError("");
      await deleteHolding(id);
      setSuccess(`${stockSymbol} was removed.`);
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove holding.");
    }
  }

  const visibleStocks = useMemo(() => {
    const term = query.trim().toUpperCase();
    return (analytics?.stocks ?? []).filter(stock => !term || stock.symbol.includes(term));
  }, [analytics, query]);

  const positive = (analytics?.total_profit_loss ?? 0) >= 0;

  return (
    <main className="tp-page">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="tp-live-line">Portfolio intelligence · paper environment</div>
          <h1 className="tp-page-title mt-2 text-4xl font-black">Portfolio</h1>
          <p className="tp-page-subtitle mt-2 max-w-2xl text-sm">
            A premium view of capital, performance, concentration and open positions. Execution remains locked to paper mode.
          </p>
        </div>
        <button type="button" onClick={() => void load(false)} disabled={refreshing} className="tp-button-secondary">
          {refreshing ? "Refreshing…" : "↻ Refresh portfolio"}
        </button>
      </header>

      {error && <div className="tp-state-error mt-5">{error}</div>}
      {success && <div className="tp-state-success mt-5">{success}</div>}

      {loading ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">{[1,2,3,4].map(i => <div key={i} className="h-32 animate-pulse rounded-2xl border border-white/10 bg-white/[.03]" />)}</div>
      ) : (
        <>
          <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Portfolio value" value={`₹${money(analytics?.current_value)}`} detail={`${analytics?.holdings_count ?? 0} open positions`} />
            <Metric label="Capital deployed" value={`₹${money(analytics?.total_invested)}`} detail={`${analytics?.transactions_count ?? 0} recorded transactions`} />
            <Metric label="Unrealized P&L" value={signedMoney(analytics?.unrealized_profit_loss)} tone={positive ? "text-emerald-300" : "text-rose-300"} detail={`${analytics?.unrealized_profit_loss_percent?.toFixed(2) ?? "—"}% open return`} />
            <Metric label="Total return" value={`${analytics?.total_return_percent == null ? "—" : `${analytics.total_return_percent >= 0 ? "+" : "−"}${Math.abs(analytics.total_return_percent).toFixed(2)}%`}`} tone={positive ? "text-emerald-300" : "text-rose-300"} detail={`Realized P&L ₹${money(analytics?.realized_profit_loss)}`} />
          </section>

          <section className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
            <div className="tp-premium-card rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="tp-section-label">Position intelligence</p>
                  <h2 className="mt-1 text-xl font-black text-white">Open positions</h2>
                </div>
                <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter symbols…" className="tp-field max-w-[190px]" aria-label="Filter portfolio symbols" />
              </div>

              {!analytics?.market_data_complete && analytics?.unavailable_symbols.length ? (
                <div className="tp-state-warning mt-4">Market data is unavailable for: {analytics.unavailable_symbols.join(", ")}. Values for those positions may be incomplete.</div>
              ) : null}

              {visibleStocks.length === 0 ? (
                <div className="tp-empty-state mt-5">No live analytics are available for this filter yet.</div>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead><tr><th className="px-3 py-3">Position</th><th className="px-3 py-3">Qty</th><th className="px-3 py-3">Avg buy</th><th className="px-3 py-3">Market value</th><th className="px-3 py-3">P&L</th><th className="px-3 py-3">Status</th></tr></thead>
                    <tbody>
                      {visibleStocks.map(stock => {
                        const up = stock.unrealized_profit_loss >= 0;
                        return (
                          <tr key={stock.symbol} className="border-t border-white/5">
                            <td className="px-3 py-4"><span className="font-black text-white">{stock.symbol}</span><span className="block text-[10px] text-slate-600">Indian equity</span></td>
                            <td className="px-3 py-4 font-semibold text-slate-300">{stock.quantity}</td>
                            <td className="px-3 py-4">₹{money(stock.invested_amount / Math.max(stock.quantity, 1))}</td>
                            <td className="px-3 py-4 font-bold text-slate-200">₹{money(stock.current_value)}</td>
                            <td className={`px-3 py-4 font-black ${up ? "text-emerald-300" : "text-rose-300"}`}>{signedMoney(stock.unrealized_profit_loss)}<span className="block text-[10px]">{stock.unrealized_profit_loss_percent.toFixed(2)}%</span></td>
                            <td className="px-3 py-4"><span className={`rounded-full px-2 py-1 text-[9px] font-black uppercase ${stock.market_data_available ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-400/10 text-amber-300"}`}>{stock.market_data_available ? "Priced" : "No quote"}</span></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="space-y-5">
              <div className="tp-premium-card rounded-2xl p-5">
                <p className="tp-section-label">Portfolio signal</p>
                <h2 className="mt-1 text-xl font-black text-white">Performance leaders</h2>
                <div className="mt-5 grid gap-3">
                  <div className="rounded-xl border border-white/5 bg-white/[.025] p-4"><p className="text-[10px] font-black uppercase tracking-wider text-slate-600">Best performer</p><p className="mt-2 text-lg font-black text-emerald-300">{analytics?.best_performer ?? "—"}</p></div>
                  <div className="rounded-xl border border-white/5 bg-white/[.025] p-4"><p className="text-[10px] font-black uppercase tracking-wider text-slate-600">Weakest performer</p><p className="mt-2 text-lg font-black text-rose-300">{analytics?.worst_performer ?? "—"}</p></div>
                </div>
                <p className="tp-action-note">Performance is based on available market data. This page does not place live orders.</p>
              </div>

              <div className="tp-premium-card rounded-2xl p-5">
                <p className="tp-section-label">Position maintenance</p>
                <h2 className="mt-1 text-xl font-black text-white">{editingId === null ? "Add a holding" : "Edit holding"}</h2>
                <form onSubmit={saveHolding} className="mt-4 space-y-3">
                  <StockSearch value={symbol} onChange={setSymbol} placeholder="Search TCS, IRFC, Infosys…" />
                  <div className="grid grid-cols-2 gap-3">
                    <label className="text-[11px] font-bold text-slate-500">Quantity<input type="number" min="0.0001" step="any" value={quantity} onChange={e => setQuantity(e.target.value)} placeholder="100" required className="tp-field mt-1" /></label>
                    <label className="text-[11px] font-bold text-slate-500">Average buy<input type="number" min="0.01" step="0.01" value={price} onChange={e => setPrice(e.target.value)} placeholder="250" required className="tp-field mt-1" /></label>
                  </div>
                  <div className="flex gap-2">
                    <button type="submit" disabled={saving} className="tp-button-primary flex-1">{saving ? "Saving…" : editingId === null ? "Add holding" : "Save changes"}</button>
                    {editingId !== null && <button type="button" onClick={resetForm} className="tp-button-secondary">Cancel</button>}
                  </div>
                </form>
                <p className="tp-action-note">Holdings are user-scoped and feed portfolio analytics and risk controls.</p>
              </div>
            </div>
          </section>

          <section className="tp-premium-card mt-5 overflow-hidden rounded-2xl">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 p-5">
              <div><p className="tp-section-label">Position registry</p><h2 className="mt-1 text-xl font-black text-white">Manage holdings</h2></div>
              <span className="text-xs font-bold text-slate-600">{holdings.length} records</span>
            </div>
            {holdings.length === 0 ? (
              <div className="tp-empty-state m-5">Your portfolio is empty. Add your first position from the panel above.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead><tr><th className="px-5 py-3">Symbol</th><th className="px-5 py-3">Quantity</th><th className="px-5 py-3">Average buy</th><th className="px-5 py-3">Invested</th><th className="px-5 py-3">Actions</th></tr></thead>
                  <tbody>
                    {holdings.map(holding => (
                      <tr key={holding.id} className="border-t border-white/5">
                        <td className="px-5 py-4 font-black text-white">{holding.symbol}</td>
                        <td className="px-5 py-4">{holding.quantity}</td>
                        <td className="px-5 py-4">₹{money(holding.average_buy_price)}</td>
                        <td className="px-5 py-4 font-bold">₹{money(holding.quantity * holding.average_buy_price)}</td>
                        <td className="px-5 py-4"><div className="flex gap-2"><button type="button" onClick={() => startEdit(holding)} className="tp-button-secondary px-3 py-2">Edit</button><button type="button" onClick={() => void remove(holding.id, holding.symbol)} className="tp-button-danger px-3 py-2">Remove</button></div></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
