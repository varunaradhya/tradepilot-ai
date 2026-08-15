import { api } from "./api";

export interface Holding {
  id: number;
  user_id: number;
  symbol: string;
  quantity: number;
  average_buy_price: number;
  created_at: string;
  updated_at: string;
}

export interface HoldingCreate {
  symbol: string;
  quantity: number;
  average_buy_price: number;
}

export async function getHoldings(): Promise<Holding[]> {
  return api.get<Holding[]>("/portfolio/holdings");
}

export async function createHolding(holding: HoldingCreate): Promise<Holding> {
  return api.post<Holding>("/portfolio/holdings", holding);
}

export async function updateHolding(id: number, holding: Partial<HoldingCreate>): Promise<Holding> {
  return api.put<Holding>(`/portfolio/holdings/${id}`, holding);
}

export async function deleteHolding(id: number): Promise<void> {
  return api.delete<void>(`/portfolio/holdings/${id}`);
}
