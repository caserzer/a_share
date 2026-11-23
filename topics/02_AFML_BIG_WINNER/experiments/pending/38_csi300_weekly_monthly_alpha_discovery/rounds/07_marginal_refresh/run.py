from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
R6=HERE.parent/"06_midwindow_refresh"
sys.path[:0]=[str(R6),str(HERE.parent/"02_adaptive_revision")]
from evaluate import EP,accounts,R,split
from scheduled_execution import net_account
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market()
parent_file=R6/"results/targets.parquet"
week_file=EP/"extensions/original78_rankic_20261118/local_cache/weekly_predictions.parquet"
t=pd.read_parquet(parent_file)
weekly=pd.read_parquet(week_file)
history={d:g.set_index("instrument")[R] for d,g in weekly.groupby("signal_date")}
audit=pd.read_csv(R6/"results/dates.csv",parse_dates=["published","signal_date"])
audit=audit[audit.model.eq(R+"_refresh")].set_index("signal_date")
targets=[];pairs=[];train=[];dec=[]
for date,group in t[t.model==R+"_refresh"].groupby("parent_date"):
    g=group[group.signal_date==date].copy()
    h=group[group.signal_date!=date].copy()
    up=set(h.instrument)-set(g.instrument)
    dn=set(g.instrument)-set(h.instrument)
    mid=int(h.entry_idx.iloc[0]); end=int(h.exit_idx.iloc[0])
    rank=history[audit.at[date,"published"]].dropna().rank(pct=True)
    member=pd.Series(m.members[mid-1],index=m.symbols)
    # Preserve the original number of slots even if the weekly universe changed.
    ups=sorted(up,key=lambda s:(-rank.get(s,0),s))
    downs=sorted(dn,key=lambda s:(member.at[s],rank.get(s,np.inf),s))
    past=[row for row in train if row[0]<=mid-1]
    slope=np.nan
    if len(past)>=12:
        denom=sum(row[2] for row in past)
        slope=sum(row[1] for row in past)/denom if denom>0 else np.nan
    chosen=set(g.instrument)
    training=[];accepted=forced=0
    for new,old in zip(ups,downs):
        gap=rank.get(new,np.nan)-rank.get(old,np.nan)
        must=not member.at[old]
        swap=must or (np.isfinite(gap) and gap>0 and slope*gap>.003)
        if swap:
            chosen.remove(old);chosen.add(new)
            accepted+=1;forced+=int(must)
        j=m.symbols.get_indexer([new,old])
        ret=m.o[end,j]/m.o[mid,j]-1
        ok=np.isfinite(ret).all() and np.all(m.buy[mid,j]&m.sell[end,j])
        edge=ret[0]-ret[1] if ok else np.nan
        pairs.append(dict(date=date,mid_signal=m.days[mid-1],exit=m.days[end],new=new,old=old,
                          gap=gap,forced=must,accepted=swap,slope=slope,edge=edge))
        if ok and not must and np.isfinite(gap) and gap>0:
            training.append([gap*edge,gap**2])
    if training:train.append((end,*np.mean(training,axis=0)))
    assert len(chosen)==len(g)
    second=pd.concat([g,h]).drop_duplicates("instrument").set_index("instrument").loc[sorted(chosen)].reset_index()
    second=second.assign(signal_date=m.days[mid-1],entry_idx=mid,entry_date=m.days[mid],exit_idx=end,exit_date=m.days[end],weight=1/len(chosen))
    targets.extend([g,second])
    dec.append(dict(date=date,past=len(past),latest_exit=m.days[past[-1][0]] if past else pd.NaT,slope=slope,accepted=accepted,
        forced=forced,possible=min(len(ups),len(downs)),slots=len(chosen)))
