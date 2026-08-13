import { api } from "./api";

export interface Quote {
  symbol: string;
  name: string | null;
  currency: string | null;
  exchange: string | null;
  price: number;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  market_time: string | null;
}

export interface HistoricalPrice {
  timestamp: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface HistoryResponse {
  symbol: string;
  currency: string | null;
  interval: string;
  range: string;
  data: HistoricalPrice[];
}

export async function getQuote(symbol: string): Promise<Quote> {
  return api.get<Quote>(`/market/quote/${encodeURIComponent(symbol)}`);
}

export async function getHistory(
  symbol: string,
  range = "1mo",
  interval = "1d",
): Promise<HistoryResponse> {
  return api.get<HistoryResponse>(
    `/market/history/${encodeURIComponent(symbol)}?range=${range}&interval=${interval}`,
  );
}
