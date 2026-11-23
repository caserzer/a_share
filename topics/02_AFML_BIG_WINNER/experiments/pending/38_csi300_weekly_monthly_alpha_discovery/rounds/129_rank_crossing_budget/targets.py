from pathlib import Path
import sys
import numpy as np
import pandas as pd

here=Path(__file__).resolve().parent
out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import accounts
from core import sha,dump
prior=here.parent/"128_rank_crossing/results"
src=prior/"targets.parquet";pairs=prior/"pairs.parquet"
base=pd.read_parquet(src,filters=[("model","=","original")])
q=pd.read_parquet(pairs).sort_values(["signal_date","median","sector"],ascending=[True,False,True]).copy()
q["select"]=q["median"].le(0).astype(float)
g=q.groupby("signal_date")
q["uniform"]=g.select.transform("mean")
q["opposite"]=g.cumcount().lt(g.select.transform("sum")).astype(float)
q.to_parquet(out/"allocations.parquet",index=False)
result=[base]
for name in ["select","uniform","opposite"]:
    w=q[name]*q.weight
    reduced=q[["signal_date","entrant"]].assign(delta=-w).rename(columns={"entrant":"instrument"})
    extra=q[["signal_date","leaver"]].assign(delta=w).rename(columns={"leaver":"instrument"})
    old=base.merge(reduced,on=["signal_date","instrument"],how="left",validate="1:1")
    old["weight"]+=old.delta.fillna(0)
    added=base.drop(columns=["instrument","weight"]).drop_duplicates().merge(extra,on="signal_date",validate="1:m").rename(columns={"delta":"weight"})
    target=pd.concat([old[base.columns],added[base.columns]])
    target=target[target.weight>0].assign(model=name)
    assert not target.duplicated(["signal_date","instrument"]).any()
    np.testing.assert_allclose(target.groupby("signal_date").weight.sum(),1,atol=1e-12)
    budget=w.groupby(q.signal_date).sum()
    if name=="select": reference=budget
    else: np.testing.assert_allclose(budget,reference,atol=1e-12)
    result.append(target)
pd.concat(result).to_parquet(out/"targets.parquet",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [src,pairs,Path(__file__),here/"PROTOCOL.md",out/"allocations.parquet",out/"targets.parquet"]})
