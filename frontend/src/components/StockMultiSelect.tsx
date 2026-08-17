import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type { StockInstrument } from "./StockSearch";

type Props = {
  value: StockInstrument[];
  onChange: (items: StockInstrument[]) => void;
  maxItems?: number;
  placeholder?: string;
  disabled?: boolean;
};

export default function StockMultiSelect({ value, onChange, maxItems = 20, placeholder = "Search and add NSE stocks...", disabled = false }: Props) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<StockInstrument[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (query.trim().length < 2) {
      setMatches([]);
      setLoading(false);
      setError("");
      return;
    }
    const current = ++requestId.current;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const results = await api.get<StockInstrument[]>(`/market/search?q=${encodeURIComponent(query.trim())}`);
        if (current === requestId.current) setMatches(results.filter((item) => !value.some((selected) => selected.symbol === item.symbol)));
      } catch (err) {
        if (current === requestId.current) {
          setMatches([]);
          setError(err instanceof Error ? err.message : "Stock search is temporarily unavailable.");
        }
      } finally {
        if (current === requestId.current) setLoading(false);
      }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [query, value]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function add(item: StockInstrument) {
    if (value.length >= maxItems || value.some((selected) => selected.symbol === item.symbol)) return;
    onChange([...value, item]);
    setQuery("");
    setMatches([]);
    setOpen(false);
  }

  function remove(symbol: string) {
    onChange(value.filter((item) => item.symbol !== symbol));
  }

  return (
    <div ref={rootRef} className="relative">
      <div className="min-h-[48px] rounded-xl border border-white/10 bg-white/[.03] p-2">
        <div className="flex flex-wrap gap-2">
          {value.map((item) => (
            <span key={item.symbol} className="inline-flex items-center gap-2 rounded-lg bg-violet-500/15 px-2.5 py-1.5 text-xs font-bold text-violet-100">
              {item.symbol}
              <button type="button" disabled={disabled} onClick={() => remove(item.symbol)} aria-label={`Remove ${item.symbol}`} className="text-violet-300 hover:text-white">×</button>
            </span>
          ))}
          <input
            value={query}
            disabled={disabled || value.length >= maxItems}
            onChange={(event) => { setQuery(event.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)}
            placeholder={value.length >= maxItems ? `Maximum ${maxItems} stocks selected` : placeholder}
            autoComplete="off"
            className="min-w-[220px] flex-1 bg-transparent px-2 py-1.5 text-sm font-semibold text-white outline-none placeholder:text-slate-600 disabled:cursor-not-allowed"
          />
        </div>
      </div>
      {open && !disabled && value.length < maxItems && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-72 overflow-y-auto rounded-xl border border-white/10 bg-slate-950 shadow-2xl">
          {query.trim().length < 2 && <div className="px-4 py-3 text-xs text-slate-500">Type at least 2 characters to search the NSE universe.</div>}
          {loading && <div className="px-4 py-3 text-xs text-slate-500">Searching current NSE instruments…</div>}
          {error && <div className="px-4 py-3 text-xs font-semibold text-amber-200">{error}</div>}
          {!loading && !error && query.trim().length >= 2 && matches.length === 0 && <div className="px-4 py-3 text-xs text-slate-500">No active NSE stock found.</div>}
          {!loading && matches.map((item) => (
            <button key={item.symbol} type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => add(item)} className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-white/5">
              <span><b className="text-white">{item.symbol}</b><span className="ml-2 text-xs text-slate-500">{item.name}</span></span>
              <span className="rounded bg-white/5 px-2 py-1 text-[10px] font-bold text-slate-500">NSE</span>
            </button>
          ))}
        </div>
      )}
      <p className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Only stocks selected from the backend instrument universe can be added.</p>
    </div>
  );
}
