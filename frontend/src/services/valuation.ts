import { api } from "./api";

export interface ValuationHolding {
  id: number;
  symbol: string;
  quantity: number;
  average_buy_price: number;
  invested_amount: number;
  current_price: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percent: number;
}

export interface PortfolioSummary {
  total_invested: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percent: number;
  holdings_count: number;
}

export interface PortfolioValuation {
  summary: PortfolioSummary;
  holdings: ValuationHolding[];
}

export async function getPortfolioValuation(): Promise<PortfolioValuation> {
  return api.get<PortfolioValuation>("/portfolio/valuation");
}
