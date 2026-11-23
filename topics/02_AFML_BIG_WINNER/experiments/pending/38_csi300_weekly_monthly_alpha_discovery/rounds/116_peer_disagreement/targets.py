from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,R
from core import sha,dump
prior=here.parent/"115_liquid_peer/results"
source=prior/"pairs.parquet"
target_file=prior/"targets.parquet"
base=pd.read_parquet(target_file,filters=[("model","=","original")])
pairs=pd.read_parquet(source)
pairs=pairs[np.sign(pairs.leader_diff)!=np.sign(pairs.reversal_diff)].copy()
signals=["leader","slow","reversal"]
pairs.to_parquet(out/"pairs.parquet",index=False)
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
    if name=="leader":reference=active
    else:np.testing.assert_allclose(active,reference,atol=1e-12)
    rows.append(b.assign(model=name,weight=wt).reset_index())
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
reference.rename("active").to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [source,target_file,Path(__file__),here/"PROTOCOL.md",*[out/n for n in ["targets.parquet","pairs.parquet","coverage.csv"]]]})
