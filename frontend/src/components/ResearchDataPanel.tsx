import { useState } from "react";
import { api } from "../services/api";

type Props = {
  missingSymbols: string[];
  interval: string;
  onComplete: () => void;
};

type DownloadResult = {
  symbol: string;
  bars: number;
  valid: boolean;
};

function isoDate(daysAgo: number) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().slice(0, 10);
}

export default function ResearchDataPanel({ missingSymbols, interval, onComplete }: Props) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  if (!missingSymbols.length) return null;

  async function downloadMissing() {
    setLoading(true);
    setMessage("");
    setError("");
    const start = isoDate(180);
    const end = isoDate(0);
    const results: DownloadResult[] = [];
    const failures: string[] = [];

    for (const symbol of missingSymbols) {
      try {
        const result = await api.post<DownloadResult>(
          `/research/intraday?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&start=${start}&end=${end}`,
        );
        results.push(result);
      } catch (err) {
        failures.push(`${symbol}: ${err instanceof Error ? err.message : "download failed"}`);
      }
    }

    if (results.length) {
      setMessage(`Downloaded ${results.length} symbol${results.length === 1 ? "" : "s"} (${results.reduce((sum, item) => sum + item.bars, 0).toLocaleString()} bars). Re-running the scan…`);
      onComplete();
    }
    if (failures.length) {
      setError(failures.join(" · "));
    }
    setLoading(false);
  }

  return (
    <section className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-400/[.05] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.16em] text-amber-300">Data required</p>
          <p className="mt-1 text-sm font-semibold text-amber-100">{missingSymbols.join(", ")}</p>
          <p className="mt-1 text-xs text-amber-200/70">These NSE datasets are not stored locally yet. Connect Dhan in Broker Center to download the last 180 days of {interval}-minute data.</p>
        </div>
        <button type="button" onClick={() => void downloadMissing()} disabled={loading} className="shrink-0 rounded-xl bg-amber-300 px-4 py-2.5 text-xs font-black text-slate-950 disabled:cursor-not-allowed disabled:opacity-50">
          {loading ? "Downloading…" : "Download missing data"}
        </button>
      </div>
      {message && <p className="mt-3 rounded-lg bg-emerald-400/10 p-2.5 text-xs font-semibold text-emerald-200">{message}</p>}
      {error && <p className="mt-3 rounded-lg bg-rose-400/10 p-2.5 text-xs font-semibold text-rose-200">{error}</p>}
    </section>
  );
}
