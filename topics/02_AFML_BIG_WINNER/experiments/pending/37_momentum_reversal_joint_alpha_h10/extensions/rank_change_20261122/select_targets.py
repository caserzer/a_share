"""Freeze next-period targets without reading evaluation labels or returns."""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parent
EP=ROOT.parents[1]
OLD=EP/"extensions/original78_rankic_20261118"
PREV=EP/"extensions/intraday_reversal_20261122"
D=ROOT/"results"
sys.path[:0]=[str(EP/"code"),str(PREV)]
from core import PRIVATE, sha, dump, assign_deciles

KEY=["signal_date","instrument"]
SCORE="RANK_MSE_78"
FIELDS=[SCORE,"mom5","mom20"]
CALIPERS=np.array([.25,.5,.5])
MAIN=pd.Timestamp("2025-03-03")
END=pd.Timestamp("2026-10-12")


def pair_group(enter,stay,scale):
    if enter.empty or stay.empty:
        return []
    a=enter[FIELDS].to_numpy()/scale
    b=stay[FIELDS].to_numpy()/scale
    ok=cdist(a,b,metric="chebyshev")<=1
    distance=cdist(a,b,metric="sqeuclidean")
    # Any additional feasible pair saves more than the total cost of all real assignments.
    penalty=4*(len(enter)+1)
    costs=np.column_stack([np.where(ok,distance,2*penalty),np.full((len(enter),len(enter)),penalty)])
    rows,cols=linear_sum_assignment(costs)
    return [(enter.index[i],stay.index[j],distance[i,j]) for i,j in zip(rows,cols) if j<len(stay) and ok[i,j]]


def select():
    D.mkdir(exist_ok=True)
    if (D/"selection.json").exists():
        raise RuntimeError("Sealed targets already exist; use a fresh extension directory")
    features=OLD/"local_cache/h10_features.parquet"
    scores=PREV/"results/scores.parquet"
    inputs=[scores,features,PRIVATE/"industry.parquet",PREV/"execution.py",EP/"code/accounts.py",EP/"code/core.py",EP/"config.yaml",
            EP/"outputs/local_cache/labels.parquet",PREV/"results/nav.parquet",PREV/"results/primary_100_windows.csv",
            PRIVATE/"net_excess_20261116/H00300.CSI.json",ROOT/"PROTOCOL.md",Path(__file__)]
    inputs += [PRIVATE/(n+".parquet") for n in ["qfq_close","qfq_open","open","opening_trade_status_v2","daily_members","limits/daily","suspensions/daily","market"]]
    dump(D/"inputs.json",{str(p):sha(p) for p in inputs})
    p=pd.read_parquet(scores,columns=KEY+[SCORE,SCORE+"_d","entry_idx","exit_idx","entry_date","exit_date","state"])
    f=pd.read_parquet(features,columns=KEY+["mom5","mom20","fold"])
    p=p.merge(f,on=KEY,validate="1:1")
    ind=pd.read_parquet(PRIVATE/"industry.parquet")
    ind["instrument"]=ind.ts_code.str[-2:]+ind.ts_code.str[:6]
    start=pd.to_datetime(ind.in_date)
    end=pd.to_datetime(ind.out_date).fillna(pd.Timestamp("2100-01-01"))
    panels,pairs,dates=[],[],[]
    prev=None
    for date,g in p.groupby("signal_date"):
        g=g.set_index("instrument").sort_index().copy()
        assert np.array_equal(assign_deciles(g.reset_index(),SCORE),g[SCORE+"_d"])
        g["pct"]=g[SCORE].rank(pct=True)
        g["industry"]=ind[(start<=date)&(end>date)].groupby("instrument").l1_code.agg(
            lambda x:x.iloc[0] if x.notna().all() and x.nunique()==1 else "UNKNOWN").reindex(g.index).fillna("UNKNOWN")
        g["prev_pct"]=np.nan if prev is None else prev.pct.reindex(g.index)
        g["prev_d"]=np.nan if prev is None else prev[SCORE+"_d"].reindex(g.index)
        g["delta"]=g.pct-g.prev_pct
        top=g[SCORE+"_d"].eq(10)
        g["role"]=np.select([top & g.prev_d.lt(10),top & g.prev_d.eq(10),top],["enter","stay","unknown"],default="other")
        g["base"]=top.astype(float)/top.sum()
        g["tilt"]=g.base.copy()
        valid=g.dropna(subset=FIELDS)
        scale=g[FIELDS].std(ddof=0).to_numpy()*CALIPERS
        assert np.isfinite(scale).all() and (scale>0).all()
        n=0
        for industry,h in valid[valid.industry.ne("UNKNOWN")&top.reindex(valid.index)].groupby("industry"):
            for a,b,distance in pair_group(h[h.role=="enter"],h[h.role=="stay"],scale):
                gaps=(g.loc[a,FIELDS].astype(float)-g.loc[b,FIELDS].astype(float)).to_numpy()
                pairs.append(dict(signal_date=date,entrant=a,stayer=b,industry=industry,distance=distance,
                                  score_gap_sd=gaps[0]/(scale[0]/CALIPERS[0]),mom5_gap_sd=gaps[1]/(scale[1]/CALIPERS[1]),
                                  mom20_gap_sd=gaps[2]/(scale[2]/CALIPERS[2]),current_pct_gap=g.at[a,"pct"]-g.at[b,"pct"],
                                  previous_pct_gap=g.at[a,"prev_pct"]-g.at[b,"prev_pct"]))
                w=.5/top.sum()
                g.loc[a,"tilt"]+=w
                g.loc[b,"tilt"]-=w
                n+=1
        assert np.allclose(g.groupby("industry")[["base","tilt"]].sum().diff(axis=1).tilt,0)
        assert np.isclose(g.tilt.sum(),1) and (g.tilt>0).equals(top)
        dates.append(dict(signal_date=date,entry_date=g.entry_date.iloc[0],exit_date=g.exit_date.iloc[0],top=int(top.sum()),
                          entrants=int((g.role=="enter").sum()),stayers=int((g.role=="stay").sum()),unknown=int((g.role=="unknown").sum()),
                          pairs=n,transferred=.5*n/top.sum(),new_fold=bool(prev is not None and g.fold.iloc[0]!=prev.fold.iloc[0]),
                          prev_date=None if prev is None else prev.signal_date.iloc[0]))
        panels.append(g.reset_index())
        if prev is not None:assert g.entry_idx.iloc[0]-prev.entry_idx.iloc[0]==10
        prev=g
    pd.concat(panels,ignore_index=True).to_parquet(D/"ranks_targets.parquet",index=False)
    pd.DataFrame(pairs).to_csv(D/"matches.csv",index=False)
    pd.DataFrame(dates).to_csv(D/"schedule.csv",index=False)
    dump(D/"selection.json",{p.name:sha(p) for p in sorted(D.iterdir())})
    print("Sealed",len(dates),"dates and",len(pairs),"pairs",flush=True)


if __name__=="__main__":
    select()
