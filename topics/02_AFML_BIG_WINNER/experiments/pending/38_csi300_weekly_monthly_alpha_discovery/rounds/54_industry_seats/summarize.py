from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R
from core import dump,sha
out=here/"results"
src=here.parent/"50_training_support/results"
def differences(p):
    v=pd.DataFrame(index=p.index)
    v["stock_only"]=p.stock_only-p[R]
    v["seats_only"]=p.seats_only-p[R]
    v["full"]=p.embargo-p[R]
    v["stock_share"]=(v.stock_only+v.full-v.seats_only)/2
    v["seats_share"]=v.full-v.stock_share
    return v
files=[out/"target_receipt.json",here/"replay.py",Path(__file__),src/"paired.csv",src/"monthly.csv",here.parent/"38_all_phases/ship_action.py",here.parent/"21_dual_support/account.py"]
for filename,keys,col,ref in [("windows",["scope","phase","signal_date","cost"],"net","paired"),("months",["scope","phase","month"],"pnl","monthly")]:
    rows=[]
    for phase in range(10):
        for root in [src,out]:
            f=root/str(phase)/(filename+".csv");files.append(f)
            d=pd.read_csv(f);rows.append(d.assign(phase=phase))
    p=pd.concat(rows).pivot(index=keys,columns="model",values=col)
    old=pd.read_csv(src/(ref+".csv")).query('comparison=="delay"').set_index(keys).delta
    v=differences(p).loc[old.index].sort_index()
    assert v.notna().all().all()
    np.testing.assert_allclose(v.full,old.sort_index(),atol=1e-12)
    v.to_csv(out/(ref+".csv"));files.append(out/(ref+".csv"))
w=pd.read_csv(out/"paired.csv");m=pd.read_csv(out/"monthly.csv")
stats=[]
for scope,g in w.groupby("scope"):
    for name in ["full","stock_only","seats_only","stock_share","seats_share"]:
        a=g.groupby(["phase","cost"])[name].mean().unstack()*1e4
        b=m[m.scope==scope].pivot(index="month",columns="phase",values=name).dropna().mean(axis=1)*1e4
        n=len(b);idx=np.random.default_rng(3854).integers(n,size=(15000,(n+2)//3))
        idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
        lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975])
        stats.append(dict(scope=scope,comparison=name,base=a.base.mean(),double=a.double.mean(),zero=a.zero.mean(),positive=(a.base>0).sum(),monthly=b.mean(),ex3=b.drop(b.nlargest(3).index).mean(),lo=lo,hi=hi))
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);print(s.round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"summary.csv"]})
