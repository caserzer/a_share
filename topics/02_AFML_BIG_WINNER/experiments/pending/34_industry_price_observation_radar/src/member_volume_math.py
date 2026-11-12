import numpy as np
import pandas as pd


def volume_ratio(raw,calendar,short=21,prior=63):
    assert not raw.date.duplicated().any()
    x=raw.set_index('date').reindex(calendar)
    v=pd.to_numeric(x.volume,errors='coerce')
    valid=np.isfinite(v)&v.ge(0)&x.volume_conflict.eq(False)
    v=v.where(valid)
    recent=v.rolling(short,min_periods=short).mean()
    past=v.shift(short).rolling(prior,min_periods=prior).mean()
    return (recent/past.where(past>0)).to_numpy(float)


def score_candidates(frame,weight=.5):
    x=frame.copy()
    x['score_A']=x.r20.rank(method='average',pct=True)
    x['score_B']=(1-weight)*x.score_A+weight*x.volume_ratio.rank(method='average',pct=True)
    return x
