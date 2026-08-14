import { apiRequest } from "./api";

export interface SignalResponse {
  symbol: string;
  signal: "BUY" | "HOLD" | "SELL";
  confidence: number;
  risk_level: string;
  entry_price?: number | null;
  target_price?: number | null;
  stop_loss?: number | null;
  risk_reward?: number | null;
  reasons: string[];
  indicators: Record<string, unknown>;
}

export interface AdvancedAnalytics {
  concentration_percent: number;
  diversification_score: number;
  risk_summary: string;
  volatility_percent: number | null;
  maximum_drawdown_percent: number | null;
  unavailable_symbols: string[];
}

export interface ReconciliationResponse {
  broker: string;
  summary: { matched: number; quantity_mismatches: number; average_price_mismatches: number; missing_from_tradepilot: number; missing_from_broker: number };
}

export interface AIAnalysis {
  summary: string;
  market_view: string;
  signal: "BUY" | "HOLD" | "SELL" | "NEUTRAL";
  confidence: number;
  reasons: string[];
  risks: string[];
  opportunities: string[];
  watch_items: string[];
  data_quality: string;
  generated_at: string;
}

export interface IntelligenceResponse {
  analysis: AIAnalysis;
  context_summary: Record<string, unknown>;
}

export async function getTechnicalSignal(symbol: string): Promise<SignalResponse> {
  return apiRequest<SignalResponse>(
    `/api/v1/signals/technical?symbol=${encodeURIComponent(symbol)}`
  );
}

export function getAdvancedAnalytics(): Promise<AdvancedAnalytics> { return apiRequest<AdvancedAnalytics>("/analytics/advanced"); }
export function getReconciliation(): Promise<ReconciliationResponse> { return apiRequest<ReconciliationResponse>("/reconciliation"); }
export function getPortfolioIntelligence(): Promise<IntelligenceResponse> { return apiRequest<IntelligenceResponse>("/intelligence/portfolio"); }
export function getStockIntelligence(symbol: string): Promise<IntelligenceResponse> { return apiRequest<IntelligenceResponse>(`/intelligence/stock/${encodeURIComponent(symbol)}`); }
