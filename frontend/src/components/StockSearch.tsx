import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";

export type StockInstrument = {
  symbol: string;
  name: string;
  exchange: "NSE" | "BSE";
};

const POPULAR_INDIAN_STOCKS: StockInstrument[] = [
  ["TCS", "Tata Consultancy Services", "NSE"],
  ["RELIANCE", "Reliance Industries", "NSE"],
  ["INFY", "Infosys", "NSE"],
  ["HDFCBANK", "HDFC Bank", "NSE"],
  ["ICICIBANK", "ICICI Bank", "NSE"],
  ["SBIN", "State Bank of India", "NSE"],
  ["BHARTIARTL", "Bharti Airtel", "NSE"],
  ["ITC", "ITC", "NSE"],
  ["LT", "Larsen & Toubro", "NSE"],
  ["TATAMOTORS", "Tata Motors", "NSE"],
  ["HAL", "Hindustan Aeronautics", "NSE"],
  ["IRFC", "Indian Railway Finance Corporation", "NSE"],
];

type StockSearchProps = {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (instrument: StockInstrument) => void;
  placeholder?: string;
  className?: string;
};

export default function StockSearch({
  value,
  onChange,
  onSelect,
  placeholder = "Search Indian stocks...",
  className = "",
}: StockSearchProps) {
  const [open, setOpen] = useState(false);
  const [matches, setMatches] = useState<StockInstrument[]>(POPULAR_INDIAN_STOCKS.slice(0, 8));
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);
  const query = value.trim();

  useEffect(() => {
    if (query.length < 2) {
      setMatches(query ? POPULAR_INDIAN_STOCKS.filter((item) =>
        item.symbol.toLowerCase().includes(query.toLowerCase()) || item.name.toLowerCase().includes(query.toLowerCase()),
      ).slice(0, 8) : POPULAR_INDIAN_STOCKS.slice(0, 8));
      setLoading(false);
      setSearchError("");
      return;
    }

    const currentRequest = ++requestId.current;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setSearchError("");
      try {
        const result = await api.get<StockInstrument[]>(`/market/search?q=${encodeURIComponent(query)}`);
        if (currentRequest === requestId.current) setMatches(result);
      } catch (error) {
        if (currentRequest !== requestId.current) return;
        const localMatches = POPULAR_INDIAN_STOCKS.filter((item) =>
          item.symbol.toLowerCase().includes(query.toLowerCase()) || item.name.toLowerCase().includes(query.toLowerCase()),
        ).slice(0, 8);
        setMatches(localMatches);
        setSearchError(error instanceof Error ? error.message : "Search is temporarily unavailable.");
      } finally {
        if (currentRequest === requestId.current) setLoading(false);
      }
    }, 250);

    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  function select(item: StockInstrument) {
    onChange(item.symbol);
    onSelect?.(item);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <input
        value={value}
        onChange={(event) => { onChange(event.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        autoComplete="off"
        aria-label="Search Indian stocks"
        aria-expanded={open}
        className={className || "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"}
      />
      {open && (
        <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
          {loading && <div className="px-4 py-3 text-sm text-slate-500">Searching Indian stocks…</div>}
          {!loading && matches.length === 0 && <div className="px-4 py-3 text-sm text-slate-500">No Indian stock found for “{query}”.</div>}
          {!loading && matches.map((item) => (
            <button
              type="button"
              key={`${item.exchange}:${item.symbol}`}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => select(item)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
            >
              <span className="min-w-0">
                <span className="block font-semibold text-slate-900">{item.symbol}</span>
                <span className="block truncate text-xs text-slate-500">{item.name}</span>
              </span>
              <span className="shrink-0 rounded bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">{item.exchange}</span>
            </button>
          ))}
          {searchError && <div className="border-t px-4 py-2 text-xs text-amber-700">Live search unavailable; showing local matches.</div>}
        </div>
      )}
    </div>
  );
}
