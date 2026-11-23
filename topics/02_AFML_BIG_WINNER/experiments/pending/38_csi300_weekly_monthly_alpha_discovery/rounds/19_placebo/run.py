from pathlib import Path
import sys
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import EP,R,E,accounts,PRIVATE
from core import sha,dump,assign_deciles
accounts.OUT=OUT;m=accounts.Market()
sf=HERE.parent/"17_calendar_challenge/results/point_in_time_scores.parquet"
p=pd.read_parquet(sf)
swapfile=HERE.parent/"18_industry_attribution/results/swaps.csv"
sw=pd.read_csv(swapfile,parse_dates=["signal_date"])
src=ROOT.parent/"34_industry_price_observation_radar/handoff/v3_candidates_20261016/early_model/periods"
cat=pd.concat(pd.read_csv(f,usecols=["date","industry_code","industry_name","state"]) for f in sorted(src.glob("*.csv")))
cat["date"]=pd.to_datetime(cat.date);history={d:g for d,g in cat.groupby("date")}
ind=pd.read_parquet(PRIVATE/"industry.parquet");ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
events=[]
for (phase,d),g in sw.groupby(["phase","signal_date"]):
    s=p[(p.offset==phase)&(p.signal_date==d)].copy()
    s["dec"]=assign_deciles(s,R)
    s[[R,E]]=s[[R,E]].rank(pct=True)
    s=s.set_index("instrument")
    k=d.strftime("%Y%m%d")
    active=ind[ind.in_date.le(k)&(ind.out_date.isna()|ind.out_date.gt(k))][["instrument","l1_name","l3_code","l3_name"]].drop_duplicates()
    s=s.join(active[~active.instrument.duplicated(False)].set_index("instrument"))
    week=max(i for i in history if i<d);tab=history[week]
    allowed=set(zip(tab.industry_code,tab.industry_name));off=tab[~tab.state.isin(["NEW","TRACKING"])]
    # DATA_INSUFFICIENT is not a supported alternative industry observation.
    off=off[off.state.ne("DATA_INSUFFICIENT")]
    outside=set(zip(off.industry_code,off.industry_name));eligible=[k in outside for k in zip(s.l3_code,s.l3_name)]
    choices=s[s.dec.eq(9)&np.asarray(eligible)].copy()
    for row in g.sort_values("incoming").itertuples():
        h=s.loc[row.incoming]
        pool=choices[choices.l1_name.eq(h.l1_name)]
        meta=dict(phase=phase,scope=row.scope,signal_date=d,incoming=row.incoming,outgoing=row.outgoing,weight=row.weight)
        if pool.empty:events.append(meta|dict(status="no_control"));continue
        dist=((pool[[R,E]]-h[[R,E]].astype(float))**2).sum(axis=1)
        name=dist.sort_index().sort_values(kind="stable").index[0]
        choices=choices.drop(index=name)
        j=m.symbols.get_indexer([row.incoming,name,row.outgoing]);e=int(h.entry_idx);x=int(h.exit_idx)
        ok=(m.buy[e,j]&m.sell[x,j]).all()
        returns=(1-.002)/(1+.001)*m.o[x,j]/m.o[e,j]-1
        if not ok:returns[:]=np.nan
        events.append(meta|dict(status="ok" if ok else "blocked",control=name,distance=dist[name]**.5,
            selected=returns[0],alternative=returns[1],original=returns[2],specific=row.weight*(returns[0]-returns[1]),
            selected_swap=row.weight*(returns[0]-returns[2]),placebo_swap=row.weight*(returns[1]-returns[2])))
z=pd.DataFrame(events);z.to_csv(OUT/"placebo_events.csv",index=False)
cal=pd.read_csv(HERE.parent/"18_industry_attribution/results/active_capital.csv",parse_dates=["signal_date"])
stats=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    ds=cal[(cal.phase==phase)&(cal.scope==scope)]
    k=g[g.status=="ok"]
    by_date=k.groupby("signal_date").specific.sum().reindex(ds.signal_date,fill_value=0.)
    mo=by_date.groupby(by_date.index.to_period("M")).sum()
    stats.append(dict(phase=phase,scope=scope,n=len(ds),swaps=len(g),paired=len(k),coverage=k.weight.sum()/g.weight.sum(),
        selected=k.selected_swap.sum()/len(ds),placebo=k.placebo_swap.sum()/len(ds),specific=by_date.mean(),
        ex3=by_date[~by_date.index.to_period("M").isin(mo.nlargest(3).index)].mean()))
s=pd.DataFrame(stats);s.to_csv(OUT/"summary.csv",index=False);print(s.round(6).to_string(index=False))
dump(OUT/"receipt.json",{str(f):sha(f) for f in [sf,swapfile,HERE/"PROTOCOL.md",Path(__file__),OUT/"placebo_events.csv"]})
