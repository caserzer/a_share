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
q=pd.read_parquet(pairs)
q=q[q["median"].le(0)].copy()
scorefiles=[here.parent/n/"results/scores.parquet" for n in ["71_2018_concentration","51_earlier_replication","38_all_phases"]]
sf=pd.concat([pd.read_parquet(f,columns=["signal_date","instrument","E1_78","RANK_MSE_78"]) for f in scorefiles])
assert not sf.duplicated(["signal_date","instrument"]).any()
for field in ["entrant","leaver"]:
    right=sf.rename(columns={"instrument":field,"E1_78":"e1_"+field,"RANK_MSE_78":"rank_"+field})
    q=q.merge(right,on=["signal_date",field],validate="m:1")
assert q.rank_entrant.gt(q.rank_leaver).all()
ref=here.parent/"57_recent_industry_labels/results/scores.parquet"
previous=pd.read_parquet(ref,columns=["signal_date","instrument","RANK_MSE_78"])
for field in ["entrant","leaver"]:
    check=q.merge(previous,left_on=["signal_date",field],right_on=["signal_date","instrument"],validate="m:1")
    np.testing.assert_allclose(check["rank_"+field],check.RANK_MSE_78,atol=1e-7,rtol=0)
q=q[q.e1_entrant.notna()&q.e1_leaver.notna()&q.e1_entrant.ne(q.e1_leaver)].copy()
q["select"]=q.e1_entrant.lt(q.e1_leaver).astype(float)
q["opposite"]=1-q.select
q["uniform"]=q.groupby("signal_date").select.transform("mean")
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
    elif name=="uniform": np.testing.assert_allclose(budget,reference,atol=1e-12)
    result.append(target)
pd.concat(result).to_parquet(out/"targets.parquet",index=False)
dump(out/"target_receipt.json",{str(f):sha(f) for f in [src,pairs,ref,*scorefiles,Path(__file__),here/"PROTOCOL.md",out/"allocations.parquet",out/"targets.parquet"]})
