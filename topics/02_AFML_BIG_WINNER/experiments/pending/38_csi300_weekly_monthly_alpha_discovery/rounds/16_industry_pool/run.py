from pathlib import Path
import sys
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import EP,PRIVATE,R,E,evaluate
from core import sha,dump
OUT=HERE/"results";OUT.mkdir(exist_ok=True)
catalog=ROOT.parent/"34_industry_price_observation_radar/handoff/v3_candidates_20261016"
hist={};files=[]
for method in ["early_model","momentum"]:
    records=[]
    for f in sorted((catalog/method/"periods").glob("*.csv")):
        files.append(f)
        records.append(pd.read_csv(f,usecols=["date","era","industry_code","industry_name","state","observation_id","event_kind"]))
    allrows=pd.concat(records);allrows["date"]=pd.to_datetime(allrows.date)
    assert not allrows.duplicated(["date","industry_code"]).any()
    hist[method]={d:g for d,g in allrows.groupby("date")}
sf=EP/"extensions/intraday_reversal_20261122/results/scores.parquet"
scores=pd.read_parquet(sf).dropna(subset=["exit_date"])
base=pd.read_parquet(ROOT/"results/targets.parquet").query("model in [@R,@E]")
industry=pd.read_parquet(PRIVATE/"industry.parquet");industry["instrument"]=industry.ts_code.str[-2:]+industry.ts_code.str[:6]
out=[base];log=[]
for date,g in scores.groupby("signal_date"):
    key=date.strftime("%Y%m%d")
    active=industry[industry.in_date.le(key)&(industry.out_date.isna()|industry.out_date.gt(key))]
    lookup=active[["instrument","l1_name","l3_code","l3_name"]].drop_duplicates()
    g=g.merge(lookup[~lookup.instrument.duplicated(False)],on="instrument",how="left",validate="1:1")
    top=g[g[R+"_d"]==10]
    for name,history in hist.items():
        week=max(d for d in history if d<date); table=history[week]
        compatible=table.era.eq("SW2021").all() and (date-week).days<=10
        active_rows=table[table.event_kind.isin(["NEW","UPDATE"])]
        assert len(active_rows)<=20
        allowed=set(zip(active_rows.industry_code,active_rows.industry_name)) if compatible else set()
        known=set(zip(table.industry_code,table.industry_name)) if compatible else set()
        pairs=list(zip(g.l3_code,g.l3_name));g["observed"]=[p in allowed for p in pairs];g["known"]=[p in known for p in pairs]
        proposals=[]
        for sector,old in g[(g[R+"_d"]==10)&~g.observed&g.known].groupby("l1_name"):
            entrants=g[(g[R+"_d"]==9)&g.observed&g.l1_name.eq(sector)]
            for (_,h),(_,k) in zip(old.sort_values(R).iterrows(),entrants.sort_values(R,ascending=False).iterrows()):
                proposals.append((h[R]-k[R],h.instrument,k.instrument))
        selected=set(top.instrument)
        changes=sorted(proposals)[:len(top)//5]
        for loss,old,new in changes:selected.remove(old);selected.add(new)
        t=g[g.instrument.isin(selected)]
        assert len(t)==len(top) and t.l1_name.value_counts().to_dict()==top.l1_name.value_counts().to_dict()
        out.append(t.assign(model=name,weight=1/len(t)))
        log.append(dict(signal_date=date,week=week,model=name,compatible=compatible,known=g.known.sum(),available=g.observed.sum(),pool=len(allowed),swaps=len(changes)))
pd.concat(out).to_parquet(OUT/"targets.parquet",index=False)
pd.DataFrame(log).to_csv(OUT/"coverage.csv",index=False)
dump(OUT/"selection.json",{str(f.relative_to(ROOT.parent)):sha(f) for f in [sf,HERE/"PROTOCOL.md",Path(__file__),OUT/"targets.parquet",*files]})
evaluate(OUT,28)
