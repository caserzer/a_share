from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
prev=here.parent/"98_d10_frequency/results"
src=prev/"targets.parquet";pf=prev/"pairs.parquet";price=PRIVATE/"qfq_close.parquet";mf=PRIVATE/"market.parquet"
base=pd.read_parquet(src,filters=[("model","=","original")]).set_index(["signal_date","instrument"]).sort_index()
p=pd.read_parquet(pf)
c=pd.read_parquet(price);bench=pd.read_parquet(mf).close.reindex(c.index)
market=bench.pct_change(fill_method=None)
values=c.pct_change(fill_method=None)
beta=values.rolling(60,min_periods=60).cov(market).div(market.rolling(60,min_periods=60).var(),axis=0)
for side in ["high","low"]:
    i=beta.index.get_indexer(p.day);j=beta.columns.get_indexer(p[side]);assert min(i)>=0 and min(j)>=0
    p[side+"_beta"]=beta.to_numpy()[i,j]
p["difference"]=p.high_beta-p.low_beta
p=p[np.isfinite(p.difference)].copy()
p["raw"]=p.budget
exposure=p.raw*p.difference
pos=exposure.clip(lower=0).groupby(p.day).transform("sum")
neg=(-exposure.clip(upper=0)).groupby(p.day).transform("sum")
scale=np.where(exposure>0,neg/pos.where(pos>0),pos/neg.where(neg>0))
p["neutral"]=p.raw*np.where(exposure.eq(0),1,np.minimum(1,scale))
p["matched"]=p.raw*p.groupby("day").neutral.transform("sum")/p.groupby("day").raw.transform("sum")
assert p[["raw","neutral","matched"]].notna().all().all()
rows=[base.reset_index()];audit=[]
for name in ["raw","neutral","matched"]:
    a=p.rename(columns={"day":"signal_date","high":"instrument"}).set_index(["signal_date","instrument"])[name]
    b=p.rename(columns={"day":"signal_date","low":"instrument"}).set_index(["signal_date","instrument"])[name]
    delta=pd.concat([a,-b]).reindex(base.index,fill_value=0)
    w=base.weight+delta
    assert w.gt(0).all()
    np.testing.assert_allclose(w.groupby(level=0).sum(),1.,atol=1e-12)
    rows.append(base.assign(weight=w,model=name).reset_index())
    active=delta.abs().groupby(level=0).sum()/2
    exp=(p[name]*p.difference).groupby(p.day).sum().reindex(active.index,fill_value=0)
    if name=="neutral":
        np.testing.assert_allclose(exp,0.,atol=1e-12)
        same=active
    if name=="matched":np.testing.assert_allclose(same,active,atol=1e-12)
    audit.append(pd.DataFrame(dict(model=name,active=active,exposure=exp)).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.concat(audit).to_csv(out/"coverage.csv",index=False);p.to_parquet(out/"pairs.parquet",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [src,pf,price,mf,Path(__file__),here/"PROTOCOL.md",out/"targets.parquet",out/"coverage.csv",out/"pairs.parquet"]})
