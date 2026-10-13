import { api } from "./api";

export interface Quote { symbol:string; name:string|null; currency:string|null; exchange:string|null; price:number; previous_close:number|null; change:number|null; change_percent:number|null; market_time:string|null; data_status:string|null; }
export interface HistoricalPrice { timestamp:string; open:number|null; high:number|null; low:number|null; close:number|null; volume:number|null; }
export interface HistoryResponse { symbol:string; currency:string|null; interval:string; range:string; data:HistoricalPrice[]; data_status:string|null; }
export interface TechnicalAnalysis { symbol:string; interval:string; range:string; data_status:string; analysis_timestamp:string; bar_count:number; indicators:Record<string,(number|null)[]>; latest:Record<string,number|null>; signal:{direction:string;conditions:string[];bullish_conditions?:number;bearish_conditions?:number;sufficient_data:boolean;[key:string]:unknown}; }
export interface StockInstrument { symbol:string; name:string; exchange:string; }

export async function getQuote(symbol:string):Promise<Quote>{return api.get<Quote>("/market/quote/"+encodeURIComponent(symbol));}
export async function getHistory(symbol:string,range="1mo",interval="1d"):Promise<HistoryResponse>{return api.get<HistoryResponse>("/market/history/"+encodeURIComponent(symbol)+"?range="+range+"&interval="+interval);}
export async function getTechnicalAnalysis(symbol:string,range="1y",interval="1d"):Promise<TechnicalAnalysis>{return api.get<TechnicalAnalysis>("/market/technical-analysis/"+encodeURIComponent(symbol)+"?range="+range+"&interval="+interval);}
