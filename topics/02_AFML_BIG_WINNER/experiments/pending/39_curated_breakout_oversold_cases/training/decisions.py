"""Read frozen outer predictions, then inspect outcomes and equal-cash seat changes."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/"results"
OUT=RES/"training_review"
KEY=["pool","signal_date","instrument"]
DAY=KEY[:2]


def case_labels():
    sets=[]
    for task in ["breakout","oversold"]:
        cases=pd.read_csv(RES/f"{task}_cases.csv.gz",usecols=KEY+["label"],parse_dates=["signal_date"])
        sets.append(cases.rename(columns={"label":task+"_label"}))
    return sets


def paired_case_accuracy(scores):
    comparison=[]
    for task in ["breakout","oversold"]:
        pairs=pd.read_csv(RES/f"{task}_pairs.csv.gz",parse_dates=["signal_date"])
        if task=="breakout":
            pairs["good"]=pairs.continued_id.str.split("_").str[-1]
            pairs["bad"]=pairs.failed_id.str.split("_").str[-1]
        else:
            pairs=pairs.rename(columns={"rebound_instrument":"good","fall_instrument":"bad"})
        for model,g in scores.groupby("model"):
            if model!="full" and not model.startswith(task+"_"):continue
            score=g.set_index(KEY).score
            refs=[pd.MultiIndex.from_arrays([pairs.pool,pairs.signal_date,pairs[name]]) for name in ["good","bad"]]
            good,bad=(score.reindex(x).to_numpy() for x in refs)
            valid=np.isfinite(good)&np.isfinite(bad)
            q=pairs.loc[valid,DAY+["scope","selected"]].copy()
            q["correct"]=np.where(good[valid]==bad[valid],.5,good[valid]>bad[valid])
            q=q.groupby(["pool","scope","signal_date","selected"]).correct.agg(["sum","size"]).reset_index()
            comparison.append(q.assign(model=model,task=task))
    pd.concat(comparison,ignore_index=True).to_parquet(OUT/"matched_case_accuracy.parquet",index=False)


def main():
    OUT.mkdir(exist_ok=True)
    panel=pd.read_parquet(RES/"panel.parquet")
    for tag in case_labels():
        panel=panel.merge(tag,on=KEY,how="left",validate="1:1")
    panel["gates"]=panel.entry_buy.fillna(False) & panel.exit_sell.fillna(False) & panel.ret10.notna()
    scores=pd.read_parquet(RES/"training_fit/scores.parquet")
    paired_case_accuracy(scores)
    rows=[]; swaps=[]; quality=[]
    for model,part in scores.groupby("model"):
        g=part[KEY+["score"]].rename(columns={"score":"prediction"}).merge(panel,on=KEY,validate="1:1")
        assert len(g)==len(part)
        g=g.sort_values(DAY+["prediction","instrument"],ascending=[True,True,False,False])
        day=g.groupby(DAY,sort=False)
        g["position"]=day.cumcount()+1
        g["picks"]=g.position.le(day.position.transform("size")//10)
        if model=="full":
            assert g.selected.eq(g.picks).all()
        for task,good,bad in [("breakout","延续","失败"),("oversold","止跌反弹","持续下跌")]:
            if model!="full" and not model.startswith(task+"_"): continue
            outcome=task+"_label"
            t=g[g[task].fillna(False)].copy()
            t["pred_rank"]=t.groupby(DAY).prediction.rank()
            # Both variables must use identical nonmissing observations for Spearman.
            t.loc[t.ret10.isna(),"pred_rank"]=np.nan
            t["pred_rank"]=t.groupby(DAY).pred_rank.rank()
            t["ret_rank"]=t.groupby(DAY).ret10.rank()
            ic=t.groupby(DAY)[["pred_rank","ret_rank"]].corr().xs("pred_rank",level=-1).ret_rank
            quality.append(ic.rename("trigger_ic").reset_index().assign(model=model,task=task))
            for state,sub in [("picked",t[t.picks]),("added",t[t.picks & ~t.selected]),("dropped",t[t.selected & ~t.picks]),("retained",t[t.selected & t.picks]),("all",t)]:
                z=sub.assign(good=sub[outcome].eq(good),bad=sub[outcome].eq(bad),
                    later_gain_after_low=sub[outcome].eq("破低后收涨"),known_label=~sub[outcome].isin(["路径未知","未知"]),
                    beats_pool=sub.ret10.gt(sub.pool_ret10).where(sub.ret10.notna()),positive=sub.ret10.gt(0).where(sub.ret10.notna()))
                v=z.groupby(["pool","scope"]).agg(stocks=("instrument","size"),dates=("signal_date","nunique"),
                     known_labels=("known_label","sum"),good=("good","sum"),bad=("bad","sum"),
                     dipped_then_gained=("later_gain_after_low","sum"),positive=("positive","sum"),known_returns=("ret10","count"),
                     mean_ret10=("ret10","mean"),mean_excess=("relative_ret10","mean"),beats_pool=("beats_pool","sum"),
                     above_high_days=("above_high_days","mean"),mae=("mae10","mean")).reset_index()
                rows.append(v.assign(task=task,model=model,state=state))
        if model=="full":continue
        added=g[g.picks & ~g.selected].copy()
        removed=g[g.selected & ~g.picks].sort_values(DAY+["score","instrument"],ascending=[True,True,False,False]).copy()
        fields=["instrument","ret10","gates","selected","entry_buy","exit_sell","in_legacy300","industry","oversold_label","breakout_label"]
        for f in [added,removed]: f["slot"]=f.groupby(DAY).cumcount()+1
        x=added[DAY+["scope","slot"]+fields].merge(removed[DAY+["slot"]+fields],on=DAY+["slot"],suffixes=("_new","_old"),validate="1:1")
        assert len(x)==len(added)==len(removed)
        x["fillable"]=x.gates_new & x.gates_old
        x["quote_diff"]=x.ret10_new-x.ret10_old
        x["equal_cash_netdiff"]=(x.quote_diff*.998/1.001).where(x.fillable)
        swaps.append(x.assign(model=model))
    pd.concat(rows,ignore_index=True).to_csv(OUT/"trigger_decisions.csv",index=False)
    pd.concat(quality,ignore_index=True).to_parquet(OUT/"trigger_rankic.parquet",index=False)
    changes=pd.concat(swaps,ignore_index=True)
    changes.to_parquet(OUT/"changed_seats.parquet",index=False)
    changes.groupby(["pool","scope","model"]).agg(paired_seats=("slot","size"),both_marked=("quote_diff","count"),both_fillable=("fillable","sum"),equal_cash_netdiff=("equal_cash_netdiff","mean"),quote_diff=("quote_diff","mean")).to_csv(OUT/"seat_summary.csv")


if __name__=="__main__":main()
