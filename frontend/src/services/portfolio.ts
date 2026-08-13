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

const API_URL =
  import.meta.env.VITE_API_URL ??
  "http://localhost:8000/api/v1";

export async function getHoldings(
  token: string
): Promise<Holding[]> {
  const response = await fetch(
    `${API_URL}/portfolio/holdings`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error("Failed to load holdings");
  }

  return response.json();
}

export async function createHolding(
  token: string,
  holding: HoldingCreate
): Promise<Holding> {
  const response = await fetch(
    `${API_URL}/portfolio/holdings`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(holding),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to create holding");
  }

  return response.json();
}
