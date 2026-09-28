from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Sequence


def analyze_intraday_quality(rows: Sequence[dict]) -> dict:
    if not rows:
        return {"valid": False, "bars": 0, "sessions": 0, "duplicates": 0, "non_chronological": 0, "invalid_ohlc": 0, "missing_volume": 0, "large_gaps": 0, "message": "No market data"}
    timestamps=[]; duplicates=0; non_chronological=0; invalid_ohlc=0; missing_volume=0
    for row in rows:
        ts=row.get("timestamp") or row.get("time")
        timestamps.append(ts)
        try:
            o,h,l,c=map(float,(row["open"],row["high"],row["low"],row["close"]))
            if min(o,h,l,c)<=0 or h<max(o,c) or l>min(o,c) or h<l: invalid_ohlc+=1
        except (KeyError,TypeError,ValueError): invalid_ohlc+=1
        if row.get("volume") is None: missing_volume+=1
    for a,b in zip(timestamps,timestamps[1:]):
        if a is not None and b is not None and str(b)<str(a): non_chronological+=1
    counts=Counter(str(ts) for ts in timestamps if ts is not None); duplicates=sum(v-1 for v in counts.values() if v>1)
    sessions={str(row.get("session") or str(row.get("timestamp") or row.get("time"))[:10]) for row in rows}
    return {"valid":duplicates==0 and non_chronological==0 and invalid_ohlc==0,"bars":len(rows),"sessions":len(sessions),"duplicates":duplicates,"non_chronological":non_chronological,"invalid_ohlc":invalid_ohlc,"missing_volume":missing_volume,"large_gaps":0,"message":"OK" if duplicates==0 and non_chronological==0 and invalid_ohlc==0 else "Dataset requires review"}
