"""Seal as-of CSI300 base weights and three equal-budget intra-industry transfers."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
D = ROOT / "results"
EP = ROOT.parents[1]
sys.path.insert(0, str(EP/"code"))
from core import PRIVATE, SOURCE, sha, dump, assign_deciles
import accounts

PRED = ROOT.parent/"original78_rankic_20261118/local_cache/predictions.parquet"
RANK = ROOT.parent/"rank_change_20261122/results/ranks_targets.parquet"
MODELS = ["E1","REV","RANK"]
MAIN = pd.Timestamp("2025-03-03")


def transfers(g):
    eligible = g[MODELS].notna().all(axis=1)
    for model in MODELS:
        valid = g.loc[eligible, ["instrument",model]]
        g[model+"_low"] = False
        if len(valid):
            g.loc[valid.index, model+"_low"] = assign_deciles(valid,model).le(2)
        g[model+"_target"] = g.base.copy()
    caps = {}
    for ind,h in g[eligible & g.industry.ne("UNKNOWN")].groupby("industry"):
        caps[ind] = .5*min(h.loc[h[model+"_low"].eq(side),"base"].sum()
                           for model in MODELS for side in [True,False])
    capacity = sum(caps.values())
    factor = min(1.,.02/capacity) if capacity>0 else 0.
    for ind,cap in caps.items():
        if cap<=0:
            continue
        h = g[eligible & g.industry.eq(ind)]
        for model in MODELS:
            for side,sign in [(True,-1),(False,1)]:
                w=h.loc[h[model+"_low"].eq(side),"base"]
                g.loc[w.index,model+"_target"] += sign*cap*factor*w/w.sum()
    return g,capacity*factor


def run():
    D.mkdir(exist_ok=True)
    if (D/"selection.json").exists():
        raise RuntimeError("Use a fresh extension to regenerate sealed selections")
    files=[PRED,RANK,ROOT/"PROTOCOL.md",Path(__file__),EP/"code/core.py",EP/"code/accounts.py",EP/"config.yaml",SOURCE/"src/portfolio.py"]
    files += [PRIVATE/(x+".parquet") for x in ["weights/snapshots","industry","qfq_close","qfq_open","daily_members","opening_trade_status_v2","open","limits/daily","suspensions/daily"]]
    dump(D/"inputs.json",{str(p):sha(p) for p in files})
    accounts.OUT=D
    market=accounts.Market()
    close=pd.DataFrame(market.c,index=market.days,columns=market.symbols)
    marked=pd.DataFrame(market.marks["flat"][1],index=market.days,columns=market.symbols)
    snapshots=pd.read_parquet(PRIVATE/"weights/snapshots.parquet")
    assert snapshots.index_code.eq("000300.SH").all()
    snapshots["date"]=pd.to_datetime(snapshots.trade_date)
    snapshots["instrument"]=snapshots.con_code.str[-2:]+snapshots.con_code.str[:6]
    snapshots=snapshots.pivot(index="date",columns="instrument",values="weight")/100
    pred=pd.read_parquet(PRED)
    ind=pd.read_parquet(RANK,columns=["signal_date","instrument","industry"])
    pred=pred.merge(ind,on=["signal_date","instrument"],validate="1:1")
    selections=[]
    schedule=[]
    for date,h in pred[pred.exit_date.notna()].groupby("signal_date",sort=True):
        i=market.days.get_loc(date)
        assert h.fit_cutoff.lt(date).all() and h.entry_idx.eq(i+1).all() and h.exit_idx.eq(i+11).all()
        snap=snapshots.index[snapshots.index<date][-1]
        b=snapshots.loc[snap].dropna()
        mem=market.symbols[market.members[i]]
        row=dict(signal_date=date,entry_date=h.entry_date.iloc[0],exit_date=h.exit_date.iloc[0],
            snapshot=snap,status="OK",members=len(mem),matched_names=len(set(b.index)&set(mem)),shift=0.)
        schedule.append(row)
        if set(b.index)!=set(mem):
            row["status"]="MEMBERS_CHANGED"
            continue
        px=marked.loc[date,b.index]/marked.loc[snap,b.index]
        if not px.gt(0).all() or not np.isfinite(px).all():
            row["status"]="UNKNOWN_DRIFT_PRICE"
            continue
        assert abs(b.sum()-1)<.002 and b.gt(0).all()
        base=b*px
        g=(base/base.sum()).rename("base").to_frame().join(h.set_index("instrument")[["industry","E1_78","RANK_MSE_78"]])
        g=g.rename(columns={"E1_78":"E1","RANK_MSE_78":"RANK"})
        common=g.E1.notna()&g.RANK.notna()
        prices=close[g.index]
        changes=pd.DataFrame({n:prices.iloc[i]/prices.iloc[i-n]-1 for n in [1,5]}).where(common,axis=0)
        valid=changes.dropna()
        g["REV"]=-valid.rank(pct=True).mean(axis=1)
        g["industry"]=g.industry.fillna("UNKNOWN")
        g,budget=transfers(g.reset_index(names="instrument"))
        selections.append(g.assign(signal_date=date))
        row.update(shift=budget,eligible=int(g[MODELS].notna().all(axis=1).sum()))
    p=pd.concat(selections,ignore_index=True)
    p.to_parquet(D/"targets.parquet",index=False)
    sch=pd.DataFrame(schedule)
    sch.to_csv(D/"schedule.csv",index=False)
    dump(D/"selection.json",{name:sha(D/name) for name in ["targets.parquet","schedule.csv","inputs.json"]})
    print(sch.groupby([sch.exit_date.le(MAIN),"status"]).size(),flush=True)


if __name__=="__main__":
    run()
