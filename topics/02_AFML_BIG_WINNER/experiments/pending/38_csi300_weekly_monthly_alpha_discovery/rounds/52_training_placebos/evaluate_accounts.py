from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
prev=here.parent/"38_all_phases"
r49=here.parent/"50_training_support/results"
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support"),str(prev)]
from evaluate import R,E,accounts,split
from ship_action import replay_with_ship_action
from core import sha,dump
out=here/"results";t=pd.read_parquet(out/"targets.parquet")
placebos=["placebo_1","placebo_2","placebo_3"]
comparisons=[(name,"embargo",name) for name in [*placebos,"average",R]]
periods=[];months=[];seats=[];inputs=[out/"training_receipt.json",out/"targets.parquet",here/"PROTOCOL.md",Path(__file__),prev/"ship_action.py"]
for phase,g in t.groupby("phase"):
    d=out/str(phase);d.mkdir(exist_ok=True);accounts.OUT=d
    replay_with_ship_action(g,d)
    w=pd.read_csv(d/"windows.csv",parse_dates=["signal_date"]);mo=pd.read_csv(d/"months.csv");a=pd.read_csv(d/"accounts.csv").set_index(["scope","cost","model"])
    assert a.valuation_complete.all()
    np.testing.assert_allclose((1+w.net).groupby([w.scope,w.cost,w.model]).prod().sort_index(),a.nav.sort_index(),atol=1e-10)
    oldfile=r49/str(phase)/"windows.csv";inputs.append(oldfile)
    h=pd.read_csv(oldfile,parse_dates=["signal_date"]).query('model!="rank_h10"')
    keys=["model","scope","cost","signal_date"]
    pd.testing.assert_series_equal(h.set_index(keys).net.sort_index(),w[~w.model.isin(placebos)].set_index(keys).net.sort_index(),atol=1e-12,rtol=0)
    for scope,sub in w.groupby("scope"):
        net=sub.pivot(index=["signal_date","cost"],columns="model",values="net")
        seg=g[(g.entry_date>=split)==(scope=="later")]
        complete=mo[(mo.scope==scope)&(mo.month>str(seg.entry_date.min().to_period("M")))&(mo.month<str(seg.exit_date.max().to_period("M")))]
        monthly=complete.pivot(index="month",columns="model",values="net" if "net" in complete.columns else "pnl")
        weights=seg.pivot(index=["signal_date","instrument"],columns="model",values="weight").fillna(0.)
        net["average"]=net[placebos].mean(axis=1)
        monthly["average"]=monthly[placebos].mean(axis=1)
        weights["average"]=weights[placebos].mean(axis=1)
        for name,left,right in comparisons:
            diff=(net[left]-net[right]).rename("delta").reset_index()
            periods.append(diff.assign(phase=phase,scope=scope,comparison=name))
            months.append((monthly[left]-monthly[right]).rename("delta").reset_index().assign(phase=phase,scope=scope,comparison=name))
            active=(weights[left]-weights[right]).abs().groupby(level=0).sum()/2
            seats.append(active.rename("active").reset_index().assign(phase=phase,scope=scope,comparison=name))
    print("verified",phase,flush=True)
w=pd.concat(periods);m=pd.concat(months);u=pd.concat(seats)
w.to_csv(out/"paired.csv",index=False);m.to_csv(out/"monthly.csv",index=False);u.to_csv(out/"active.csv",index=False)
x=w.pivot(index=["phase","scope","signal_date","cost"],columns="comparison",values="delta")
np.testing.assert_allclose(x[placebos].mean(axis=1),x.average,atol=1e-12)
rows=[]
for (scope,name),g in w.groupby(["scope","comparison"]):
    v=g.groupby(["phase","cost"]).delta.mean().unstack()*1e4
    ma=m[(m.scope==scope)&(m.comparison==name)].pivot(index="month",columns="phase",values="delta").dropna().mean(axis=1)*1e4
    budget=u[(u.scope==scope)&(u.comparison==name)]
    n=len(ma);idx=np.random.default_rng(3850).integers(n,size=(15000,(n+2)//3))
    idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
    lo,hi=np.quantile(ma.to_numpy()[idx].mean(axis=1),[.025,.975])
    rows.append(dict(scope=scope,comparison=name,base=v.base.mean(),double=v.double.mean(),zero=v.zero.mean(),positive=int(v.base.gt(0).sum()),
        active_pct=budget.groupby("phase").active.mean().mean()*100,trigger=int(budget.active.gt(1e-12).sum()),n_dates=len(budget),
        monthly=ma.mean(),ex3=ma.drop(ma.nlargest(3).index).mean(),lo=lo,hi=hi,best=",".join(ma.nlargest(3).index)))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"summary.csv",out/"paired.csv",out/"monthly.csv",out/"active.csv"]})
