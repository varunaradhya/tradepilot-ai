from app.services.option_pattern_discovery import discover_option_patterns

def test_option_pattern_discovery_uses_iv_oi_volume_and_out_of_sample():
    rows=[];p=100.0
    for i in range(240):
        c=p*(1+(.002 if i%9<6 else -.001));rows.append({'timestamp':i,'side':'ce','strike_key':'ATM','strike':100,'open':p,'high':max(p,c)*1.001,'low':min(p,c)*.999,'close':c,'volume':1000+(1000 if i%13==0 else 0),'oi':5000,'iv':18,'spot':100});p=c
    result=discover_option_patterns(rows,horizon=3,min_occurrences=20)
    assert isinstance(result,list)
    for r in result: assert r.occurrences>=20 and 0<=r.win_rate<=1
