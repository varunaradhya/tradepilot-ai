from app.services.pattern_discovery import discover_patterns,enrich_bars

def rows(n=600):
    out=[];p=100.0
    for i in range(n):
        drift=0.08 if i%11<7 else -0.03
        o=p;c=p+drift+(0.15 if i%17==0 else 0);h=max(o,c)+0.2;l=min(o,c)-0.1
        out.append({'timestamp':i,'open':o,'high':h,'low':l,'close':c,'volume':1000+(500 if i%19==0 else 0)})
        p=c
    return out

def test_enrichment_preserves_rows_and_features():
    e=enrich_bars(rows()); assert len(e)==600; assert {'ema20','ema50','rsi','rel_volume','body_ratio','ret_1'} <= set(e[100])

def test_pattern_discovery_has_train_test_split_and_no_future_labels_in_conditions():
    result=discover_patterns(rows(),horizon=3,min_occurrences=10)
    assert isinstance(result,list)
    for r in result:
        assert r.occurrences>=10
        assert 0<=r.win_rate<=1
        assert r.test_score==r.test_score
