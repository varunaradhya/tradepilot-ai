import { api } from "./api";


export interface StockPerformance {
  symbol: string;
  quantity: number;
  invested_amount: number;
  current_value: number;
  unrealized_profit_loss: number;
  unrealized_profit_loss_percent: number;
}


export interface PortfolioAnalytics {
  total_invested: number;
  current_value: number;
  unrealized_profit_loss: number;
  unrealized_profit_loss_percent: number;
  realized_profit_loss: number;
  total_profit_loss: number;
  total_return_percent: number;
  best_performer: string | null;
  worst_performer: string | null;
  holdings_count: number;
  transactions_count: number;
  stocks: StockPerformance[];
}


export async function getPortfolioAnalytics() {

  return api.get<PortfolioAnalytics>(
    "/analytics/portfolio",
  );

}
