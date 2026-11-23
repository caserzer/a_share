from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,EP,R,E,accounts,split
from core import assign_deciles,sha,dump
from scheduled_execution import net_account
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market()
basefile=ROOT/"results/targets.parquet"
weeklyfile=EP/"extensions/original78_rankic_20261118/local_cache/weekly_predictions.parquet"
base=pd.read_parquet(basefile).query("model in [@R,@E]")
old=pd.read_parquet(weeklyfile)
hist={d:g for d,g in old.groupby("signal_date")}
dates=pd.DatetimeIndex(sorted(hist))
plans=[];rec=[]
for (dt,ref),g in base.groupby(["signal_date","model"]):
    e=int(g.entry_idx.iloc[0]); k=e+5; x=e+10
    sd=m.days[k-1]; recent=dates[dates.searchsorted(sd,side="right")-1]
    for method in ["original","reset","refresh"]:
        name=ref+"_"+method
        if method=="original":
            plans.append(g.assign(model=name,parent_date=dt));continue
        plans.append(g.assign(model=name,parent_date=dt,exit_idx=k,exit_date=m.days[k]))
        h=g.copy()
        if method=="refresh" and recent>dt:
            candidate=hist[recent].dropna(subset=[ref]).copy()
            j=m.symbols.get_indexer(candidate.instrument)
            assert min(j)>=0
            candidate=candidate[m.members[k-1,j]]
            h=candidate[assign_deciles(candidate,ref)==10].copy()
            assert len(h)>0
        rec.append(dict(model=name,signal_date=dt,mid_signal_date=sd,published=recent,
                age=m.days.get_loc(sd)-m.days.get_loc(recent),new=recent>dt,
                active_names=len(set(g.instrument)^set(h.instrument)),n=len(h)))
        plans.append(h.assign(model=name,parent_date=dt,signal_date=sd,entry_idx=k,entry_date=m.days[k],exit_idx=x,exit_date=m.days[x],weight=1/len(h)))
t=pd.concat(plans,ignore_index=True)
assert np.allclose(t.groupby(["model","entry_idx"]).weight.sum(),1)
t.to_parquet(OUT/"targets.parquet",index=False);pd.DataFrame(rec).to_csv(OUT/"dates.csv",index=False)
dump(OUT/"selection.json",{str(p.relative_to(ROOT.parent)):sha(p) for p in [basefile,weeklyfile,HERE/"PROTOCOL.md",Path(__file__),HERE/"scheduled_execution.py",OUT/"targets.parquet"]})
w=[];a=[];mm=[];oo=[]
for (model,late),g in t.groupby(["model",t.parent_date.isin(base[base.entry_date>=split].signal_date)]):
    scope="later" if late else "primary"
    end=int(g.exit_idx.max())
    for cost,bf,sf in [("base",.001,.002),("double",.002,.004),("zero",0,0)]:
        d,o,status=net_account(m,g,end,"flat",bf,sf)
        meta=dict(model=model,cost=cost,scope=scope)
        d=d.set_index("date")
        o["units"]=(o.buy-o.sell)/o.price
        mat=o.pivot(index="date",columns="instrument",values="units").reindex(index=d.index,columns=m.symbols).fillna(0.)
        u=mat.cumsum();u=u.mask(u.abs()<1e-12,0.)
        idx=m.days.get_indexer(d.index)
        cm=pd.DataFrame(m.marks["flat"][1][idx],index=d.index,columns=m.symbols)
        op=pd.DataFrame(m.marks["flat"][0][idx],index=d.index,columns=m.symbols)
        if status["valuation_complete"]:cm.iloc[-1]=op.iloc[-1]
        val=(u*cm).mask(u==0,0.)
        assert val.notna().all().all()
        np.testing.assert_allclose(val.sum(axis=1)+d.cash,d.nav,atol=1e-9)
        prev=u.shift().fillna(0.)
        before=(prev*op).mask(prev==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
        if cost=="base":
            oo.append(o.assign(**meta))
            def flows(col):
                return o.pivot(index="date",columns="instrument",values=col).reindex_like(val).fillna(0.)
            prof=val-val.shift().fillna(0.)+flows("sell")-flows("buy")-flows("fee")
            period=d.index.to_period("M")
            pnl=prof.groupby(period).sum().div(d.nav.shift().fillna(1.).groupby(period).first(),axis=0)
            mm.append(pnl.stack().loc[lambda v:v!=0].rename("pnl").reset_index().set_axis(["month","instrument","pnl"],axis=1).assign(**meta))
        for dt,h in g.groupby("parent_date"):
            first,last=h.entry_date.min(),h.exit_date.max()
            if last>d.index[-1]:continue
            stop=d.nav.iloc[-1] if last==m.days[end] else before.at[last]
            seg=d[(d.index>=first)&(d.index<last)] if last!=m.days[end] else d.loc[first:last]
            w.append(dict(**meta,signal_date=dt,net=stop/before.at[first]-1,fees=seg.fees.sum()/before.at[first],turnover=(seg.buy+seg.sell).sum()/before.at[first]))
        a.append(dict(**meta,**status,nav=d.nav.iloc[-1],end=d.index[-1],mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min(),cagr=d.nav.iloc[-1]**(252/(end-idx[0]))-1 if status["valuation_complete"] else np.nan))
w=pd.DataFrame(w)
keys=["scope","cost","signal_date"]
oldwin=pd.read_csv(ROOT/"results/windows.csv",parse_dates=["signal_date"])
oldwin=oldwin[oldwin.scope!="whole"]
for ref in [R,E]:
    match=w[w.model==ref+"_original"].merge(oldwin[oldwin.model==ref],on=keys,validate="1:1")
    assert len(match)==417
    np.testing.assert_allclose(match.net_x,match.open_net,atol=1e-12)
    w["vs_"+ref]=w.net-oldwin[oldwin.model==ref].set_index(keys).open_net.reindex(pd.MultiIndex.from_frame(w[keys])).to_numpy()
w["excess"]=w.net-oldwin[oldwin.model==R].set_index(keys).index_entry_exit_close.reindex(pd.MultiIndex.from_frame(w[keys])).to_numpy()
w.to_csv(OUT/"windows.csv",index=False);pd.DataFrame(a).to_csv(OUT/"accounts.csv",index=False)
pd.concat(mm).to_parquet(OUT/"stock_month.parquet",index=False)
pd.concat(oo).to_parquet(OUT/"orders.parquet",index=False)
wm=w.query("cost=='base'").groupby(["model","scope"]).agg({"net":"size","vs_RANK_MSE_78":"mean","vs_E1_78":"mean","excess":"mean","fees":"mean","turnover":"mean"})
print(wm.round(5))
