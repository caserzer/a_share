from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
source=here.parent/"98_d10_frequency/results/targets.parquet"
base=pd.read_parquet(source,filters=[("model","=","original")])
sf=[here.parent/(n+"/results/scores.parquet") for n in ["71_2018_concentration","57_recent_industry_labels"]]
scores=pd.concat([pd.read_parquet(f,columns=["signal_date","instrument",R]) for f in sf])
h=base.merge(scores,on=["signal_date","instrument"],validate="1:1")
assert len(h)==len(base)
fields={n:PRIVATE/(n+".parquet") for n in ["close","high","low","volume","money","industry"]}
prices={n:pd.read_parquet(f) for n,f in fields.items() if n!="industry"}
c,hi,lo=prices["close"],prices["high"],prices["low"]
volume,money=prices["volume"],prices["money"]
vwap=money/volume.where(volume.gt(0))
spread=hi-lo;mid=(hi+lo)/2
valid=(lo.gt(0)&spread.gt(0)&c.ge(lo)&c.le(hi)&money.gt(0)&volume.gt(0))
within=vwap.ge(lo-.01)&vwap.le(hi+.01)
ok=valid&within
vwap=vwap.clip(lower=lo,upper=hi)
signals={"vwap":c-vwap,"geometry":c-mid,"volume":mid-vwap}
i=c.index.get_indexer(h.signal_date);j=c.columns.get_indexer(h.instrument);assert min(i)>=0 and min(j)>=0
for name,raw in signals.items():
    h[name]=raw.div(spread.where(ok)).rolling(20,min_periods=20).mean().to_numpy()[i,j]
h["bad_quote_last20"]=(~valid).rolling(20).sum().to_numpy()[i,j]
h["vwap_outside_last20"]=(valid&~within).rolling(20).sum().to_numpy()[i,j]
np.testing.assert_allclose(h.vwap,h.geometry+h.volume,equal_nan=True,atol=1e-12)
ind=pd.read_parquet(fields["industry"]);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
maps=[]
for day,g in h.groupby("signal_date"):
    date=day.strftime("%Y%m%d")
    v=ind[ind.in_date.le(date)&(ind.out_date.isna()|ind.out_date.gt(date))][["instrument","l1_name"]].drop_duplicates()
    mapping=v[~v.instrument.duplicated(False)].set_index("instrument").l1_name
    maps.append(g.instrument.map(mapping))
h["sector"]=pd.concat(maps).reindex(h.index)
e=h.dropna(subset=["sector","vwap","geometry","volume"]).sort_values(["signal_date","sector",R,"instrument"],ascending=[True,True,False,True]).copy()
group=["signal_date","sector"]
e["n"]=e.groupby(group).cumcount()
e["pair"]=e.n//2
pairs=e[e.n.mod(2)==0].merge(e[e.n.mod(2)==1],on=group+["pair"],suffixes=("_a","_b"),validate="1:1")
for name in signals:pairs[name+"_diff"]=pairs[name+"_a"]-pairs[name+"_b"]
pairs=pairs[(pairs[[n+"_diff" for n in signals]].abs()>1e-12).all(axis=1)].copy()
pairs.to_parquet(out/"pairs.parquet",index=False)
h.to_parquet(out/"signals.parquet",index=False)
b=base.set_index(["signal_date","instrument"]).sort_index()
rows=[b.reset_index()]
for name in signals:
    amount=np.sign(pairs[name+"_diff"])*pairs.weight_a/2
    a=pairs.assign(delta=amount).set_index(["signal_date","instrument_a"]).delta
    z=pairs.assign(delta=-amount).set_index(["signal_date","instrument_b"]).delta
    delta=pd.concat([a,z]);delta.index.names=b.index.names;delta=delta.reindex(b.index,fill_value=0)
    wt=b.weight+delta;assert wt.gt(0).all()
    np.testing.assert_allclose(wt.groupby(level=0).sum(),1.,atol=1e-12)
    active=delta.abs().groupby(level=0).sum()/2
    if name=="vwap":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,*sf,*fields.values(),Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","signals.parquet","coverage.csv"]]]})
