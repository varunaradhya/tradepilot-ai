from app.services.research_quality import valid_ohlc,series_quality

def test_valid_ohlc_rejects_bad_bar():
    assert valid_ohlc({'open':10,'high':12,'low':9,'close':11})
    assert not valid_ohlc({'open':10,'high':8,'low':9,'close':11})
    assert not valid_ohlc({'open':0,'high':12,'low':9,'close':11})

def test_series_quality_detects_duplicate_and_invalid():
    rows=[{'timestamp':1,'open':10,'high':12,'low':9,'close':11},{'timestamp':2,'open':10,'high':8,'low':9,'close':11},{'timestamp':2,'open':10,'high':12,'low':9,'close':11}]
    q=series_quality(rows)
    assert q['bars']==3 and q['unique_timestamps']==2 and q['duplicate_timestamps']==1 and q['invalid_ohlc']==1
