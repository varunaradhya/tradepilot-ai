import { api } from "./api";


export interface Transaction {
  id: number;
  symbol: string;
  transaction_type: "BUY" | "SELL";
  quantity: number;
  price: number;
  transaction_date: string;
}


export interface TransactionSummary {
  total_transactions: number;
  total_buy_value: number;
  total_sell_value: number;
  realized_profit_loss: number;
}


export interface TransactionListResponse {
  transactions: Transaction[];
  summary: TransactionSummary;
}


export interface TransactionCreate {
  symbol: string;
  transaction_type: "BUY" | "SELL";
  quantity: number;
  price: number;
}


export async function createTransaction(
  transaction: TransactionCreate,
): Promise<Transaction> {

  return api.post<Transaction>(
    "/transactions",
    transaction,
  );
}


export async function getTransactions(): Promise<TransactionListResponse> {

  return api.get<TransactionListResponse>(
    "/transactions",
  );
}
