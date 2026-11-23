from pathlib import Path
import sys
import pandas as pd
import numpy as np
here=Path(__file__).resolve().parent;out=here/"results"
sys.path.insert(0,str(here.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,accounts
from core import sha,dump
accounts.OUT=out
m=accounts.Market()
files={k:PRIVATE/(k+".parquet") for k in ["close","high","low","volume","money","industry","qfq_open","open","daily_members","limits/daily","opening_trade_status_v2"]}
c,hi,lo,vol,money=[pd.read_parquet(files[k]).loc[:"2017-12-31"] for k in ["close","high","low","volume","money"]]
spread=hi-lo;mid=(hi+lo)/2
vwap=money/vol.where(vol.gt(0))
valid=lo.gt(0)&spread.gt(0)&c.ge(lo)&c.le(hi)&money.gt(0)&vol.gt(0)&vwap.ge(lo-.01)&vwap.le(hi+.01)
location=((c-mid)/spread.where(valid)).rolling(20,min_periods=20).mean()
priced=((vwap.clip(lower=lo,upper=hi)-mid)/spread.where(valid)).rolling(20,min_periods=20).mean()
ind=pd.read_parquet(files["industry"]);ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
anchor=m.days.get_loc("2021-01-08")
records=[];dates=[]
for day in c.index:
    i=m.days.get_loc(day);en=i+1;ex=en+10
    if (i-anchor)%10 or i<19 or m.days[ex].year!=2017:continue
    pool=m.symbols[m.members[i]]
    stamp=day.strftime("%Y%m%d")
    s=ind[ind.in_date.le(stamp)&(ind.out_date.isna()|ind.out_date.gt(stamp))][["instrument","l1_name"]].drop_duplicates()
    sectors=s[~s.instrument.duplicated(False)].set_index("instrument").l1_name
    h=pd.DataFrame({"location":location.loc[day].reindex(pool),"priced":priced.loc[day].reindex(pool),"sector":sectors.reindex(pool)}).dropna().rename_axis("instrument").reset_index().sort_values(["sector","location","instrument"])
    order=h.groupby("sector").cumcount();h["pair"]=order//2
    q=h[order.mod(2).eq(0)].merge(h[order.mod(2).eq(1)],on=["sector","pair"],suffixes=("_a","_b"),validate="1:1")
    q=q[(q.priced_a-q.priced_b).abs()>1e-12]
    for pair in q.itertuples():
        high,low=(pair.instrument_a,pair.instrument_b) if pair.priced_a>pair.priced_b else (pair.instrument_b,pair.instrument_a)
        j,k=m.symbols.get_indexer([high,low]);quotes=m.o[[en,ex]][:,[j,k]]
        can=np.isfinite(quotes).all() and (quotes>0).all() and m.buy[en,j] and m.sell[en,k] and m.sell[ex,j] and m.buy[ex,k]
        gross=net=np.nan
        if can:
            h_end,l_end=quotes[1]/quotes[0]
            gross=h_end-l_end;net=gross-(.003+.002*h_end+.001*l_end)
        records.append(dict(day=day,entry=m.days[en],exit=m.days[ex],high=high,low=low,sector=pair.sector,loc_gap=abs(pair.location_a-pair.location_b),signal_gap=abs(pair.priced_a-pair.priced_b),budget=.5/len(pool),complete=can,gross=gross,net=net))
    dates.append(dict(day=day,members=len(pool),covered=len(h),pairs=len(q)))
p=pd.DataFrame(records);p.to_csv(out/"pairs.csv",index=False)
d=pd.DataFrame(dates).set_index("day")
v=p[p.complete].groupby("day")
d=d.join(v.agg(complete=("net","size"),gross=("gross","mean"),net=("net","mean"),active=("budget","sum")))
d["known_budget_net_bp"]=(p.budget*p.net*1e4).groupby(p.day).sum(min_count=1)
d.to_csv(out/"dates.csv")
summary=dict(dates=len(d),observed_dates=int(d.net.notna().sum()),pairs=len(p),complete=int(p.complete.sum()),pair_gross_bp=d.gross.mean()*1e4,pair_net_bp=d.net.mean()*1e4,positive_dates=int(d.net.gt(0).sum()),ex3_bp=d.net.dropna().sort_values().iloc[:-3].mean()*1e4,active=d.active.mean(),known_budget_net_bp=d.known_budget_net_bp.mean())
dump(out/"summary.json",summary)
dump(out/"receipt.json",{str(f):sha(f) for f in [*files.values(),Path(accounts.__file__),here/"PROTOCOL.md",Path(__file__),out/"pairs.csv",out/"dates.csv",out/"summary.json"]})
print(summary)
