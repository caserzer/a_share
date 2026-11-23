from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import R,E,PRIVATE
from core import sha,dump
out=here/"results";src=here.parent/"57_recent_industry_labels/results"
price=PRIVATE/"qfq_open.parquet";op=pd.read_parquet(price)
fs=src/"scores.parquet";ft=src/"targets.parquet";fw=src/"windows.csv";files=[price,fs,ft,fw,Path(__file__),here/"PROTOCOL.md"]
scores=pd.read_parquet(fs,columns=["signal_date","instrument","entry_date","exit_date"])
targets=[pd.read_parquet(ft).query('model=="within"')]
early=here.parent/"51_earlier_replication/results";recent=here.parent/"50_training_support/results"
for root in [early,recent]:
    f=root/"targets.parquet";files.append(f);targets.append(pd.read_parquet(f).query("model in [@R,@E]"))
weights=dict(tuple(pd.concat(targets).groupby("signal_date")))
ideal=[]
for day,g in scores.groupby("signal_date"):
    y=(op.loc[g.exit_date.iloc[0],g.instrument]/op.loc[g.entry_date.iloc[0],g.instrument]-1).replace([np.inf,-np.inf],np.nan)
    t=weights[day]
    gross={k:y.reindex(h.instrument).mean(skipna=False) for k,h in t.groupby("model")}
    for model,pick in gross.items():
        ideal.append(dict(signal_date=day,model=model,ideal=pick,pool=y.mean(),complete=np.isfinite(list(gross.values())).all(),quoted=y.notna().sum(),eligible=len(y)))
ideal=pd.DataFrame(ideal)
bench=[]
for ph in range(10):
    f=recent/str(ph)/"windows.csv";files.append(f);d=pd.read_csv(f).query('model==@R and cost=="base"')
    bench.append(d.assign(phase=ph).rename(columns={"index":"benchmark"}))
for year,mode in [(2019,"original"),(2020,"flat"),(2020,"half")]:
    f=(early if mode=="original" else early/("sensitivity_"+mode))/"windows.csv";files.append(f)
    b=pd.read_csv(f).query('year==@year and cost=="base" and model==@R')
    bench.append(b.assign(scope=str(year)+"_"+mode).rename(columns={"price_index":"benchmark"}))
keys=["scope","phase","signal_date"]
b=pd.concat(bench)[keys+["benchmark"]]
w=pd.read_csv(fw)[keys+["cost",R,E,"within"]].melt(id_vars=keys+["cost"],var_name="model",value_name="net")
w=w.pivot(index=keys+["model"],columns="cost",values="net").reset_index().merge(b,on=keys,validate="many_to_one")
w.signal_date=pd.to_datetime(w.signal_date);w=w.merge(ideal,on=["signal_date","model"],validate="many_to_one")
w["pool_vs_index"]=w.pool-w.benchmark
w["selection"]=w.ideal-w.pool
w["execution"]=w.zero-w.ideal
w["fees"]=w.base-w.zero
w["net_vs_index"]=w.base-w.benchmark
cols=["pool_vs_index","selection","execution","fees"]
q=w[w.complete];np.testing.assert_allclose(q[cols].sum(axis=1),q.net_vs_index,atol=1e-12)
w.to_csv(out/"windows.csv",index=False)
rows=[]
for (scope,model),g in w.groupby(["scope","model"]):
    h=g[g.complete];values=h.groupby("phase")[cols+["net_vs_index"]].mean().mean()*1e4
    rows.append(dict(scope=scope,model=model,n=len(g),usable=len(h),quoted=g.quoted.sum()/g.eligible.sum(),full_net=g.groupby("phase").net_vs_index.mean().mean()*1e4,**values.to_dict()))
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);print(s.round(2).to_string(index=False))
dump(out/"receipt.json",{str(f):sha(f) for f in [*files,out/"windows.csv",out/"summary.csv"]})
