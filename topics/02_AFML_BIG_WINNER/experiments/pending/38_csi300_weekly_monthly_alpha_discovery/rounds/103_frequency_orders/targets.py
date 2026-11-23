from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE
from core import sha,dump
prev=here.parent/"98_d10_frequency/results"
src=prev/"targets.parquet"
pairfile=prev/"pairs.parquet"
t=pd.read_parquet(src,filters=[("model","in",["original","overlay"])])
base=t[t.model.eq("original")].set_index(["signal_date","instrument"]).sort_index()
full=t[t.model.eq("overlay")].set_index(["signal_date","instrument"]).weight.reindex(base.index)
p=pd.read_parquet(pairfile)
plans=base.reset_index()
previous=plans[["phase","exit_idx","instrument"]].rename(columns={"exit_idx":"entry_idx"}).assign(retained=True)
h=plans.merge(previous,on=["phase","entry_idx","instrument"],how="left",validate="1:1")
h["retained"]=h.retained.eq(True)
clocks=plans[["phase","exit_idx"]].drop_duplicates().rename(columns={"exit_idx":"entry_idx"}).assign(covered=True)
h=h.merge(clocks,on=["phase","entry_idx"],how="left",validate="m:1")
h=h.set_index(["signal_date","instrument"])
for side in ["high","low"]:
    ix=pd.MultiIndex.from_arrays([p.day,p[side]])
    p[side+"_retained"]=h.retained.reindex(ix).to_numpy()
    if side=="high":p["covered"]=h.covered.reindex(ix).eq(True).to_numpy()
p["order_type"]=np.select([~p.covered,p.high_retained & p.low_retained,~p.high_retained & ~p.low_retained],["missing","retained","new"],default="mixed")
p.to_parquet(out/"pairs.parquet",index=False)
rows=[base.reset_index()]
parts=[]
for name in ["new","retained","mixed","missing"]:
    selected=p[p.order_type.eq(name)]
    a=selected.rename(columns={"day":"signal_date","high":"instrument"}).set_index(["signal_date","instrument"]).budget
    b=selected.rename(columns={"day":"signal_date","low":"instrument"}).set_index(["signal_date","instrument"]).budget
    delta=pd.concat([a,-b]).reindex(base.index,fill_value=0)
    assert delta.groupby(level=0).sum().abs().max()<1e-12
    parts.append(delta)
    if name!="missing":rows.append(base.assign(weight=base.weight+delta,model=name).reset_index())
np.testing.assert_allclose(sum(parts),full-base.weight,atol=1e-12)
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame({n:part.abs().groupby(level=0).sum()/2 for n,part in zip(["new","retained","mixed","missing"],parts)}).to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [src,pairfile,Path(__file__),here/"PROTOCOL.md",out/"pairs.parquet",out/"coverage.csv",out/"targets.parquet"]})
