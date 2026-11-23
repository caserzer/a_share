from pathlib import Path
import sys
import numpy as np
import pandas as pd
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,accounts,split
from core import dump,sha
out=here/"results";accounts.OUT=out
m=accounts.Market()
f=here.parent/"57_recent_industry_labels/results/scores.parquet";h=pd.read_parquet(f,columns=["signal_date","instrument","entry_idx","exit_idx","entry_date","phase"])
highfile=PRIVATE/"high.parquet";closefile=PRIVATE/"close.parquet";lim=PRIVATE/"limits/daily.parquet"
high=pd.read_parquet(highfile).reindex(index=m.days,columns=m.symbols);cl=pd.read_parquet(closefile).reindex_like(high)
v=pd.read_parquet(lim);v["instrument"]=v.ts_code.str[-2:]+v.ts_code.str[:6];v["day"]=pd.to_datetime(v.trade_date)
up=v.pivot(index="day",columns="instrument",values="up_limit").reindex_like(high)
i=m.days.get_indexer(h.signal_date);j=m.symbols.get_indexer(h.instrument);assert min(i)>0 and min(j)>=0
u=up.to_numpy()[i,j];hi=high.to_numpy()[i,j];close=cl.to_numpy()[i,j]
valid=np.isfinite(u)&(u>0)&np.isfinite(hi)&np.isfinite(close)
touch=valid&(abs(hi-u)<1e-5)
schedule=h[["signal_date","entry_date"]].drop_duplicates().copy()
schedule["scope"]=np.where(schedule.signal_date.dt.year<2021,schedule.signal_date.dt.year.astype(str),np.where(schedule.entry_date>=split,"later","primary"))
h=h[touch].copy();days=i[touch];names=j[touch]
h["sealed"]=abs(close[touch]-u[touch])<1e-5
h["band"]=np.round(100*(u[touch]/cl.to_numpy()[days-1,names]-1))
h["scope"]=np.where(h.signal_date.dt.year<2021,h.signal_date.dt.year.astype(str),np.where(h.entry_date>=split,"later","primary"))
e=h.entry_idx.to_numpy();x=h.exit_idx.to_numpy()
h["buy"]=m.buy[e,names]&m.members[e-1,names];h["sell"]=m.sell[x,names]
h["gross"]=m.o[x,names]/m.o[e,names]-1
h["comparable"]=h.buy&h.sell&np.isfinite(h.gross)
p=here.parent/"68_bottom_agreement/results/targets.parquet";b=here.parent/"64_mature_group_switch/results/targets.parquet"
pool=pd.read_parquet(b,columns=["signal_date","instrument","model"]).query('model=="passive"')
kept=pd.read_parquet(p,columns=["signal_date","instrument","model"]).query('model=="agree"')
keys=["signal_date","instrument"];bottom=pool.set_index(keys).index.difference(kept.set_index(keys).index)
h["low_consensus"]=h.set_index(keys).index.isin(bottom)
h.to_parquet(out/"events.parquet",index=False)
pairs=[]
for (scope,dt,band),g in h[h.comparable].groupby(["scope","signal_date","band"]):
    a=g[g.sealed];z=g[~g.sealed]
    if len(a) and len(z):
        pairs.append(dict(scope=scope,day=dt,band=band,weight=min(len(a),len(z)),sealed=len(a),opened=len(z),spread=a.gross.mean()-z.gross.mean()))
ps=pd.DataFrame(pairs);ps.to_csv(out/"pairs.csv",index=False);summary=[]
for scope,g in h.groupby("scope"):
    u=ps[ps.scope==scope];daily=u.assign(weighted=u.spread*u.weight).groupby("day")[["weight","weighted"]].sum()
    diff=daily.weighted/daily.weight
    summary.append(dict(scope=scope,touched=len(g),sealed=g.sealed.sum(),reopened=(~g.sealed).sum(),sealed_buy=g[g.sealed].buy.mean(),opened_buy=g[~g.sealed].buy.mean(),sell_blocked=(g.buy&~g.sell).sum(),overlap=g.low_consensus.sum(),bottom_total=bottom.get_level_values(0).isin(schedule.loc[schedule.scope==scope,"signal_date"]).sum(),paired_days=len(diff),spread=diff.mean()*1e4,positive=diff.gt(0).sum(),ex3=diff.drop(diff.nlargest(3).index).mean()*1e4))
s=pd.DataFrame(summary);s.to_csv(out/"summary.csv",index=False);print(s.round(2).to_string(index=False))
dump(out/"receipt.json",{str(p):sha(p) for p in [f,highfile,closefile,lim,p,b,Path(accounts.__file__),PRIVATE/"qfq_open.parquet",PRIVATE/"opening_trade_status_v2.parquet",PRIVATE/"daily_members.parquet",Path(__file__),here/"PROTOCOL.md",out/"events.parquet",out/"pairs.csv",out/"summary.csv"]})
