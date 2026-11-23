from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E
from core import sha,dump
out=here/"results";rows=[];risk=[];files=[out/"fit_receipt.json",out/"target_receipt.json",Path(__file__)]
for mode in ["original","flat","half","flat_archive","half_archive","flat_csv"]:
    d=out/mode;files.append(d/"receipt.json")
    w=pd.read_parquet(d/"windows.parquet");a=pd.read_parquet(d/"accounts.parquet");daily=pd.read_parquet(d/"daily.parquet")
    v=w.pivot(index=["phase","cost","signal_date"],columns="model",values="net").dropna()
    v["benchmark"]=w.groupby(["phase","cost","signal_date"]).benchmark.first().reindex(v.index)
    months=[]
    for (ph,name),g in daily.groupby(["phase","model"]):
        g=g.sort_values("date")
        b=(1+g.nav.pct_change().fillna(g.nav.iloc[0]-1)).groupby(g.date.dt.to_period("M")).prod().iloc[1:-1]-1
        months.append(b.rename("net").rename_axis("month").reset_index().assign(phase=ph,model=name))
        end=g.nav.iloc[-1];risk.append(dict(mode=mode,phase=ph,model=name,nav=end,cagr=end**(252/(len(g)-1))-1 if a[(a.phase==ph)&(a.model==name)].complete.all() else np.nan,mdd=(g.nav/g.nav.cummax().clip(lower=1)-1).min()))
    mon=pd.concat(months).pivot(index=["phase","month"],columns="model",values="net")
    for other in ["linear","passive",R,E,"benchmark"]:
        p=(v.matched-v[other]).groupby(level=["phase","cost"]).mean().unstack()*1e4
        st=dict(mode=mode,ref=other,n=len(v.xs("base",level="cost")),complete=a.complete.sum(),base=p.base.mean(),zero=p.zero.mean(),double=p.double.mean(),positive=p.base.gt(0).sum())
        if other in mon and "matched" in mon:
            b=(mon.matched-mon[other]).unstack(0).dropna().mean(axis=1)*1e4
            if len(b)>3:
                n=len(b);idx=np.random.default_rng(3871).integers(n,size=(12000,(n+2)//3))
                idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
                lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975])
                st.update(months=n,monthly=b.mean(),lo=lo,hi=hi,ex3=b.drop(b.nlargest(3).index).mean())
        rows.append(st)
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);pd.DataFrame(risk).to_csv(out/"risk.csv",index=False)
print(s[s.ref.isin(["linear","passive","benchmark"])].round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"summary.csv",out/"risk.csv"]})
