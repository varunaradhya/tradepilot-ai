from __future__ import annotations
import csv, io, time
from dataclasses import dataclass
import httpx
from app.services.instrument_master_service import INSTRUMENT_MASTER_URL

@dataclass(frozen=True)
class FNOUnderlying:
    security_id:str; exchange_segment:str; symbol:str; name:str

class FNOInstrumentMaster:
    def __init__(self,url=INSTRUMENT_MASTER_URL,ttl_seconds=86400): self.url=url; self.ttl_seconds=ttl_seconds; self.loaded_at=0.0; self.items=[]
    def load(self,force=False):
        if self.items and not force and time.time()-self.loaded_at<self.ttl_seconds:return self.items
        r=httpx.get(self.url,timeout=30); r.raise_for_status(); reader=csv.DictReader(io.StringIO(r.text)); out=[]; seen=set()
        for row in reader:
            exchange=(row.get("SEM_EXM_EXCH_ID") or row.get("EXCH_ID") or "").strip().upper(); segment=(row.get("SEM_SEGMENT") or row.get("SEGMENT") or "").strip().upper(); instrument=(row.get("SEM_INSTRUMENT_NAME") or row.get("INSTRUMENT") or "").strip().upper()
            sid=(row.get("SEM_SMST_SECURITY_ID") or row.get("SEM_SECURITY_ID") or row.get("SECURITY_ID") or "").strip(); symbol=(row.get("SEM_TRADING_SYMBOL") or row.get("SYMBOL_NAME") or "").strip().upper(); name=(row.get("SEM_CUSTOM_SYMBOL") or row.get("DISPLAY_NAME") or symbol).strip()
            if exchange!="NSE" or segment not in {"I","E"} or not sid or not symbol or symbol in seen: continue
            if segment=="I" and "INDEX" not in instrument: continue
            if segment=="E": continue
            seen.add(symbol); out.append(FNOUnderlying(sid,"IDX_I",symbol,name or symbol))
        self.items=out; self.loaded_at=time.time(); return out
    def search(self,q,limit=20):
        q=q.strip().upper()
        if not q:return []
        items=self.load(); exact=[x for x in items if x.symbol==q]; rest=[x for x in items if x.symbol!=q and (q in x.symbol or q in x.name.upper())]
        return (exact+rest)[:max(1,min(limit,50))]

fno_instrument_master=FNOInstrumentMaster()