z=pd.concat(targets,ignore_index=True).assign(model="marginal")
z.to_parquet(OUT/"targets.parquet",index=False)
pd.DataFrame(pairs).to_csv(OUT/"pairs.csv",index=False)
pd.DataFrame(dec).to_csv(OUT/"decisions.csv",index=False)
dump(OUT/"selection.json",{str(f.relative_to(ROOT.parent)):sha(f) for f in [parent_file,week_file,HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet"]})
w=[];a=[];months=[];orders=[]
for late,g in z.groupby(z.parent_date.isin(t[(t.model==R+"_original")&(t.entry_date>=split)].parent_date)):
    end=int(g.exit_idx.max());scope="later" if late else "primary"
    for cost,bf,sf in [("base",.001,.002),("zero",0,0),("double",.002,.004)]:
        d,o,st=net_account(m,g,end,"flat",bf,sf)
        meta=dict(scope=scope,cost=cost)
        d=d.set_index("date");idx=m.days.get_indexer(d.index)
        o["units"]=(o.buy-o.sell)/o.price
        def matrix(col):
            return o.pivot(index="date",columns="instrument",values=col).reindex(index=d.index,columns=m.symbols).fillna(0.)
        u=matrix("units").cumsum();u=u.mask(u.abs()<1e-12,0.)
        op=pd.DataFrame(m.marks["flat"][0][idx],index=d.index,columns=m.symbols)
        close=pd.DataFrame(m.marks["flat"][1][idx],index=d.index,columns=m.symbols)
        if st["valuation_complete"]:close.iloc[-1]=op.iloc[-1]
        value=(u*close).mask(u==0,0.)
        assert value.notna().all().all()
        np.testing.assert_allclose(value.sum(axis=1)+d.cash,d.nav,atol=1e-9)
        prior=u.shift().fillna(0.)
        before=(prior*op).mask(prior==0,0.).sum(axis=1,skipna=False)+d.cash.shift().fillna(1.)
        if cost=="base":
            orders.append(o.assign(**meta))
            prof=value-value.shift().fillna(0.)+matrix("sell")-matrix("buy")-matrix("fee")
            per=d.index.to_period("M")
            pnl=prof.groupby(per).sum().div(d.nav.shift().fillna(1.).groupby(per).first(),axis=0)
            months.append(pnl.stack().loc[lambda v:v!=0].rename("pnl").reset_index().set_axis(["month","instrument","pnl"],axis=1).assign(**meta))
        for date,h in g.groupby("parent_date"):
            e,x=h.entry_date.min(),h.exit_date.max()
            if x>d.index[-1]:continue
            stop=d.nav.iloc[-1] if x==m.days[end] else before.at[x]
            w.append(dict(**meta,signal_date=date,net=stop/before.at[e]-1))
        a.append(dict(**meta,**st,nav=d.nav.iloc[-1],cagr=d.nav.iloc[-1]**(252/(end-idx[0]))-1 if st["valuation_complete"] else np.nan,
                      mdd=(d.nav/np.maximum.accumulate(np.r_[1.,d.nav])[1:]-1).min()))
w=pd.DataFrame(w);keys=["scope","cost","signal_date"]
orig=pd.read_csv(R6/"results/windows.csv",parse_dates=["signal_date"])
for model in [R+"_original",R+"_reset",R+"_refresh","E1_78_original"]:
    ref=orig[orig.model==model].set_index(keys)
    order=pd.MultiIndex.from_frame(w[keys])
    w["vs_"+model]=w.net-ref.net.reindex(order).to_numpy()
    w["excess"]=w.net-(ref.net-ref.excess).reindex(order).to_numpy()
w.to_csv(OUT/"windows.csv",index=False)
pd.DataFrame(a).to_csv(OUT/"accounts.csv",index=False)
pd.concat(months).to_parquet(OUT/"stock_month.parquet",index=False)
pd.concat(orders).to_parquet(OUT/"orders.parquet",index=False)
print((w.groupby(["scope","cost"]).mean(numeric_only=True)*1e4).round(2).to_string())
