from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import PRIVATE,accounts
from core import sha,dump
EP24=ROOT.parent/"24_conditional_return_distribution_exploration"
sys.path.insert(0,str(EP24/"src"))
import re
def available_date(record):
    dates=[pd.Timestamp(record['publish_date'])]
    dates.extend(pd.Timestamp(value) for value in re.findall(r'/([12]\d{3}-\d{2}-\d{2})/',record['url']))
    assert len(dates)>=2,'Missing explicit archive-path date'
    return max(dates)



OUT=HERE/"results";OUT.mkdir(exist_ok=True);accounts.OUT=OUT
m=accounts.Market()
panel=EP24/"outputs/r37_exchange_guidance/announcement_panel.parquet"
a=pd.read_parquet(panel)
a["available"]=[available_date(r) for r in a.to_dict("records")]
a["signal_idx"]=m.days.searchsorted(a.available,side="right")
coverage=EP24/"outputs/r37_exchange_guidance/stock_coverage.csv"
universe=pd.read_csv(coverage)
assert "instrument" in universe
covered=set(universe.instrument)
ip=PRIVATE/"industry.parquet"
industry=pd.read_parquet(ip)
industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
out=[]
for i,g in a.groupby("signal_idx"):
    if i==0 or i+11>=len(m.days):continue
    date=m.days[i];key=date.strftime("%Y%m%d")
    active=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))]
    mapping=active[["instrument","l1_name"]].drop_duplicates()
    sectors=mapping[~mapping.instrument.duplicated(False)].set_index("instrument").l1_name
    j=np.flatnonzero(m.members[i])
    market=pd.DataFrame(dict(index=j,ret=m.c[i,j]/m.c[i-1,j]-1),index=m.symbols[j])
    market["sector"]=sectors.reindex(market.index)
    market["rel"]=market.ret-market.groupby("sector").ret.transform("median")
    day=set(g.instrument);controls=market[market.index.isin(covered-day)].dropna()
    for symbol in sorted(day & set(market.index)):
        s=market.loc[symbol]
        meta=dict(signal_date=date,exit_date=m.days[i+11],stock=symbol,ids="|".join(g[g.instrument==symbol].announcement_id.astype(str)),relative=s.rel)
        peer=controls[controls.sector==s.sector]
        dist=(peer.ret-s.ret).abs().dropna().sort_values(kind="stable")
        if not np.isfinite(s.rel) or s.rel==0 or dist.empty or dist.iloc[0]>.01:
            out.append(meta|dict(status="no_match"));continue
        comp=dist.index[0]; ids=m.symbols.get_indexer([symbol,comp])
        trade=m.buy[i+1,ids]&m.sell[i+11,ids]
        diff=(m.o[i+11,ids]/m.o[i+1,ids]*(1-.002)/(1+.001))
        ok=trade.all() and np.isfinite(diff).all()
        edge=diff[0]-diff[1] if ok else np.nan
        out.append(meta|dict(status="ok" if ok else "trade_blocked",control=comp,dist=dist.iloc[0],edge=edge,signed=np.sign(s.rel)*edge))
z=pd.DataFrame(out)
z["scope"]=np.select([z.exit_date.lt("2021-01-01"),z.signal_date.lt("2021-01-01"),z.exit_date.le("2025-03-03"),z.signal_date.lt("2025-03-03")],["early","boundary","primary","boundary"],default="later")
z.to_csv(OUT/"matched_events.csv",index=False)
s=[]
for scope,g in z.groupby("scope"):
    good=g[g.status=="ok"]
    for sign,h in [("all",good),("positive",good[good.relative>0]),("negative",good[good.relative<0])]:
        v=h.groupby("signal_date").signed.mean()
        s.append(dict(scope=scope,sign=sign,total=len(g),matched=(g.status!="no_match").sum(),ok=len(h),dates=len(v),mean=v.mean()))
stats=pd.DataFrame(s)
early=stats[stats.scope=="early"].set_index("sign")
passed=bool(early.at["all","mean"]>0 and early.at["positive","mean"]>0)
stats.to_csv(OUT/"summary.csv",index=False)
dump(OUT/"decision.json",dict(early_passed=passed,hashes={str(f):sha(f) for f in [panel,coverage,ip,HERE/"PROTOCOL.md",Path(__file__),OUT/"matched_events.csv"]}))
print(stats.round(5).to_string(index=False));print("early gate",passed)
