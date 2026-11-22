"""Join the sealed revenue vintages as of the signal, then freeze all matched baskets."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
D=ROOT/"results"
EP=ROOT.parents[1]
RANK=EP/"extensions/rank_change_20261122"
INTRA=EP/"extensions/intraday_reversal_20261122"
FIN=next(EP.parent.glob("33_*/restart/financial_events"))
TIMED=next(EP.parent.glob("35_*/data/financial_timed_facts.parquet"))
sys.path[:0]=[str(RANK),str(INTRA),str(EP/"code")]
from select_targets import pair_group, CALIPERS, FIELDS, SCORE
from core import PRIVATE, sha, dump, clean

MAIN=pd.Timestamp("2025-03-03")
END=pd.Timestamp("2026-10-12")


def run():
    D.mkdir(exist_ok=True)
    if (D/"selection.json").exists():
        raise RuntimeError("Use a fresh extension directory to repeat a sealed run")
    panel_path=RANK/"results/ranks_targets.parquet"
    fields=["instrument","signal_date","entry_date","exit_date","entry_idx","exit_idx","industry","state",SCORE,SCORE+"_d","mom5","mom20","base"]
    panel=pd.read_parquet(panel_path,columns=fields)
    calendar=pd.read_parquet(PRIVATE/"market.parquet").index
    events=pd.read_parquet(FIN/"stock_available_events.parquet")
    keep=events.instrument.isin(panel.instrument)&events.state_accepted&~events.left_censored
    f=events[keep].sort_values(["known_date","instrument"]).copy()
    assert not f.duplicated(["instrument","known_date"]).any()
    assert (f.available_date>=f.current_update).all() and (f.available_date>=f.current_notice).all()
    assert (f.current_notice>=f.period_end).all()
    past=f.available_date.ge(calendar.min())
    assert np.array_equal(calendar[calendar.searchsorted(f.loc[past,"available_date"],side="right")],f.loc[past,"known_date"])
    assert np.allclose(f.acceleration,f.growth-f.previous_growth)
    receipt=json.loads((FIN/"receipt.json").read_text())
    script=FIN.parent/"src/financial_events.py"
    assert sha(script)==receipt["code_sha256"]
    source_audit=[]
    for name,h in receipt["source_hashes"].items():
        code,exchange=Path(name).stem.split(".")
        if exchange+code in set(panel.instrument.unique()):
            assert sha(name)==h
            source_audit.append(dict(instrument=exchange+code,path=name,sha256=h))
    pd.DataFrame(source_audit).to_csv(D/"raw_sources.csv",index=False)
    files=[ROOT/"PROTOCOL.md",Path(__file__),panel_path,FIN/"stock_available_events.parquet",FIN/"receipt.json",script,
           RANK/"select_targets.py",RANK/"evaluate.py",INTRA/"execution.py",EP/"code/accounts.py",EP/"code/core.py",EP/"config.yaml",
           PRIVATE/"market.parquet",TIMED,RANK/"results/daily.parquet",PRIVATE/"net_excess_20261116/H00300.CSI.json"]
    files += [PRIVATE/(n+".parquet") for n in ["qfq_close","qfq_open","open","opening_trade_status_v2","daily_members","limits/daily","suspensions/daily"]]
    dump(D/"inputs.json",{str(x):sha(x) for x in files})
    p=pd.merge_asof(panel.sort_values(["signal_date","instrument"]),f,left_on="signal_date",right_on="known_date",
                    by="instrument",direction="backward")
    known=p.known_date.notna()
    p["age_sessions"]=np.where(known,calendar.get_indexer(p.signal_date)-calendar.get_indexer(p.known_date),np.nan)
    p["period_age"]=(p.signal_date-p.period_end).dt.days
    p["notice_age"]=(p.signal_date-p.current_notice).dt.days
    p["usable"]=p.age_sessions.between(0,126)&p.period_age.between(0,550)&np.isfinite(p.acceleration)
    p["fresh"]=p.usable & p.kind.eq("NOTICE_ALIGNED_PROXY") & p.age_sessions.le(20) & p.period_age.le(180)
    p["old_notice"]=p.usable & p.notice_age.gt(180)
    p["tilt"]=p.base.copy()
    pairs=[]
    coverage=[]
    for date,idx in p.groupby("signal_date").groups.items():
        rows=p.loc[idx].set_index("instrument").sort_index()
        rows["row_id"]=p.loc[idx].set_index("instrument").index.map(dict(zip(p.loc[idx,"instrument"],idx)))
        scale=rows[FIELDS].std(ddof=0).to_numpy()*CALIPERS
        good=rows[rows.usable&rows.industry.ne("UNKNOWN")].dropna(subset=FIELDS)
        for (industry,decile),group in good.groupby(["industry",SCORE+"_d"]):
            for a,b,dist in pair_group(group[group.acceleration>0],group[group.acceleration<0],scale):
                x,y=group.loc[a],group.loc[b]
                delta=x[FIELDS].astype(float)-y[FIELDS].astype(float)
                pairs.append(dict(signal_date=date,positive=a,negative=b,decile=decile,industry=industry,distance=dist,
                     score_gap_sd=delta.iloc[0]*CALIPERS[0]/scale[0],mom5_gap_sd=delta.iloc[1]*CALIPERS[1]/scale[1],
                     mom20_gap_sd=delta.iloc[2]*CALIPERS[2]/scale[2],fresh=bool(x.fresh and y.fresh),
                     stale=bool(x.old_notice and y.old_notice),pullback=bool(x.mom5<0 and y.mom5<0)))
                if decile==10:
                    p.loc[x.row_id,"tilt"]+=.5*x.base
                    p.loc[y.row_id,"tilt"]-=.5*y.base
        top=rows[rows.base>0]
        coverage.append(dict(signal_date=date,stocks=len(rows),state=rows.known_date.count(),usable=rows.usable.sum(),fresh=rows.fresh.sum(),
              old_notice=rows.old_notice.sum(),top=len(top),top_usable=top.usable.sum(),top_fresh=top.fresh.sum(),
              period_age_median=rows.loc[rows.usable,"period_age"].median(),notice_age_median=rows.loc[rows.usable,"notice_age"].median()))
    weights=p.groupby(["signal_date","industry"])[["base","tilt"]].sum()
    assert np.allclose(weights.base,weights.tilt) and (p.base.gt(0)==p.tilt.gt(0)).all()
    p.to_parquet(D/"panel.parquet",index=False)
    pd.DataFrame(coverage).to_csv(D/"coverage.csv",index=False)
    pd.DataFrame(pairs).to_csv(D/"pairs.csv",index=False)
    timed=pd.read_parquet(TIMED)
    dump(D/"source_scope.json",clean(dict(archived_sources=receipt["sources"],verified_pool_files=len(source_audit),
         universe_names=panel.instrument.nunique(),eligible_states=len(f),event_kinds=f.kind.value_counts().to_dict(),
         audited_document_facts=len(timed),audited_revenue_rows=int(timed.field.str.contains("reported_revenue").sum()),
         reviewed_revenue_periods=timed.loc[timed.field.str.contains("reported_revenue"),"event_time"].astype(str).tolist())))
    dump(D/"selection.json",{x.name:sha(x) for x in sorted(D.iterdir())})
    print("Sealed",len(p),"rows",len(pairs),"pairs",flush=True)


if __name__=="__main__":
    run()
