import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";

export type StockInstrument = {
  symbol: string;
  name: string;
  exchange: "NSE";
  security_id: string;
  exchange_segment: "NSE_EQ";
};

type StockSearchProps = {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (instrument: StockInstrument) => void;
  onSelectionChange?: (instrument: StockInstrument | null) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
};

export default function StockSearch({
  value,
  onChange,
  onSelect,
  onSelectionChange,
  placeholder = "Search NSE stock by name or symbol...",
  className = "",
  disabled = false,
}: StockSearchProps) {
  const [open, setOpen] = useState(false);
  const [matches, setMatches] = useState<StockInstrument[]>([]);
  const [highlighted, setHighlighted] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);
  const query = value.trim();
  const listId = "tradepilot-stock-search-results";

  useEffect(() => {
    if (query.length < 2) {
      setMatches([]);
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
        setMatches([]);
        setHighlighted(0);
        setSearchError(error instanceof Error ? error.message : "Stock search is temporarily unavailable.");
      } finally {
        if (currentRequest === requestId.current) setLoading(false);
      }
    }, 220);

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
    onSelectionChange?.(item);
    onSelect?.(item);
    setOpen(false);
  }

  function handleInputChange(nextValue: string) {
    onChange(nextValue);
    onSelectionChange?.(null);
    setOpen(true);
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
        onChange={(event) => handleInputChange(event.target.value)}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoComplete="off"
        disabled={disabled}
        role="combobox"
        aria-autocomplete="list"
        aria-controls={listId}
        aria-expanded={open}
        aria-activedescendant={open && matches[highlighted] ? `${listId}-${highlighted}` : undefined}
        aria-label="Search NSE stocks"
        className={className || "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"}
      />

      {open && !disabled && (
        <div id={listId} role="listbox" aria-label="Authoritative NSE stock suggestions" className="absolute z-50 mt-1 max-h-80 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl">
          {query.length < 2 && <div className="px-4 py-3 text-sm text-slate-500">Type at least 2 characters to search the NSE universe.</div>}
          {loading && <div className="px-4 py-3 text-sm text-slate-500">Searching the current NSE instrument master…</div>}
          {!loading && query.length >= 2 && matches.length === 0 && !searchError && <div className="px-4 py-3 text-sm text-slate-500">No active NSE stock matches “{query}”. Select a stock from the suggestions.</div>}
          {searchError && <div className="border-t bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-800">{searchError} No manual symbol submission is allowed.</div>}
          {!loading && matches.map((item, index) => (
            <button
              type="button"
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === highlighted}
              key={`${item.exchange}:${item.symbol}`}
              onMouseEnter={() => setHighlighted(index)}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => select(item)}
              className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left ${index === highlighted ? "bg-slate-100" : "hover:bg-slate-50"}`}
            >
              <span className="min-w-0">
                <span className="block font-semibold text-slate-900">{item.symbol}</span>
                <span className="block truncate text-xs text-slate-500">{item.name}</span>
              </span>
              <span className="shrink-0 rounded bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">NSE</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
