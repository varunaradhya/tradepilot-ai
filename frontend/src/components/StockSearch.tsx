import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";

export type StockInstrument = {
  symbol: string;
  name: string;
  exchange: "NSE" | "BSE";
};

const POPULAR_INDIAN_STOCKS: StockInstrument[] = [
  { symbol: "TCS", name: "Tata Consultancy Services", exchange: "NSE" },
  { symbol: "RELIANCE", name: "Reliance Industries", exchange: "NSE" },
  { symbol: "INFY", name: "Infosys", exchange: "NSE" },
  { symbol: "HDFCBANK", name: "HDFC Bank", exchange: "NSE" },
  { symbol: "ICICIBANK", name: "ICICI Bank", exchange: "NSE" },
  { symbol: "SBIN", name: "State Bank of India", exchange: "NSE" },
  { symbol: "BHARTIARTL", name: "Bharti Airtel", exchange: "NSE" },
  { symbol: "ITC", name: "ITC", exchange: "NSE" },
  { symbol: "LT", name: "Larsen & Toubro", exchange: "NSE" },
  { symbol: "TATAMOTORS", name: "Tata Motors", exchange: "NSE" },
  { symbol: "HAL", name: "Hindustan Aeronautics", exchange: "NSE" },
  { symbol: "IRFC", name: "Indian Railway Finance Corporation", exchange: "NSE" },
];

type StockSearchProps = {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (instrument: StockInstrument) => void;
  placeholder?: string;
  className?: string;
};

function localFallback(query: string): StockInstrument[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return POPULAR_INDIAN_STOCKS.slice(0, 8);
  return POPULAR_INDIAN_STOCKS.filter(
    (item) =>
      item.symbol.toLowerCase().includes(normalized) ||
      item.name.toLowerCase().includes(normalized),
  ).slice(0, 8);
}

export default function StockSearch({
  value,
  onChange,
  onSelect,
  placeholder = "Search Indian stocks...",
  className = "",
}: StockSearchProps) {
  const [open, setOpen] = useState(false);
  const [matches, setMatches] = useState<StockInstrument[]>(POPULAR_INDIAN_STOCKS.slice(0, 8));
  const [highlighted, setHighlighted] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);
  const query = value.trim();
  const listId = "tradepilot-stock-search-results";

  useEffect(() => {
    if (query.length < 2) {
      setMatches(localFallback(query));
      setHighlighted(0);
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
        if (currentRequest === requestId.current) {
          setMatches(result);
          setHighlighted(0);
        }
      } catch (error) {
        if (currentRequest !== requestId.current) return;
        setMatches(localFallback(query));
        setHighlighted(0);
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

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!open || loading || matches.length === 0) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((index) => Math.min(index + 1, matches.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      select(matches[highlighted]);
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <input
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-autocomplete="list"
        aria-controls={listId}
        aria-expanded={open}
        aria-activedescendant={open && matches[highlighted] ? `${listId}-${highlighted}` : undefined}
        aria-label="Search Indian stocks"
        className={
          className ||
          "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
        }
      />
      {open && (
        <div
          id={listId}
          role="listbox"
          aria-label="Indian stock suggestions"
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        >
          {loading && <div className="px-4 py-3 text-sm text-slate-500">Searching Indian stocks…</div>}
          {!loading && matches.length === 0 && (
            <div className="px-4 py-3 text-sm text-slate-500">
              No Indian stock found for “{query}”. You can type the exact NSE symbol and use Search Indian Stock; the backend will validate it.
            </div>
          )}
          {!loading &&
            matches.map((item, index) => (
              <button
                type="button"
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === highlighted}
                key={`${item.exchange}:${item.symbol}`}
                onMouseEnter={() => setHighlighted(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => select(item)}
                className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left ${
                  index === highlighted ? "bg-slate-100" : "hover:bg-slate-50"
                }`}
              >
                <span className="min-w-0">
                  <span className="block font-semibold text-slate-900">{item.symbol}</span>
                  <span className="block truncate text-xs text-slate-500">{item.name}</span>
                </span>
                <span className="shrink-0 rounded bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">
                  {item.exchange}
                </span>
              </button>
            ))}
          {searchError && (
            <div className="border-t px-4 py-2 text-xs text-amber-700">
              Live search unavailable; showing only verified local suggestions. Exact symbols can still be submitted through the Search Indian Stock button and are validated by the backend.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
