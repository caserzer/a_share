"""Concentration and uncertainty for the same-close and horizon experiments."""
from pathlib import Path
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
r="RANK_MSE_78_original"
base=pd.read_parquet(HERE/"06_midwindow_refresh/results/stock_month.parquet")
base=base[base.model==r].groupby(["scope","month"]).pnl.sum()
rows=[]
for run in ["08_same_close","09_horizon_target"]:
    for f in sorted((HERE/run/"results").glob("*/windows.csv")):
        z=pd.read_csv(f)
        pnl=pd.read_parquet(f.parent/"stock_month.parquet").groupby(["scope","month"]).pnl.sum()
        month=(pnl-base).rename("delta_rank").reset_index()
        month.to_csv(f.parent/"months.csv",index=False)
        for scope,g in z[z.cost=="base"].groupby("scope"):
            v=g["vs_"+r].to_numpy()
            n=len(v)
            starts=np.random.default_rng(38).integers(n,size=(10000,(n+2)//3))
            ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
            lo,hi=np.quantile(v[ix].mean(axis=1),[.025/20,1-.025/20])
            mon=month[month.scope==scope].delta_rank
            o=z[z.scope==scope].groupby("cost")["vs_"+r].mean()
            rows.append(dict(run=run,model=f.parent.name,scope=scope,n=n,mean=v.mean(),low=lo,high=hi,
                           zero=o.zero,double=o.double,vs_e1=g.vs_E1_78_original.mean(),vs_index=g.excess.mean(),
                           ex3=mon.drop(mon.nlargest(3).index).mean()))
pd.DataFrame(rows).to_csv(HERE/"09_horizon_target/results/comparison.csv",index=False)
print(pd.DataFrame(rows).round(5).to_string(index=False))
