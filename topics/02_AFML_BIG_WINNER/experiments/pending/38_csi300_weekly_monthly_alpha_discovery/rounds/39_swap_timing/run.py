from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import accounts,R,PRIVATE,split
from core import sha,dump
out=here/"results";out.mkdir(exist_ok=True);accounts.OUT=out
m=accounts.Market()
source=here.parent/"38_all_phases/results/targets.parquet"
t=pd.read_parquet(source)
rows=[];instruments=[]
legs=["prior","overnight","first5","second5","post10"]
for (phase,day),g in t.groupby(["phase","signal_date"]):
    w=g.pivot(index="instrument",columns="model",values="weight").fillna(0)
    active=w.early_model-w[R]
    active=active[active.abs()>1e-12]
    e=int(g.entry_idx.iloc[0]);i=e-1;x=e+10
    rec=dict(phase=phase,scope="later" if m.days[e]>=split else "primary",signal_date=day,weight=active.clip(lower=0).sum(),pairs=(active>0).sum())
    if active.empty:
        rows.append(dict(**rec,status="no_swap",**dict.fromkeys(legs,0.)));continue
    assert np.isclose(active.sum(),0.)
    j=m.symbols.get_indexer(active.index);assert min(j)>=0
    pts=np.array([m.c[i-10,j],m.c[i,j],m.o[e,j],m.o[e+5,j],m.o[x,j]])
    good=(np.isfinite(pts)&(pts>0)).all(axis=0)&m.buy[e,j]&m.sell[e,j]&m.buy[x,j]&m.sell[x,j]
    for stock,v,b in zip(active.index,active,good):
        instruments.append(dict(phase=phase,signal_date=day,instrument=stock,active_weight=v,all_endpoints_and_gates=b))
    if not good.all():
        rows.append(dict(**rec,status="unknown",**dict.fromkeys(legs,np.nan)));continue
    ret=np.vstack([pts[1:]/pts[:-1]-1,pts[-1]/pts[2]-1])
    rows.append(dict(**rec,status="priced",**dict(zip(legs,ret@active.to_numpy()))))
z=pd.DataFrame(rows);z.to_csv(out/"windows.csv",index=False)
pd.DataFrame(instruments).to_parquet(out/"active.parquet",index=False)
records=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    h=g[g.status=="priced"]
    rec=dict(phase=phase,scope=scope,n=len(g),priced=len(h),unknown=g.status.eq("unknown").sum(),avg_budget=g.weight.mean())
    for leg in legs:
        rec[leg+"_bp"]=g[leg].mean()*1e4
        rec[leg+"_active_bp"]=h[leg].sum()/h.weight.sum()*1e4
    records.append(rec)
s=pd.DataFrame(records);s.to_csv(out/"summary.csv",index=False)
new=s[~s.phase.isin([0,5])]
print(new.groupby("scope").mean(numeric_only=True).round(3).to_string())
dump(out/"receipt.json",{str(f):sha(f) for f in [source,PRIVATE/"qfq_open.parquet",PRIVATE/"qfq_close.parquet",here/"PROTOCOL.md",Path(__file__),out/"summary.csv",out/"windows.csv",out/"active.parquet"]})
