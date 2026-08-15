import { useEffect, useMemo, useRef, useState } from "react";

export type StockInstrument = {
  symbol: string;
  name: string;
  exchange: "NSE" | "BSE" | "NASDAQ" | "NYSE";
};

const INSTRUMENTS: StockInstrument[] = [
  ["TCS", "Tata Consultancy Services", "NSE"],
  ["INFY", "Infosys", "NSE"],
  ["RELIANCE", "Reliance Industries", "NSE"],
  ["HDFCBANK", "HDFC Bank", "NSE"],
  ["ICICIBANK", "ICICI Bank", "NSE"],
  ["SBIN", "State Bank of India", "NSE"],
  ["ITC", "ITC", "NSE"],
  ["LT", "Larsen & Toubro", "NSE"],
  ["BHARTIARTL", "Bharti Airtel", "NSE"],
  ["AXISBANK", "Axis Bank", "NSE"],
  ["KOTAKBANK", "Kotak Mahindra Bank", "NSE"],
  ["HINDUNILVR", "Hindustan Unilever", "NSE"],
  ["MARUTI", "Maruti Suzuki India", "NSE"],
  ["TATAMOTORS", "Tata Motors", "NSE"],
  ["TATASTEEL", "Tata Steel", "NSE"],
  ["SUNPHARMA", "Sun Pharmaceutical Industries", "NSE"],
  ["WIPRO", "Wipro", "NSE"],
  ["ADANIENT", "Adani Enterprises", "NSE"],
  ["ADANIPORTS", "Adani Ports & SEZ", "NSE"],
  ["ASIANPAINT", "Asian Paints", "NSE"],
  ["BAJFINANCE", "Bajaj Finance", "NSE"],
  ["BEL", "Bharat Electronics", "NSE"],
  ["COALINDIA", "Coal India", "NSE"],
  ["HCLTECH", "HCL Technologies", "NSE"],
  ["HINDALCO", "Hindalco Industries", "NSE"],
  ["JSWSTEEL", "JSW Steel", "NSE"],
  ["M&M", "Mahindra & Mahindra", "NSE"],
  ["NTPC", "NTPC", "NSE"],
  ["ONGC", "Oil & Natural Gas Corporation", "NSE"],
  ["POWERGRID", "Power Grid Corporation", "NSE"],
  ["TITAN", "Titan Company", "NSE"],
  ["ULTRACEMCO", "UltraTech Cement", "NSE"],
  ["ZOMATO", "Eternal (Zomato)", "NSE"],
  ["AAPL", "Apple", "NASDAQ"],
  ["MSFT", "Microsoft", "NASDAQ"],
  ["NVDA", "NVIDIA", "NASDAQ"],
  ["AMZN", "Amazon", "NASDAQ"],
  ["GOOGL", "Alphabet", "NASDAQ"],
  ["META", "Meta Platforms", "NASDAQ"],
  ["TSLA", "Tesla", "NASDAQ"],
].map(([symbol, name, exchange]) => ({ symbol, name, exchange } as StockInstrument));

type StockSearchProps = {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (instrument: StockInstrument) => void;
  placeholder?: string;
  className?: string;
};

export default function StockSearch({ value, onChange, onSelect, placeholder = "Search stocks...", className = "" }: StockSearchProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const query = value.trim().toLowerCase();

  const matches = useMemo(() => {
    if (!query) return INSTRUMENTS.slice(0, 8);
    return INSTRUMENTS.filter((item) =>
      item.symbol.toLowerCase().includes(query) || item.name.toLowerCase().includes(query),
    ).slice(0, 8);
  }, [query]);

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  return (
    <div ref={rootRef} className="relative">
      <input
        value={value}
        onChange={(event) => { onChange(event.target.value.toUpperCase()); setOpen(true); }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        autoComplete="off"
        className={className || "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"}
      />
      {open && matches.length > 0 && (
        <div className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
          {matches.map((item) => (
            <button
              type="button"
              key={`${item.exchange}:${item.symbol}`}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => { onChange(item.symbol); onSelect?.(item); setOpen(false); }}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
            >
              <span>
                <span className="block font-semibold text-slate-900">{item.symbol}</span>
                <span className="block text-xs text-slate-500">{item.name}</span>
              </span>
              <span className="rounded bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">{item.exchange}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
