from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
source=here.parent/"106_close_vwap/results/signals.parquet"
h=pd.read_parquet(source)
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date","weight","model"]
base=h[keys].copy()
fields={n:PRIVATE/(n+".parquet") for n in ["qfq_open","qfq_close","volume"]}
c,o,vol=[pd.read_parquet(fields[k]) for k in ["qfq_close","qfq_open","volume"]]
o=o.reindex_like(c);vol=vol.reindex_like(c)
prev=c.shift(1)
valid=(o>0)&(c>0)&(prev>0)&(vol>0)
day=np.log(c.where(valid)/o).rolling(20,min_periods=20).sum()
night=np.log(o.where(valid)/prev).rolling(20,min_periods=20).sum()
i=c.index.get_indexer(h.signal_date);j=c.columns.get_indexer(h.instrument)
assert min(i)>=0 and min(j)>=0
h["total"]=(day+night).to_numpy()[i,j]
h["daytime"]=(day-night).to_numpy()[i,j]
h["overnight"]=-h.daytime
signals=["daytime","overnight","total"]
e=h.dropna(subset=["sector","daytime","total"]).sort_values(["signal_date","sector","total","instrument"]).copy()
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
    if name=="daytime":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,*fields.values(),Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","signals.parquet","coverage.csv"]]]})
