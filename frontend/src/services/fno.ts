import { api } from "./api";
export type FNOUnderlying={security_id:string;exchange_segment:string;symbol:string;name:string};
export type FNOCandidate={strike:number;option_type:"CE"|"PE";security_id:number|string|null;last_price:number;bid:number;ask:number;volume:number;oi:number;iv:number;delta:number;gamma:number;theta:number;vega:number;score:number;score_components:Record<string,number>};
export async function searchFNOUnderlyings(q:string){return api.get<FNOUnderlying[]>(`/fno/underlyings?q=${encodeURIComponent(q)}`)}
export async function getFNOExpiries(underlying_security_id:number,underlying_segment="IDX_I"){return api.post<any>("/fno/expiries",{underlying_security_id,underlying_segment})}
export async function getFNOChain(underlying_security_id:number,underlying_segment:string,expiry:string){return api.post<any>("/fno/chain",{underlying_security_id,underlying_segment,expiry})}
export async function scanFNO(payload:{underlying:Record<string,unknown>;direction:"BULLISH"|"BEARISH";option_chain:Record<string,unknown>;config?:Record<string,unknown>}){return api.post<{candidates:FNOCandidate[];decision:any;mode:string}>("/fno/scan",payload)}
