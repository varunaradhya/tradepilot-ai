import { useEffect, useRef, useState } from "react";
import { getFNOChain, getFNOExpiries, scanFNO, searchFNOUnderlyings, type FNOCandidate, type FNOUnderlying } from "../services/fno";

export default function FNOPage() {
  const [q, setQ] = useState("NIFTY");
  const [underlyings, setUnderlyings] = useState<FNOUnderlying[]>([]);
  const [selected, setSelected] = useState<FNOUnderlying | null>(null);
  const [expiries, setExpiries] = useState<string[]>([]);
  const [expiry, setExpiry] = useState("");
  const [direction, setDirection] = useState<"BULLISH" | "BEARISH">("BULLISH");
  const [capital, setCapital] = useState("100000");
  const [lotSize, setLotSize] = useState("1");
  const [candidates, setCandidates] = useState<FNOCandidate[]>([]);
  const [decision, setDecision] = useState<any>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [expiryLoading, setExpiryLoading] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [error, setError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    const timer = window.setTimeout(async () => {
      const query = q.trim();
      if (query.length < 2 || selected) {
        setUnderlyings([]);
        setSearchLoading(false);
        return;
      }
      setSearchLoading(true);
      try {
        const results = await searchFNOUnderlyings(query);
        if (live) setUnderlyings(results);
      } catch (e) {
        if (live) {
          setUnderlyings([]);
          setError(e instanceof Error ? e.message : "Unable to search NSE F&O underlyings.");
        }
      } finally {
        if (live) setSearchLoading(false);
      }
    }, 250);
    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [q, selected]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setUnderlyings([]);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function clearResults() {
    setCandidates([]);
    setDecision(null);
  }

  function resetDerivativeState() {
    setSelected(null);
    setExpiries([]);
    setExpiry("");
    clearResults();
  }

  async function choose(item: FNOUnderlying) {
    setSelected(item);
    setQ(item.symbol);
    setUnderlyings([]);
    setError("");
    setExpiries([]);
    setExpiry("");
    clearResults();
    setExpiryLoading(true);
    try {
      const raw = await getFNOExpiries(Number(item.security_id), item.exchange_segment);
      const list = raw?.data ?? raw;
      const nextExpiries = Array.isArray(list) ? list.filter((value): value is string => typeof value === "string") : [];
      setExpiries(nextExpiries);
      setExpiry(nextExpiries[0] ?? "");
      if (!nextExpiries.length) {
        setError(`${item.symbol} has no active option expiries available from Dhan right now.`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load option expiries.");
    } finally {
      setExpiryLoading(false);
    }
  }

  async function run() {
    const capitalValue = Number(capital);
    const lotValue = Number(lotSize);
    if (!selected) {
      setError("Select an NSE F&O underlying from the suggestions.");
      return;
    }
    if (!expiry) {
      setError("Select an active expiry before scanning.");
      return;
    }
    if (!Number.isFinite(capitalValue) || capitalValue <= 0) {
      setError("Capital must be greater than zero.");
      return;
    }
    if (!Number.isInteger(lotValue) || lotValue <= 0) {
      setError("Lot size must be a positive whole number.");
      return;
    }

    setScanLoading(true);
    setError("");
    clearResults();
    try {
      const chain = await getFNOChain(Number(selected.security_id), selected.exchange_segment, expiry);
      const rawChain = chain?.data ?? chain;
      if (!rawChain || typeof rawChain !== "object") throw new Error("Dhan returned an empty option chain.");
      const result = await scanFNO({
        underlying: {
          symbol: selected.symbol,
          name: selected.name,
          security_id: selected.security_id,
          capital: capitalValue,
          lot_size: lotValue,
        },
        direction,
        option_chain: rawChain,
      });
      setCandidates(Array.isArray(result.candidates) ? result.candidates : []);
      setDecision(result.decision);
      if (!result.candidates?.length) setError("No liquid option contracts passed the current liquidity/Greeks filters.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "F&O scan failed.");
    } finally {
      setScanLoading(false);
    }
  }

  return (
    <main className="tp-page">
      <div className="tp-live-line">F&O command center · paper-only decision engine</div>
      <header className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="tp-page-title text-4xl font-black">F&O Intelligence</h1>
          <p className="tp-page-subtitle mt-2 max-w-3xl">First-class NSE derivatives workflow: live Dhan option-chain data → liquidity/Greeks scoring → risk-sized paper decision. No live order is sent by this screen.</p>
        </div>
        <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1.5 text-[10px] font-black text-amber-300">PAPER ONLY</span>
      </header>

      <section className="mt-7 grid gap-5 xl:grid-cols-[.9fr_1.5fr]">
        <article className="tp-premium-card rounded-2xl p-5">
          <p className="tp-section-label">Underlying</p>
          <div ref={rootRef} className="relative mt-3">
            <input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                resetDerivativeState();
                setError("");
              }}
              onFocus={() => {
                if (q.trim().length >= 2 && !selected) void searchFNOUnderlyings(q).then(setUnderlyings).catch(() => undefined);
              }}
              placeholder="Search NIFTY, BANKNIFTY, TCS…"
              className="w-full rounded-xl border border-white/10 bg-white/[.03] px-4 py-3 text-sm font-bold text-white outline-none"
              autoComplete="off"
            />
            {!selected && (searchLoading || underlyings.length > 0) && (
              <div className="absolute left-0 right-0 top-14 z-30 max-h-72 overflow-y-auto rounded-xl border border-white/10 bg-slate-950 p-1 shadow-2xl">
                {searchLoading && <div className="px-3 py-3 text-xs text-slate-500">Searching active NSE F&O underlyings…</div>}
                {!searchLoading && underlyings.map((item) => (
                  <button key={`${item.exchange_segment}:${item.security_id}`} type="button" onClick={() => void choose(item)} className="w-full rounded-lg px-3 py-3 text-left hover:bg-white/5">
                    <b className="text-white">{item.symbol}</b>
                    <span className="ml-2 text-xs text-slate-500">{item.name}</span>
                  </button>
                ))}
                {!searchLoading && underlyings.length === 0 && <div className="px-3 py-3 text-xs text-slate-500">No active NSE option underlying found. Try NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, NIFTYNXT50 or an F&O stock.</div>}
              </div>
            )}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <button type="button" onClick={() => { setDirection("BULLISH"); clearResults(); }} className={`rounded-xl px-3 py-2 text-xs font-black ${direction === "BULLISH" ? "bg-emerald-400/15 text-emerald-300" : "bg-white/5 text-slate-500"}`}>CALL / BULLISH</button>
            <button type="button" onClick={() => { setDirection("BEARISH"); clearResults(); }} className={`rounded-xl px-3 py-2 text-xs font-black ${direction === "BEARISH" ? "bg-rose-400/15 text-rose-300" : "bg-white/5 text-slate-500"}`}>PUT / BEARISH</button>
          </div>

          <label className="mt-4 block text-xs font-bold text-slate-500">Expiry</label>
          <select value={expiry} onChange={(e) => { setExpiry(e.target.value); clearResults(); }} disabled={!selected || expiryLoading} className="mt-2 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">
            <option value="">{expiryLoading ? "Loading expiries…" : "Select expiry"}</option>
            {expiries.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className="text-xs font-bold text-slate-500">Capital<input inputMode="decimal" value={capital} onChange={(e) => { setCapital(e.target.value); clearResults(); }} className="mt-2 w-full rounded-xl border border-white/10 bg-white/[.03] px-3 py-2.5 text-white"/></label>
            <label className="text-xs font-bold text-slate-500">Lot size<input inputMode="numeric" value={lotSize} onChange={(e) => { setLotSize(e.target.value); clearResults(); }} className="mt-2 w-full rounded-xl border border-white/10 bg-white/[.03] px-3 py-2.5 text-white"/></label>
          </div>

          <button type="button" disabled={scanLoading || expiryLoading || !selected || !expiry} onClick={() => void run()} className="mt-5 w-full rounded-xl bg-violet-500 px-4 py-3 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-50">
            {scanLoading ? "Reading option chain…" : "Scan & size paper trade"}
          </button>
          {error && <p className="mt-3 rounded-xl bg-rose-400/10 p-3 text-xs font-semibold text-rose-200">{error}</p>}
        </article>

        <article className="tp-premium-card rounded-2xl p-5">
          <div className="flex items-center justify-between">
            <div><p className="tp-section-label">Smart contract selection</p><h2 className="mt-1 text-lg font-black text-white">Best liquid contracts</h2></div>
            {decision && <span className={`rounded-full px-3 py-1 text-[10px] font-black ${decision.decision === "QUALIFIED" ? "bg-emerald-400/10 text-emerald-300" : "bg-rose-400/10 text-rose-300"}`}>{decision.decision}</span>}
          </div>
          {decision?.contract && <div className="mt-4 grid gap-2 rounded-xl border border-violet-400/20 bg-violet-400/[.05] p-4 sm:grid-cols-4"><div><p className="tp-section-label">Contract</p><b className="text-white">{decision.contract.strike} {decision.contract.option_type}</b></div><div><p className="tp-section-label">Entry</p><b className="text-white">₹{decision.entry}</b></div><div><p className="tp-section-label">SL / Target</p><b className="text-white">₹{decision.stop} / ₹{decision.target}</b></div><div><p className="tp-section-label">Size</p><b className="text-white">{decision.quantity} ({decision.lots} lot)</b></div></div>}
          <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="text-[10px] uppercase tracking-wider text-slate-600"><tr><th className="py-3">Strike</th><th>Type</th><th>LTP</th><th>Spread</th><th>OI</th><th>Volume</th><th>IV</th><th>Delta</th><th>Score</th></tr></thead><tbody>{candidates.map((item) => <tr key={`${item.strike}-${item.option_type}-${item.security_id}`} className="border-t border-white/5"><td className="py-3 font-black text-white">{item.strike}</td><td className="font-bold">{item.option_type}</td><td>₹{Number(item.last_price).toFixed(2)}</td><td>{Number(item.score_components?.spread_percent ?? 0).toFixed(2)}%</td><td>{Number(item.oi ?? 0).toLocaleString()}</td><td>{Number(item.volume ?? 0).toLocaleString()}</td><td>{Number(item.iv ?? 0).toFixed(1)}</td><td>{Number(item.delta ?? 0).toFixed(2)}</td><td className="font-black text-violet-300">{Number(item.score ?? 0).toFixed(2)}</td></tr>)}{!candidates.length&&<tr><td colSpan={9} className="py-16 text-center text-sm text-slate-600">Select an active NSE F&O underlying and expiry, then scan the live Dhan option chain.</td></tr>}</tbody></table></div>
        </article>
      </section>

      <section className="mt-5 grid gap-4 md:grid-cols-3"><div className="tp-kpi"><p className="tp-section-label">Decision model</p><p className="mt-2 text-sm font-black text-white">Liquidity + OI + Delta + Spread + IV</p></div><div className="tp-kpi"><p className="tp-section-label">Risk model</p><p className="mt-2 text-sm font-black text-white">0.5% capital risk / trade</p></div><div className="tp-kpi"><p className="tp-section-label">Execution boundary</p><p className="mt-2 text-sm font-black text-amber-300">No live orders from this module</p></div></section>
    </main>
  );
}
