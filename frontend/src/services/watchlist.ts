import { api } from "./api";


export interface WatchlistItem {
  id: number;
  symbol: string;
}


export interface WatchlistQuote {
  id: number;
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
}


export async function getWatchlist() {

  return api.get<WatchlistItem[]>(
    "/watchlist",
  );

}


export async function getWatchlistQuotes() {

  return api.get<WatchlistQuote[]>(
    "/watchlist/quotes",
  );

}


export async function addWatchlistSymbol(
  symbol: string,
) {

  return api.post<WatchlistItem>(
    "/watchlist",
    {
      symbol,
    },
  );

}


export async function deleteWatchlistSymbol(
  id: number,
) {

  return api.delete<void>(
    `/watchlist/${id}`,
  );

}
