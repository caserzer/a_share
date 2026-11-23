from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E
from core import sha,dump
out=here/"results";src=here.parent/"50_training_support/results"
rows=[];months=[];files=[out/"early_receipt.json",out/"fit_receipt.json",here/"recent.py",Path(__file__),here.parent/"38_all_phases/ship_action.py",here.parent/"21_dual_support/account.py"]
early=here.parent/"51_earlier_replication/results"
for name,dest,col in [("windows",rows,"signal_date"),("months",months,"month")]:
    f=out/("early_"+name+".csv");files.append(f)
    d=pd.read_csv(f);d["scope"]=d.year.astype(str)+"_"+d["mode"]
    keys=["scope","phase",col,"cost","model","net"];dest.append(d[keys])
    for year,mode in [(2019,"original"),(2020,"flat"),(2020,"half")]:
        root=early if mode=="original" else early/("sensitivity_"+mode)
        f=root/("windows.csv" if name=="windows" else "monthly.csv");files.append(f)
        a=pd.read_csv(f).query("year==@year and model==@E")
        dest.append(a.assign(scope=str(year)+"_"+mode)[keys])
    for phase in range(10):
        for root in [src,out]:
            f=root/str(phase)/(name+".csv");files.append(f);a=pd.read_csv(f)
            if name=="months":
                a=a.rename(columns={"pnl":"net"}).assign(cost="base")
                # Only complete natural months in the common reference calendar.
                cal=src/"monthly.csv";files.append(cal)
                ix=pd.read_csv(cal).query('phase==@phase and comparison=="delay"').set_index(["scope","month"]).index
                a=a[a.set_index(["scope","month"]).index.isin(ix)]
            dest.append(a.assign(phase=phase)[keys])
w=pd.concat(rows).pivot(index=["scope","phase","signal_date","cost"],columns="model",values="net")
m=pd.concat(months).pivot(index=["scope","phase","month"],columns="model",values="net")
wanted=[R,E,"embargo","within","sector","zero_recent"]
assert w[wanted].notna().all().all() and m[wanted].notna().all().all()
w[wanted].to_csv(out/"windows.csv");m[wanted].to_csv(out/"monthly.csv")
t=pd.read_parquet(out/"targets.parquet")
source=[]
for path in [early/"targets.parquet",src/"targets.parquet"]:
    files.append(path);source.append(pd.read_parquet(path).query('model in [@R,"embargo"]'))
weights=pd.concat([t,*source]).pivot(index=["signal_date","instrument"],columns="model",values="weight").fillna(0)
active=weights.sub(weights[R],axis=0).abs().groupby(level=0).sum()/2
bench=[]
for phase in range(10):
    f=src/str(phase)/"windows.csv";a=pd.read_csv(f).query('model==@R and cost=="base"')
    bench.append(a.assign(phase=phase).rename(columns={"index":"benchmark"}))
for year,mode in [(2019,"original"),(2020,"flat"),(2020,"half")]:
    root=early if mode=="original" else early/("sensitivity_"+mode)
    a=pd.read_csv(root/"windows.csv").query('year==@year and model==@R and cost=="base"')
    bench.append(a.assign(scope=str(year)+"_"+mode).rename(columns={"price_index":"benchmark"}))
bench=pd.concat(bench).set_index(["scope","phase","signal_date"]).benchmark
stats=[]
for scope,g in w.groupby(level="scope"):
    for name in ["within","sector","zero_recent","embargo"]:
        delta=g[name]-g[R];p=delta.groupby(level=["phase","cost"]).mean().unstack()*1e4
        b=m.loc[scope];b=(b[name]-b[R]).unstack(0).dropna().mean(axis=1)*1e4
        n=len(b);idx=np.random.default_rng(3857).integers(n,size=(15000,(n+2)//3))
        idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
        lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975])
        dates=pd.to_datetime(g.xs("base",level="cost").index.get_level_values("signal_date"))
        base=g.xs("base",level="cost")
        vsindex=base[name]-bench.reindex(base.index)
        assert vsindex.notna().all()
        stats.append(dict(vs_index=vsindex.groupby(level="phase").mean().mean()*1e4,vs_E=(base[name]-base[E]).groupby(level="phase").mean().mean()*1e4,scope=scope,model=name,base=p.base.mean(),zero=p.zero.mean(),double=p.double.mean(),positive=(p.base>0).sum(),monthly=b.mean(),lo=lo,hi=hi,ex3=b.drop(b.nlargest(3).index).mean(),active_pct=active.loc[dates,name].mean()*100 if name in active else np.nan))
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False);print(s.round(3).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"summary.csv",out/"windows.csv",out/"monthly.csv"]})
