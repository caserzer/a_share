from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
prev=here.parent/"38_all_phases"
sys.path[:0]=[str(here.parent/"02_adaptive_revision"),str(here.parent/"21_dual_support"),str(prev)]
from evaluate import R,E,PRIVATE,accounts,split
from ship_action import replay_with_ship_action
from core import sha,dump
out=here/"results";accounts.OUT=out;m=accounts.Market()
t=pd.read_parquet(out/"targets.parquet")
rows=[];monthly=[];inputs=[out/"targets.parquet",out/"training_receipt.json",Path(__file__),here/"PROTOCOL.md",prev/"ship_action.py"]
for phase,g in t.groupby("phase"):
    dest=out/str(phase);dest.mkdir(exist_ok=True);accounts.OUT=dest
    replay_with_ship_action(g,dest)
    w=pd.read_csv(dest/"windows.csv",parse_dates=["signal_date"]);mo=pd.read_csv(dest/"months.csv")
    ac=pd.read_csv(dest/"accounts.csv").set_index(["scope","model","cost"])
    assert ac.valuation_complete.all(),ac[~ac.valuation_complete]
    np.testing.assert_allclose((1+w.net).groupby([w.scope,w.model,w.cost]).prod().sort_index(),ac.nav.sort_index(),atol=1e-10)
    before=prev/f"results/{phase}/windows.csv";inputs.append(before)
    keys=["scope","cost","signal_date","model"]
    old=pd.read_csv(before,parse_dates=["signal_date"]).query("model in [@R,@E]")
    pd.testing.assert_series_equal(w[w.model.isin([R,E])].set_index(keys).net.sort_index(),old.set_index(keys).net.sort_index(),atol=1e-12,rtol=0)
    orders=pd.read_parquet(dest/"orders.parquet")
    for scope,h in w.groupby("scope"):
        v=h.pivot(index="signal_date",columns=["model","cost"],values="net")
        dates=g[(g.entry_date>=split)==(scope=="later")].drop_duplicates("signal_date").set_index("signal_date").sort_index()
        q=mo[(mo.model=="rank_h20")&(mo.scope==scope)].copy()
        q=q[(q.month>str(dates.entry_date.min().to_period("M")))&(q.month<str(dates.exit_date.max().to_period("M")))]
        monthly.append(q.assign(phase=phase))
        turn={}
        for name in [R,"rank_h10","rank_h20"]:
            cap=(1+v[name,"base"]).cumprod().shift(fill_value=1)
            o=orders[(orders.model==name)&(orders.scope==scope)]
            ids=pd.DatetimeIndex(dates.entry_date).searchsorted(o.date,side="right")-1
            assert ids.min()>=0 and dates.index.equals(v.index)
            turn[name]=((o.buy+o.sell).to_numpy()/cap.to_numpy()[ids]).sum()/len(v)
        c=v["rank_h20","base"]
        rows.append(dict(phase=phase,scope=scope,n=len(v),vs_common=(c-v["rank_h10","base"]).mean()*1e4,vs_E=(c-v[E,"base"]).mean()*1e4,
            vs_index=(c-h.query('model=="rank_h20" and cost=="base"').set_index("signal_date")["index"]).mean()*1e4,
            turnover=turn["rank_h20"],original_turnover=turn[R],common_turnover=turn["rank_h10"],
            **{cost:(v["rank_h20",cost]-v[R,cost]).mean()*1e4 for cost in ["base","zero","double"]}))
    print("verified",phase,flush=True)
s=pd.DataFrame(rows);s.to_csv(out/"summary.csv",index=False);mon=pd.concat(monthly);mon.to_csv(out/"months.csv",index=False)
stats=[]
for scope,g in s.groupby("scope"):
    a=mon[mon.scope==scope].pivot(index="month",columns="phase",values="delta").dropna().mean(axis=1)*1e4
    n=len(a);ix=np.random.default_rng(3849).integers(n,size=(15000,(n+2)//3))
    ix=((ix[:,:,None]+np.arange(3))%n).reshape(len(ix),-1)[:,:n]
    lo,hi=np.quantile(a.to_numpy()[ix].mean(axis=1),[.025,.975])
    stats.append(dict(scope=scope,positive=int(g.base.gt(0).sum()),**g.drop(columns=["phase","scope","n"]).mean().to_dict(),months=n,monthly=a.mean(),lo=lo,hi=hi,ex3=a.drop(a.nlargest(3).index).mean()))
a=pd.DataFrame(stats);a.to_csv(out/"aggregate.csv",index=False);print(a.round(3).to_string(index=False))
p=pd.read_parquet(out/"scores.parquet").merge(pd.read_parquet(prev/"results/scores.parquet"),on=["signal_date","instrument"],validate="one_to_one")
j=m.symbols.get_indexer(p.instrument);e=p.entry_idx.to_numpy()
records=[]
for horizon in [10,20]:
    ok=e+horizon<len(m.days)
    y=np.full(len(e),np.nan);y[ok]=m.o[e[ok]+horizon,j[ok]]/m.o[e[ok],j[ok]]-1
    p["outcome"]=y
    for date,h in p.groupby("signal_date"):
        if not h.outcome.notna().any():continue
        end=m.days[int(h.entry_idx.iloc[0])+horizon]
        if h.entry_date.iloc[0]<split<end or end>pd.Timestamp("2026-10-12"):continue
        common=h[["outcome","rank_h20","rank_h10",R]].dropna()
        vals=common.rank().corr().outcome
        records.append(dict(date=date,phase=int(h.phase.iloc[0]),scope="later" if h.entry_date.iloc[0]>=split else "primary",horizon=horizon,n=len(common),**vals.drop("outcome").to_dict()))
pd.DataFrame(records).to_csv(out/"rankic.csv",index=False)
dump(out/"receipt.json",{str(f):sha(f) for f in [*inputs,out/"aggregate.csv",out/"rankic.csv",out/"summary.csv"]})
