import { api } from "./api";

export type FNOUnderlying={security_id:string;exchange_segment:string;symbol:string;name:string};
export type FNOCandidate={strike:number;option_type:"CE"|"PE";security_id:number|string|null;last_price:number;bid:number;ask:number;volume:number;oi:number;iv:number;delta:number;gamma:number;theta:number;vega:number;score:number;score_components:Record<string,number>};
export type FNOPaperPosition={id:number;symbol:string;underlying:string;expiry:string;strike:number;option_type:"CE"|"PE";security_id:string;quantity:number;entry_price:number;last_price:number|null;stop_price:number;target_price:number;pnl:number;status:"OPEN"|"CLOSED";reason:string|null};
export async function searchFNOUnderlyings(q:string){return api.get<FNOUnderlying[]>(`/fno/underlyings?q=${encodeURIComponent(q)}`)}
export async function getFNOExpiries(underlying_security_id:number,underlying_segment="IDX_I"){return api.post<any>("/fno/expiries",{underlying_security_id,underlying_segment})}
export async function getFNOChain(underlying_security_id:number,underlying_segment:string,expiry:string){return api.post<any>("/fno/chain",{underlying_security_id,underlying_segment,expiry})}
export async function scanFNO(payload:{underlying:Record<string,unknown>;direction:"BULLISH"|"BEARISH";option_chain:Record<string,unknown>;config?:Record<string,unknown>}){return api.post<{candidates:FNOCandidate[];decision:any;mode:string}>("/fno/scan",payload)}
export async function openFNOPaper(decision:any,strategy_version="V1"){return api.post<{mode:string;position:FNOPaperPosition}>("/fno/paper/open",{decision,strategy_version})}
export async function getFNOPaperPositions(){return api.get<{mode:string;market_connected:boolean;positions:FNOPaperPosition[]}>("/fno/paper/positions")}
export async function closeFNOPaper(trade_id:number,exit_price:number){return api.post<{mode:string;position:any}>(`/fno/paper/positions/${trade_id}/close?exit_price=${encodeURIComponent(exit_price)}`,{})}
