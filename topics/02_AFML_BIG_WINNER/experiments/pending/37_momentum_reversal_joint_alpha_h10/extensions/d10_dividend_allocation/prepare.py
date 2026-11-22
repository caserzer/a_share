"""Build paired H10 outcomes, then fit only on labels mature at each quarterly cutoff."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
EP = ROOT.parents[1]
RANK = ROOT.parent / "rank_change_20261122"
INTRA = ROOT.parent / "intraday_reversal_20261122"
sys.path[:0] = [str(EP/"code"), str(INTRA)]
from core import PRIVATE, sha, dump
import accounts

ARCHIVE = Path.home()/".cache/golden_loop/repository-migration-20261012/forward_return_data_prep/reports/20260915/evidence/initial/csi_perf_000922.json"
TARGETS = RANK/"results/ranks_targets.parquet"
BENCH = PRIVATE/"net_excess_20261116/H00300.CSI.json"
MAIN = pd.Timestamp("2025-03-03")
FEATURES = ["trend20", "breadth", "relative20"]


def dividend(calendar):
    assert sha(ARCHIVE) == "8ee726856e6e99673c4c952a65d8c44985339cca77553a30556e8476826a6e6b"
    x = pd.DataFrame(json.loads(ARCHIVE.read_text())["data"])
    assert x.indexCode.eq("000922").all() and x.tradeDate.is_unique
    x.index = pd.to_datetime(x.tradeDate)
    return x[["open","close"]].astype(float).where(lambda a: a > 0).reindex(calendar)


def samples(m, panel):
    idx = dividend(m.days)
    market = pd.read_parquet(PRIVATE/"market.parquet").reindex(m.days)
    trend = market.close / market.close.shift(20)-1
    relative = idx.close / idx.close.shift(20)-1-trend
    rows = []
    for date, group in panel.groupby("signal_date",sort=True):
        i = m.days.get_loc(date)
        earlier, middle, recent = m.c[i-60], m.c[i-5], m.c[i]
        known = m.members[i] & (earlier>0) & (middle>0) & (recent>0)
        down = (middle<earlier) & (recent<middle)
        chosen = group[group.base.gt(0)].copy()
        assert chosen.RANK_MSE_78_d.eq(10).all()
        assert np.allclose(chosen.base, 1/len(chosen))
        first = chosen.iloc[0]
        e,x = int(first.entry_idx),int(first.exit_idx)
        assert m.days[e]==first.entry_date and e==i+1 and x==e+10
        row = dict(signal_date=date, entry_date=first.entry_date,exit_date=first.exit_date,
            trend20=trend.at[date],relative20=relative.at[date],breadth=down[known].mean(),
            members=m.members[i].sum(),known=known.sum(),scoreable=len(group),
            scoreable_breadth=group.state.eq("DD").mean(),d10_n=len(chosen),d10=np.nan,red=np.nan,
            filled=0,blocked_exit=0,label=np.nan,gap=np.nan,event_status="H10_IMMATURE")
        if x < len(m.days) and pd.notna(first.exit_date):
            assert m.days[x]==first.exit_date
            stats,_=accounts.event(m,chosen.assign(weight=chosen.base),0.,0.)
            row.update(filled=stats["bought"],blocked_exit=stats["blocked_exit_count"])
            if stats["complete_exit"] and stats["any_entry"]:
                row["d10"]=stats["net_return"]
            row["red"]=idx.open.iloc[x]/idx.open.iloc[e]-1
            if np.isfinite(row["d10"]) and np.isfinite(row["red"]):
                gap=row["d10"]-row["red"]
                row.update(gap=gap,label=float(gap>0) if gap!=0 else np.nan,event_status="OK" if gap!=0 else "TIE")
            else:
                row["event_status"]=";".join(k for k in ["D10_EXIT_OR_ENTRY" if pd.isna(row["d10"]) else "",
                                                        "DIVIDEND_QUOTE" if pd.isna(row["red"]) else ""] if k)
        rows.append(row)
    return pd.DataFrame(rows).set_index("signal_date")


def fit(frame):
    frame=frame.copy()
    frame["prob"]=np.nan
    frame["train_n"]=0
    frame["base_rate"]=np.nan
    frame["cutoff"]=pd.NaT
    fits=[]
    for quarter,group in frame.groupby(frame.index.to_period("Q")):
        cutoff=group.index[0]
        train=frame.loc[frame.exit_date.le(cutoff)].dropna(subset=FEATURES+["label"])
        frame.loc[group.index,["train_n","cutoff"]]=[len(train),cutoff]
        if len(train)<36 or train.label.nunique()!=2:
            continue
        assert train.index.max()<cutoff
        scaler=StandardScaler().fit(train[FEATURES])
        model=LogisticRegression(C=1,solver="lbfgs",max_iter=1000,tol=1e-10).fit(scaler.transform(train[FEATURES]),train.label)
        test=group.dropna(subset=FEATURES)
        if len(test):
            frame.loc[test.index,"prob"]=model.predict_proba(scaler.transform(test[FEATURES]))[:,1]
        frame.loc[group.index,"base_rate"]=train.label.mean()
        fits.append(dict(quarter=str(quarter), cutoff=cutoff, n=len(train),latest_exit=train.exit_date.max(),
                         features=FEATURES, mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
                         coef=model.coef_[0].tolist(),intercept=model.intercept_[0]))
    frame["allocation"]=frame.prob.ffill().fillna(.5)
    frame["phase"]=np.where(frame.index<frame.prob.first_valid_index(),"warmup","test")
    frame["rule"]=np.where(frame.trend20<0,.25,.75)
    return frame,fits


def run():
    OUT.mkdir(exist_ok=True)
    files=[ROOT/"DESIGN.md",ROOT/"RUN_SPEC.md",Path(__file__),ARCHIVE,TARGETS,BENCH, EP/"config.yaml",
           EP/"code/core.py",EP/"code/accounts.py",INTRA/"execution.py",RANK/"results/daily.parquet"]
    files.extend(PRIVATE/(name+".parquet") for name in ["market","qfq_close","qfq_open","open","daily_members",
                  "opening_trade_status_v2","limits/daily","suspensions/daily"])
    dump(OUT/"inputs.json",{str(p):sha(p) for p in files})
    accounts.OUT=OUT
    m=accounts.Market()
    frame,fits=fit(samples(m,pd.read_parquet(TARGETS)))
    frame.to_csv(OUT/"signals.csv")
    dump(OUT/"fits.json",fits)
    print(frame.groupby("phase").size(),frame.prob.first_valid_index(),flush=True)


if __name__=="__main__":
    run()
