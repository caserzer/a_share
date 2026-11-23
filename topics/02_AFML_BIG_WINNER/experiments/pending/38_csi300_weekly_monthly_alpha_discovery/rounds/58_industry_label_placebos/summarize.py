from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R
from core import dump,sha
out=here/"results";src=here.parent/"57_recent_industry_labels/results"
files=[Path(__file__),here/"recent.py",out/"early_receipt.json",out/"fit_receipt.json",src/"receipt.json"]
shuffles=["shuffle1","shuffle2","shuffle3"];tables=[]
for filename,key in [("windows","signal_date"),("monthly","month")]:
    keys=["scope","phase",key]+(["cost"] if key=="signal_date" else [])
    f=src/(filename+".csv");files.append(f);ref=pd.read_csv(f).set_index(keys)[[R,"within","embargo"]]
    monthly=key=="month"
    f=out/("early_months.csv" if monthly else "early_windows.csv");files.append(f)
    h=pd.read_csv(f);h["scope"]=h.year.astype(str)+"_"+h["mode"];parts=[h[h.model.isin(shuffles)]]
    for phase in range(10):
        f=out/str(phase)/("months.csv" if monthly else "windows.csv")
        files.append(f);parts.append(pd.read_csv(f).rename(columns={"pnl":"net"}).assign(phase=phase))
    v=pd.concat(parts).pivot(index=keys,columns="model",values="net")
    z=ref.join(v,how="left");assert z.notna().all().all()
    z["placebo_mean"]=z[shuffles].mean(axis=1)
    z.to_csv(out/(filename+".csv"));tables.append(z)
w,m=tables;stats=[]
for scope,g in w.groupby(level="scope"):
    for left,right in [("within","placebo_mean"),*[(k,R) for k in shuffles],("placebo_mean",R),("within",R)]:
        p=(g[left]-g[right]).groupby(level=["phase","cost"]).mean().unstack()*1e4
        b=m.loc[scope];b=(b[left]-b[right]).unstack(0).dropna().mean(axis=1)*1e4
        n=len(b);idx=np.random.default_rng(3858).integers(n,size=(15000,(n+2)//3))
        idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
        lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975])
        stats.append(dict(scope=scope,left=left,right=right,base=p.base.mean(),double=p.double.mean(),zero=p.zero.mean(),positive=(p.base>0).sum(),monthly=b.mean(),ex3=b.drop(b.nlargest(3).index).mean(),lo=lo,hi=hi))
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);print(s.query('right=="placebo_mean"').round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"windows.csv",out/"monthly.csv",out/"summary.csv"]})
