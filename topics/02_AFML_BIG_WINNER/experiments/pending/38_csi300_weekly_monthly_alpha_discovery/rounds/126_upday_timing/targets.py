from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
source=here.parent/"124_upday_dispersion/results/signals.parquet"
h=pd.read_parquet(source)
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date","weight","model"]
base=h[keys].copy()
fields={n:PRIVATE/(n+".parquet") for n in ["qfq_close","volume"]}
c=pd.read_parquet(fields["qfq_close"])
vol=pd.read_parquet(fields["volume"]).reindex_like(c)
ret=np.log(c.where(c>0)).diff().where(vol.gt(0)&vol.shift().gt(0))
pos=ret.clip(lower=0)
i=c.index.get_indexer(h.signal_date);j=c.columns.get_indexer(h.instrument)
total=pos.rolling(20,min_periods=20).sum()
position=np.arange(len(pos))
weighted=pos.mul(position,axis=0).rolling(20,min_periods=20).sum()
center=(weighted/total.where(total>0)).sub(position-19,axis=0)
h["timing"]=center.to_numpy()[i,j]
assert h.timing.dropna().between(-1e-8,19+1e-8).all()
h["early"]=-h.timing
h["week"]=ret.rolling(5,min_periods=5).sum().to_numpy()[i,j]
signals=["timing","week","early"]
group=["signal_date","sector"]
e=h.dropna(subset=["sector","effective",*signals]).sort_values(group+["effective","instrument"]).copy()
e["n"]=e.groupby(group).cumcount()
e["pair"]=e.n//2
pairs=e[e.n.mod(2)==0].merge(e[e.n.mod(2)==1],on=group+["pair"],suffixes=("_a","_b"),validate="1:1")
for name in signals:pairs[name+"_diff"]=pairs[name+"_a"]-pairs[name+"_b"]
pairs.to_parquet(out/"before_ties.parquet",index=False)
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
    if name=="timing":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,*fields.values(),Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["before_ties.parquet","targets.parquet","pairs.parquet","signals.parquet","coverage.csv"]]]})
