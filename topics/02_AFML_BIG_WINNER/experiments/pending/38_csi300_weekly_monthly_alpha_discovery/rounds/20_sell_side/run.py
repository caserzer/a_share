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
    retained=s[s.dec.eq(10)&np.asarray(eligible)&~s.index.isin(g.outgoing)].copy()
    for row in g.sort_values("outgoing").itertuples():
        h=s.loc[row.outgoing]
        pool=retained[retained.l1_name.eq(h.l1_name)]
        meta=dict(phase=phase,scope=row.scope,signal_date=d,incoming=row.incoming,outgoing=row.outgoing,weight=row.weight)
        if pool.empty:
            events.append(meta|dict(status="no_control"));continue
        dist=((pool[[R,E]]-h[[R,E]].astype(float))**2).sum(axis=1)
        name=dist.sort_index().sort_values(kind="stable").index[0]
        retained=retained.drop(index=name)
        j=m.symbols.get_indexer([row.outgoing,name])
        assert min(j)>=0 and name not in set(g.outgoing)
        e,x=int(h.entry_idx),int(h.exit_idx)
        ok=(m.buy[e,j]&m.sell[x,j]).all()
        ret=m.o[x,j]/m.o[e,j]*(1-.002)/(1+.001)-1
        events.append(meta|dict(status="ok" if ok else "blocked",sell_control=name,distance=dist[name]**.5,
                     sell_edge=row.weight*(ret[1]-ret[0]) if ok else np.nan))
z=pd.DataFrame(events)
buyfile=HERE.parent/"19_placebo/results/placebo_events.csv"
buy=pd.read_csv(buyfile,parse_dates=["signal_date"])
keys=["phase","scope","signal_date","outgoing","incoming"]
z=z.merge(buy[keys+["specific","selected_swap","placebo_swap","control"]],on=keys,validate="1:1")
z["double_placebo"]=z.placebo_swap-z.sell_edge
z["both_edge"]=z.specific+z.sell_edge
common=z.dropna(subset=["both_edge"])
np.testing.assert_allclose(common.selected_swap-common.double_placebo,common.both_edge,atol=1e-14)
z.to_csv(OUT/"events.csv",index=False)
cal=pd.read_csv(HERE.parent/"18_industry_attribution/results/active_capital.csv",parse_dates=["signal_date"])
summary=[]
for (phase,scope),g in z.groupby(["phase","scope"]):
    dates=cal[(cal.phase==phase)&(cal.scope==scope)].signal_date
    sell=g.dropna(subset=["sell_edge"]);both=g.dropna(subset=["both_edge"])
    values=sell.groupby("signal_date").sell_edge.sum().reindex(dates,fill_value=0)
    month=values.groupby(values.index.to_period("M")).sum()
    ix=values.index.to_period("M").isin(month.nlargest(3).index)
    summary.append(dict(phase=phase,scope=scope,windows=len(dates),swaps=len(g),sell_pairs=len(sell),
         days=sell.signal_date.nunique(),coverage=sell.weight.sum()/g.weight.sum(),sell_bp=values.mean()*1e4,
         sell_ex3_bp=values[~ix].mean()*1e4,both_pairs=len(both),both_coverage=both.weight.sum()/g.weight.sum(),
         buy_common_bp=both.specific.sum()/len(dates)*1e4,sell_common_bp=both.sell_edge.sum()/len(dates)*1e4,
         both_bp=both.both_edge.sum()/len(dates)*1e4))
stats=pd.DataFrame(summary);stats.to_csv(OUT/"summary.csv",index=False);print(stats.round(3).to_string(index=False))
dump(OUT/"receipt.json",{str(f):sha(f) for f in [sf,swapfile,buyfile,HERE/"PROTOCOL.md",Path(__file__),OUT/"events.csv",OUT/"summary.csv"]})
