import { apiRequest } from "./api";

export interface SignalResponse { symbol:string; signal:"BUY"|"HOLD"|"SELL"; confidence:number; risk_level:string; entry_price?:number|null; target_price?:number|null; stop_loss?:number|null; risk_reward?:number|null; reasons:string[]; indicators:Record<string,unknown>; }
export interface AdvancedAnalytics { concentration_percent:number; diversification_score:number; risk_summary:string; volatility_percent:number|null; maximum_drawdown_percent:number|null; unavailable_symbols:string[]; }
export interface ReconciliationResponse { broker:string; summary:{matched:number;quantity_mismatches:number;average_price_mismatches:number;missing_from_tradepilot:number;missing_from_broker:number}; }
export interface AIAnalysis {
  summary:string; market_view:string; signal:"BUY"|"HOLD"|"SELL"|"NEUTRAL"; confidence:number; reasons:string[]; risks:string[]; opportunities:string[]; watch_items:string[]; data_quality:string; limitations:string[]; generated_at:string;
  risk_level?:string|null; entry_price?:number|null; target_price?:number|null; stop_loss?:number|null; risk_reward?:number|null; indicators?:Record<string,unknown>;
}
export interface Opportunity { symbol:string; score:number; signal:"BUY"|"HOLD"|"SELL"; reasons:string[]; risks:string[]; data_quality:string; risk_score:number; }
export interface OpportunityResponse { opportunities:Opportunity[]; unavailable_symbols:string[]; data_quality:string; }
export interface TradingViewResponse { market_candidates:Opportunity[]; buy_candidates:Opportunity[]; hold_candidates:Opportunity[]; sell_candidates:Opportunity[]; strongest_momentum:Opportunity|null; highest_risk:Opportunity|null; requires_attention:Opportunity[]; unavailable_symbols:string[]; data_quality:string; disclaimer:string; }
export interface DailyBriefing { headline:string; portfolio_summary:string; risk_summary:string; top_opportunities:Opportunity[]; top_risks:string[]; watch_items:string[]; generated_at:string; }
export interface HistoryItem { id:number; analysis_type:string; symbol:string|null; provider:string; signal:string; confidence:number; summary:string; generated_at:string; }
export interface IntelligenceResponse { analysis:AIAnalysis; context_summary:Record<string,unknown>; }
export interface TradingTradeStat { symbol:string; realized_pnl:number; return_percent:number; quantity:number; sell_price:number; cost_basis:number; }
export interface TradingGeneral { realized_pnl:number; total_closed_quantity:number; winning_trades:number; losing_trades:number; breakeven_trades:number; win_rate_percent:number; average_win:number; average_loss:number; profit_factor:number|null; expectancy_per_trade:number; best_trade:TradingTradeStat|null; worst_trade:TradingTradeStat|null; largest_win_percent:number|null; largest_loss_percent:number|null; strategy_score:number; strategy_label:string; strategy_insights:string[]; loss_patterns:string[]; profit_patterns:string[]; suggested_rules:string[]; sample_size:number; disclaimer:string; }
export function getTechnicalSignal(symbol:string){return apiRequest<SignalResponse>(`/api/v1/signals/technical?symbol=${encodeURIComponent(symbol)}`);}
export function getAdvancedAnalytics(){return apiRequest<AdvancedAnalytics>("/analytics/advanced");}
export function getReconciliation(){return apiRequest<ReconciliationResponse>("/reconciliation/");}
export function getPortfolioIntelligence(){return apiRequest<IntelligenceResponse>("/intelligence/portfolio");}
export function getStockIntelligence(symbol:string){return apiRequest<IntelligenceResponse>(`/intelligence/stock/${encodeURIComponent(symbol)}`);}
export function getOpportunities(){return apiRequest<OpportunityResponse>("/intelligence/opportunities");}
export function getTradingView(){return apiRequest<TradingViewResponse>("/intelligence/trading-view");}
export function getDailyBriefing(){return apiRequest<DailyBriefing>("/intelligence/daily-briefing");}
export function getAnalysisHistory(){return apiRequest<HistoryItem[]>("/intelligence/history");}
export function getTradingGeneral(){return apiRequest<TradingGeneral>("/analytics/trading-general");}
