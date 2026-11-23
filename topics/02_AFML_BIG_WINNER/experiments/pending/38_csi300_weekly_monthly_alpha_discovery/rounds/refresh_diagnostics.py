"""Summarize the window refresh and marginal-cost experiments on matched dates."""
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
a=HERE/"06_midwindow_refresh/results"; b=HERE/"07_marginal_refresh/results"
r="RANK_MSE_78"
w=pd.read_csv(a/"windows.csv")
z=pd.read_csv(b/"windows.csv").rename(columns={"vs_"+r+"_original":"vs_"+r,"vs_E1_78_original":"vs_E1_78"})
w=pd.concat([w,z.assign(model="marginal")],ignore_index=True)
p=pd.concat([pd.read_parquet(a/"stock_month.parquet"),pd.read_parquet(b/"stock_month.parquet").assign(model="marginal")])
m=p.groupby(["model","scope","month"]).pnl.sum().reset_index()
for ref in [r+"_original","E1_78_original"]:
    lookup=m[m.model==ref].set_index(["scope","month"]).pnl
    m["vs_"+ref]=m.pnl-lookup.reindex(pd.MultiIndex.from_frame(m[["scope","month"]])).to_numpy()
m.to_csv(b/"all_monthly.csv",index=False)
rows=[]
for (model,scope),g in w[w.cost=="base"].groupby(["model","scope"]):
    v=g["vs_"+r].to_numpy()
    n=len(v)
    starts=np.random.default_rng(38).integers(n,size=(10000,(n+2)//3))
    ix=((starts[:,:,None]+np.arange(3))%n).reshape(10000,-1)[:,:n]
    ci=np.quantile(v[ix].mean(axis=1),[.025/16,1-.025/16])
    mon=m[(m.model==model)&(m.scope==scope)]["vs_"+r+"_original"]
    costs=w[(w.model==model)&(w.scope==scope)].groupby("cost")["vs_"+r].mean()
    rows.append(dict(model=model,scope=scope,n=n,paired=v.mean(),lo=ci[0],hi=ci[1],vs_E1=g.vs_E1_78.mean(),
                     excess=g.excess.mean(),ex3=mon.drop(mon.nlargest(3).index).mean(),zero=costs.zero,double=costs.double))
s=pd.DataFrame(rows);s.to_csv(b/"refresh_summary.csv",index=False)
print(s[s.model.isin(["marginal",r+"_refresh"])].round(6).to_string(index=False))
d=pd.read_csv(b/"decisions.csv");d["scope"]=["primary"]*100+["later"]*39
print(d.groupby("scope")[["accepted","forced","possible"]].sum());print(d.groupby("scope").accepted.apply(lambda x:(x>0).sum()))
