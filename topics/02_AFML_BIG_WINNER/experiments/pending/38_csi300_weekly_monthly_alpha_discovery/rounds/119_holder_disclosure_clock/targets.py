from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
prior=here.parent/"118_shareholder_counts/results"
source=prior/"pairs.parquet"
target=prior/"targets.parquet"
calendar=PRIVATE/"qfq_close.parquet"
days=pd.read_parquet(calendar,columns=[]).index
base=pd.read_parquet(target,filters=[("model","=","original")])
pairs=pd.read_parquet(source)
known=pairs[["known_a","known_b"]].max(axis=1)
pairs["age"]=days.get_indexer(pairs.signal_date)-days.searchsorted(known,side="right")+1
assert pairs.age.ge(1).all()
pairs.to_parquet(out/"pairs.parquet",index=False)
signals=["fresh","mirror","stale"]
b=base.set_index(["signal_date","instrument"]).sort_index()
rows=[b.reset_index()]
for name in signals:
    eligible=pairs.age.gt(10) if name=="stale" else pairs.age.le(10)
    amount=np.sign(pairs.recent_diff)*pairs.weight_a/2*eligible*(-1 if name=="mirror" else 1)
    a=pairs.assign(delta=amount).set_index(["signal_date","instrument_a"]).delta
    z=pairs.assign(delta=-amount).set_index(["signal_date","instrument_b"]).delta
    delta=pd.concat([a,z]);delta.index.names=b.index.names;delta=delta.reindex(b.index,fill_value=0)
    wt=b.weight+delta;assert wt.gt(0).all()
    np.testing.assert_allclose(wt.groupby(level=0).sum(),1.,atol=1e-12)
    active=delta.abs().groupby(level=0).sum()/2
    if name=="fresh": coverage={}
    coverage[name]=active
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame(coverage).to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,target,calendar,Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","coverage.csv"]]]})
