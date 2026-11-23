from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE,accounts
from core import sha,dump
files=[here/"PROTOCOL.md",here/"run.py",here/"engine.py",here.parent/"64_mature_group_switch/account.py",Path(accounts.__file__),Path(__file__)]
for r in ["71_2018_concentration","72_passive_weighting","81_margin_subindustry","50_training_support","51_earlier_replication"]:
    f=here.parent/r/"results"/("baseline.parquet" if r.startswith("71") else "targets.parquet");files.append(f)
files.extend([here.parent/"71_2018_concentration/results"/(mode+post) for mode in ["half_archive","flat_archive"] for post in ["/suspensions.parquet","_prices.csv"]])
files.extend([PRIVATE/(k+".parquet") for k in ["qfq_open","qfq_close","open","close","market","opening_trade_status_v2","daily_members","limits/daily","suspensions/daily"]]);files.append(PRIVATE/"net_excess_20261116/H00300.CSI.json")
stats=[]
for scope in ["2018","2018_half","2019","2020_flat","2020_half","primary","later"]:
    data=[]
    for field in ["windows","months","accounts"]:
        fs=[out/(scope+mid+field+".parquet") for mid in ["_","_baseline_"]];files.extend(fs)
        data.append(pd.concat([pd.read_parquet(f) for f in fs]))
    w,m,a=data
    for h in [w,m]:
        h["arm"]=h.model+"_"+h.clock.astype(str)
    keys=["phase","offset","cost","signal_date"]
    v=w.pivot(index=keys,columns="arm",values="net");assert v.notna().all().all()
    v["index"]=w.groupby(keys).benchmark.first().reindex(v.index)
    mo=m.pivot(index=["phase","offset","month"],columns="arm",values="net")
    for tbl in [v,mo]:
        for clock in ["10","20"]:tbl["increment_"+clock]=tbl["stock_weight_"+clock]-tbl["drift_group_"+clock]
    for name,ref in [("stock_weight_20","drift_group_20"),("stock_weight_10","drift_group_10"),("increment_20","increment_10"),("stock_weight_20","stock_weight_10"),("stock_weight_20","index"),("stock_weight_20",R+"_20"),("stock_weight_20",E+"_20")]:
        delta=v[name]-v[ref];p=delta.groupby(level=[0,1,2]).mean().unstack()*1e4
        st=dict(scope=scope,arm=name,ref=ref,base=p.base.mean(),zero=p.zero.mean(),double=p.double.mean(),positive=p.base.gt(0).sum(),n=len(v.xs("base",level="cost")))
        if ref in mo:
            b=(mo[name]-mo[ref]).unstack([0,1]).dropna().mean(axis=1)*1e4
            if len(b)>3:
                n=len(b);idx=np.random.default_rng(3882).integers(n,size=(10000,(n+2)//3));idx=((idx[:,:,None]+np.arange(3))%n).reshape(len(idx),-1)[:,:n]
                lo,hi=np.quantile(b.to_numpy()[idx].mean(axis=1),[.025,.975]);st.update(months=n,monthly=b.mean(),lo=lo,hi=hi,ex3=b.drop(b.nlargest(3).index).mean())
        stats.append(st)
s=pd.DataFrame(stats);s.to_csv(out/"summary.csv",index=False)
print(s[s.arm.eq("stock_weight_20")].pivot(index="scope",columns="ref",values="base").round(2))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"summary.csv"]})
