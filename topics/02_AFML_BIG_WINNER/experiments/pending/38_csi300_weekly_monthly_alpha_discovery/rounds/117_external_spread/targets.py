from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
source=here.parent/"115_liquid_peer/results/signals.parquet"
h=pd.read_parquet(source)
keys=["signal_date","instrument","year","phase","entry_idx","exit_idx","entry_date","exit_date","weight","model"]
base=h[keys].copy()
h["active_return"]=h.leader-h.reversal
h["external_spread"]=h.leader-h.slow
h["common_return"]=(h.leader+h.slow)/2-h.reversal
signals=["external_spread","common_return","active_return"]
e=h.dropna(subset=["sector",*signals]).sort_values(["signal_date","sector","reversal","instrument"]).copy()
group=["signal_date","sector"]
e["n"]=e.groupby(group).cumcount()
e["pair"]=e.n//2
pairs=e[e.n.mod(2)==0].merge(e[e.n.mod(2)==1],on=group+["pair"],suffixes=("_a","_b"),validate="1:1")
pairs=pairs[pairs.leader_peer_a.ne(pairs.leader_peer_b)].copy()
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
    if name=="external_spread":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","signals.parquet","coverage.csv"]]]})
