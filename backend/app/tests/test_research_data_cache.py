from app.services.research_data_cache import ResearchDataCache

def test_research_cache_round_trip(tmp_path):
    db=tmp_path/'market.sqlite'
    with ResearchDataCache(db) as cache:
        cache.dataset('ds','Dhan','5','2021-01-01','2021-02-01',{'strikes':['ATM']})
        cache.put_spot([{'timestamp':1,'open':1,'high':2,'low':0.5,'close':1.5,'volume':10}])
        cache.put_options([{'timestamp':1,'side':'ce','strike_key':'ATM','strike':100,'open':5,'high':6,'low':4,'close':5.5,'volume':100,'oi':200,'iv':15,'spot':100}])
        assert cache.counts()=={'spot_bars':1,'option_rows':1,'windows':0}
        assert not cache.done('ds','w1'); cache.mark_done('ds','w1'); assert cache.done('ds','w1')
        assert cache.option_rows({'ATM'})[0]['strike']==100
