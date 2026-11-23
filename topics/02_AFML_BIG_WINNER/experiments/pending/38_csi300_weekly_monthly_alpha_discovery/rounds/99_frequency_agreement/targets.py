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
assert p.score_gap.ne(0).all(),"handle equal scores separately"
rows=[base.reset_index(),base.assign(weight=full,model="overlay").reset_index()]
parts=[]
for name,match in [("agree",p.score_gap.gt(0)),("conflict",p.score_gap.lt(0))]:
    selected=p[match]
    a=selected.rename(columns={"day":"signal_date","high":"instrument"}).set_index(["signal_date","instrument"]).budget
    b=selected.rename(columns={"day":"signal_date","low":"instrument"}).set_index(["signal_date","instrument"]).budget
    delta=pd.concat([a,-b]).reindex(base.index,fill_value=0)
    assert delta.groupby(level=0).sum().abs().max()<1e-12
    parts.append(delta)
    rows.append(base.assign(weight=base.weight+delta,model=name).reset_index())
np.testing.assert_allclose(parts[0]+parts[1],full-base.weight,atol=1e-12)
pd.concat(rows).to_parquet(out/"targets.parquet",index=False)
pd.DataFrame({n:part.abs().groupby(level=0).sum()/2 for n,part in zip(["agree","conflict"],parts)}).to_csv(out/"coverage.csv")
dump(out/"target_receipt.json",{str(f):sha(f) for f in [src,pairfile,Path(__file__),here/"PROTOCOL.md",out/"coverage.csv",out/"targets.parquet"]})
