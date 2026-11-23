from pathlib import Path
import sys
import pandas as pd
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];OUT=HERE/"results";OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(HERE.parent/"02_adaptive_revision"))
from evaluate import R,E
from core import sha,dump
from account import replay
f=HERE.parent/"20_sell_side/results/events.csv"
keys=["phase","scope","signal_date","incoming","outgoing","control","sell_control"]
events=pd.read_csv(f,usecols=keys,parse_dates=["signal_date"]).dropna(subset=["control","sell_control"])
scores=pd.read_parquet(HERE.parent/"17_calendar_challenge/results/point_in_time_scores.parquet")
stats=[]
for phase,folder in [(0,"16_industry_pool"),(5,"17_calendar_challenge")]:
    orig=HERE.parent/folder/"results"
    dest=OUT/str(phase);dest.mkdir(exist_ok=True)
    base=pd.read_parquet(orig/"targets.parquet").query("model in [@R,@E]")
    t=[base]
    s=scores[scores.offset==phase]
    for date,h in base[base.model==R].groupby("signal_date"):
        g=events[(events.phase==phase)&(events.signal_date==date)]
        for name,sell,buy in [("supported","outgoing","incoming"),("placebo","sell_control","control")]:
            assert g[buy].is_unique and g[sell].is_unique
            old=set(h.instrument)
            assert set(g[sell])<=old and old.isdisjoint(g[buy])
            names=(old-set(g[sell]))|set(g[buy])
            chosen=s[(s.signal_date==date)&s.instrument.isin(names)]
            assert len(chosen)==len(h)
            t.append(chosen.assign(model=name,weight=1/len(h)))
    targets=pd.concat(t,ignore_index=True)
    targets.to_parquet(dest/"targets.parquet",index=False)
    from evaluate import accounts
    accounts.OUT=dest
    replay(targets,dest)
    w=pd.read_csv(dest/"windows.csv")
    old=pd.read_csv(orig/"windows.csv")
    for ref in [R,E]:
        match=w[w.model==ref].merge(old[old.model==ref],on=["signal_date","scope","cost"],validate="1:1")
        assert len(match)==len(old[old.model==ref])
        np.testing.assert_allclose(match.net_x,match.net_y,atol=1e-12)
    months=pd.read_csv(dest/"months.csv")
    for scope,g in w.groupby("scope"):
        p=g.pivot(index="signal_date",columns=["model","cost"],values="net")
        mon=months[months.scope==scope].pivot(index="month",columns="model",values="pnl")
        for ref in [R,"placebo",E]:
            dm=mon.supported-mon[ref]
            bycost={c:(p["supported",c]-p[ref,c]).mean()*1e4 for c in ["base","double","zero"]}
            stats.append(dict(phase=phase,scope=scope,reference=ref,n=len(p),matched_dates=events[(events.phase==phase)&(events.scope==scope)].signal_date.nunique(),
                    ex3_month_bp=dm.drop(dm.nlargest(3).index).mean()*1e4,**bycost))
a=pd.DataFrame(stats);a.to_csv(OUT/"summary.csv",index=False);print(a.round(3).to_string(index=False))
dump(OUT/"receipt.json",{str(p):sha(p) for p in [f,HERE/"PROTOCOL.md",HERE/"account.py",Path(__file__),OUT/"summary.csv"]})
