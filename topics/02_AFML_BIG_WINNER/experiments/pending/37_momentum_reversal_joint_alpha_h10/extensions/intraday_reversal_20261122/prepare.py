"""Freeze point-in-time split-return predictors and the three paired ridge rankings."""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
EP=ROOT.parents[1]
OLD=EP/"extensions/original78_rankic_20261118"
D=ROOT/"results"
sys.path[:0]=[str(OLD),str(EP/"code")]
from core import PRIVATE, SOURCE, sha, dump, assign_deciles, centered_rank
from model import ridge, predict

KEY=["signal_date","instrument"]
MODELS=["E1_78","RANK_MSE_78","split","joint"]
MAIN=pd.Timestamp("2025-03-03")
END=pd.Timestamp("2026-10-12")


def add_features(frames):
    def read(name):
        return pd.read_parquet(PRIVATE/(name+".parquet"))
    close=read("qfq_close")
    op=read("qfq_open").reindex_like(close)
    recent=close.shift(5)
    day=np.log(close/op).rolling(5).sum()
    night=np.log(op/close.shift()).rolling(5).sum()
    trend=recent/close.shift(60)-1
    factor=close/read("close").reindex_like(close)
    state=read("opening_trade_status_v2").reindex_like(close)
    high=read("qfq_high").reindex_like(close)
    low=read("qfq_low").reindex_like(close)
    adjust=np.log(factor/factor.shift())
    gap=np.log(op/close.shift())
    flags={"factor_change":adjust.abs().gt(.005),"trade_status":state.ne(1)|state.shift().ne(1),
           "open_anomaly":gap.abs().gt(.10)|(op>high+1e-8)|(op<low-1e-8),
           "audit_missing":adjust.isna()|gap.isna()|op.isna()|close.isna()|high.isna()|low.isna()|state.isna()|state.shift().isna()}
    features={"split5":day-night,"split_trend":(day-night)*trend,
              "identity_err":(day+night-np.log(close/recent)).abs()}
    features.update({n:x.rolling(5).max() for n,x in flags.items()})
    for frame in frames:
        i=close.index.get_indexer(frame.signal_date)
        j=close.columns.get_indexer(frame.instrument)
        assert min(i)>=0 and min(j)>=0
        for n,mat in features.items():
            frame[n]=mat.to_numpy()[i,j]
        frame["flagged"]=frame[list(flags)].fillna(1).astype(bool).any(axis=1)|frame.split5.isna()
        assert frame.identity_err.max()<1e-12


def main():
    D.mkdir(exist_ok=True)
    if (D/"selection.json").exists():
        raise RuntimeError("Use a fresh extension directory to repeat a sealed run.")
    files=[PRIVATE/(n+".parquet") for n in ["features","labels","qfq_close","qfq_open","qfq_high","qfq_low","close",
           "opening_trade_status_v2","open","daily_members","limits/daily","suspensions/daily","market"]]
    files += [OLD/"local_cache"/(n+".parquet") for n in ["predictions","h10_features","rankings","daily_accounts"]]
    files += [OLD/"local_cache/ledgers/RANK_MSE_78_D10_primary_main_flat_orders.parquet",
              OLD/"model.py",OLD/"outputs/folds.csv",EP/"code/core.py",EP/"code/accounts.py",EP/"config.yaml",
              SOURCE/"configs/feature_dictionary.csv",EP/"outputs/local_cache/labels.parquet",
              PRIVATE/"net_excess_20261116/H00300.CSI.json",ROOT/"PROTOCOL.md",Path(__file__)]
    dump(D/"inputs.json",{str(p):sha(p) for p in files})
    base=pd.read_parquet(OLD/"local_cache/h10_features.parquet")
    weekly=pd.read_parquet(PRIVATE/"features.parquet")
    add_features([weekly,base])
    train=weekly.merge(pd.read_parquet(PRIVATE/"labels.parquet",columns=KEY+["h10","target_z","h10_mature"]),on=KEY,validate="1:1")
    old=pd.read_parquet(OLD/"local_cache/predictions.parquet",columns=KEY+MODELS[:2])
    oldfits=pd.read_csv(OLD/"outputs/folds.csv").query("model=='RANK_MSE_78'").set_index("fold")
    core=pd.read_csv(SOURCE/"configs/feature_dictionary.csv").query("group=='core'").feature.tolist()
    scores=[]
    fits=[]
    checks=[]
    stored={}
    for quarter,group in base.groupby(base.signal_date.dt.to_period("Q")):
        mature=train[train.score_eligible & train.target_z.notna() & train.h10_mature.lt(quarter.start_time) & train.signal_date.lt(quarter.start_time)].copy()
        assert len(mature)==oldfits.loc[str(quarter),"train_rows"]
        mature["target_rank"]=mature.groupby("signal_date").h10.transform(centered_rank)
        p=group[KEY+["entry_date","exit_date","entry_idx","exit_idx","state","flagged","factor_change","open_anomaly","trade_status","audit_missing","identity_err","split5","split_trend"]].copy()
        for name,cols in zip(MODELS,[core,core,core+["split5"],core+["split5","split_trend"]]):
            model=ridge(mature,cols,"target_z" if name=="E1_78" else "target_rank")
            p[name]=predict(group[cols],model)
            stored[str(quarter)+"_"+name]=model
            fits.append(dict(quarter=str(quarter),model=name,train_rows=len(mature),latest_maturity=mature.h10_mature.max(),
                             split_coefficient=model["coef"][78] if len(cols)>78 else None,interaction_coefficient=model["coef"][79] if len(cols)>79 else None))
        ref=p.merge(old,on=KEY,validate="1:1",suffixes=("","_old"))
        for name in MODELS[:2]:
            err=(ref[name]-ref[name+"_old"]).abs().max()
            assert len(ref)==len(p) and err<1e-10
            checks.append(dict(quarter=str(quarter),model=name,max_error=err))
        scores.append(p)
    p=pd.concat(scores,ignore_index=True)
    for name in MODELS:
        p[name+"_d"]=p.groupby("signal_date",group_keys=False)[[name,"instrument"]].apply(lambda g:assign_deciles(g,name)).astype(int)
    p.to_parquet(D/"scores.parquet",index=False)
    pd.DataFrame(fits).to_csv(D/"folds.csv",index=False)
    pd.DataFrame(checks).to_csv(D/"replay.csv",index=False)
    dump(D/"models.json",stored)
    audit=p.groupby("signal_date").agg(eligible=("instrument","size"),flagged=("flagged","sum"),factor_proxy=("factor_change","sum"),
          abnormal=("open_anomaly","sum"),trade_status=("trade_status","sum"),missing=("audit_missing","sum"),max_err=("identity_err","max"))
    audit.to_csv(D/"quality.csv")
    dump(D/"selection.json",{f.name:sha(f) for f in D.iterdir() if f.is_file()})
    print("Sealed",len(p),"rows",len(fits),"fits",flush=True)


if __name__=="__main__":
    main()
