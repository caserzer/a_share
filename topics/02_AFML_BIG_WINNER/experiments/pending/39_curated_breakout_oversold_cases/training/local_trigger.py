"""EP39 supplementary frozen-score test inside each trigger cohort.

Before opening these conditional tails: require >=10 triggers; take the floor of
one fifth at each end; use common complete-quote dates across all seven arms.
The account data and model coefficients are not inputs to tail construction.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = RES / "training_local"
TASKS = ["breakout", "oversold"]
SEEDS = [39, 139, 239, 339, 439]
KEY = ["pool","signal_date","instrument"]
DAY = ["pool","scope","signal_date"]
MIN_TRIGGER = 10
TAIL_DIVISOR = 5


def observe(panel, scores):
    details, dates, audits = [], [], []
    cal = panel[DAY].drop_duplicates()
    for task in TASKS:
        arms = ["full",task+"_curated",*(f"{task}_random_{seed}" for seed in SEEDS)]
        cohort = panel.loc[panel[task].fillna(False), KEY+["scope","ret10","entry_buy","exit_sell"]]
        counts = cal.merge(cohort.groupby(DAY).size().rename("triggers").reset_index(), on=DAY, how="left")
        counts["triggers"] = counts.triggers.fillna(0).astype(int)
        for model in arms:
            pred = scores[scores.model.eq(model)][KEY+["score"]]
            g = cohort.merge(pred, on=KEY, validate="1:1", how="left")
            assert np.isfinite(g.score).all()
            g = g.sort_values(DAY+["score","instrument"])
            bydate = g.groupby(DAY,sort=False)
            n = bydate.score.transform("size")
            size = n // TAIL_DIVISOR
            rank = bydate.cumcount()
            mask = (n>=MIN_TRIGGER) & ((rank<size)|(rank>=n-size))
            g = g.loc[mask].copy()
            g["tail"] = np.where(rank.loc[mask]<size.loc[mask],"bottom","top")
            g["model"] = model
            g["task"] = task
            g["two_gates_pass"] = g.entry_buy.fillna(False) & g.exit_sell.fillna(False)
            details.append(g)
            tally = g.groupby(DAY+["tail"]).agg(n=("score","size"),known=("ret10","count"),
                     gross=("ret10","mean"),two_gates=("two_gates_pass","sum")).unstack("tail")
            tally.columns = ["_".join(c) for c in tally.columns]
            d = tally.reset_index().assign(model=model,task=task)
            assert d.n_top.eq(d.n_bottom).all()
            d["complete"] = d.n_top.eq(d.known_top) & d.n_bottom.eq(d.known_bottom)
            dates.append(d)
        period = pd.concat(dates[-len(arms):])
        complete = period.groupby(DAY).complete.sum().rename("complete_models").reset_index()
        counts = counts.merge(complete,on=DAY,how="left")
        counts["complete_models"] = counts.complete_models.fillna(0).astype(int)
        counts["eligible"] = counts.complete_models.eq(len(arms)) & counts.triggers.ge(MIN_TRIGGER)
        counts["reason"] = np.select([counts.triggers.lt(MIN_TRIGGER),~counts.eligible],
                                    ["fewer_than_10","incomplete_endpoint"],default="complete")
        audits.append(counts.assign(task=task))
    meta = pd.concat(audits,ignore_index=True)
    obs = pd.concat(dates,ignore_index=True).merge(meta[DAY+["task","eligible"]], on=DAY+["task"],validate="m:1")
    obs["spread_bp"] = (obs.gross_top-obs.gross_bottom)*10000
    return pd.concat(details,ignore_index=True),meta,obs


def paired_results(meta, obs):
    rows=[]
    for (pool,scope,task), dates in meta.groupby(["pool","scope","task"]):
        dates=dates.sort_values("signal_date")
        g=obs[(obs.pool==pool)&(obs.scope==scope)&(obs.task==task)&obs.eligible]
        values=g.pivot(index="signal_date",columns="model",values="spread_bp").reindex(dates.signal_date)
        rand=[f"{task}_random_{seed}" for seed in SEEDS]
        assert values.notna().sum(axis=1).isin([0,7]).all()
        cur=values[task+"_curated"]
        randmean=values[rand].mean(axis=1)
        # Preserve excluded H10 positions in the calendar when resampling.
        n=len(values);rng=np.random.default_rng(390510)
        ix=(rng.integers(n,size=(10000,(n+2)//3,1))+np.arange(3))%n
        ix=ix.reshape(10000,-1)[:,:n]
        for arm, contrast in [("full",cur-values.full),("random_mean",cur-randmean)]:
            draws=contrast.to_numpy()[ix]
            valid=np.isfinite(draws).sum(axis=1)>0
            intervals=np.quantile(np.nanmean(draws[valid],axis=1),[.025,.975])
            rows.append(dict(pool=pool,scope=scope,task=task,reference=arm,
                calendar=n,paired=len(g)//7,curated_spread_bp=cur.mean(),full_spread_bp=values.full.mean(),
                random_mean_spread_bp=randmean.mean(),random_min_bp=values[rand].mean().min(),
                random_max_bp=values[rand].mean().max(),pairs_positive=int(contrast.gt(0).sum()),
                delta_bp=contrast.mean(),low_bp=intervals[0],high_bp=intervals[1]))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p_path=RES/"panel.parquet";s_path=RES/"training_fit/scores.parquet"
    panel=pd.read_parquet(p_path,columns=KEY+["scope","breakout","oversold","ret10","entry_buy","exit_sell"])
    scores=pd.read_parquet(s_path)
    details,meta,obs=observe(panel,scores)
    details.to_parquet(OUT/"tail_constituents.parquet",index=False)
    meta.to_csv(OUT/"calendar.csv",index=False)
    obs.to_parquet(OUT/"group_by_date.parquet",index=False)
    audit=meta.groupby(["task","pool","scope","reason"]).size().rename("days").reset_index()
    audit.to_csv(OUT/"coverage.csv",index=False)
    summary=obs[obs.eligible].groupby(["task","pool","scope","model"]).agg(
        n=("signal_date","size"),mean_seats_per_tail=("n_top","mean"),gross_top=("gross_top","mean"),
        gross_bottom=("gross_bottom","mean"),spread_bp=("spread_bp","mean")).reset_index()
    summary.to_csv(OUT/"group_summary.csv",index=False)
    paired_results(meta,obs).to_csv(OUT/"paired.csv",index=False)
    def sha(path):
        with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
    files=[path for path in OUT.glob("*") if path.name!="receipt.json"]
    (OUT/"receipt.json").write_text(json.dumps(dict(min_scored_triggers=MIN_TRIGGER,tail_divisor=TAIL_DIVISOR,
       require_complete_quotes_all_seven=True,seeds=SEEDS,unordered_ties="score_then_instrument_ascending",
       inputs={str(path):sha(path) for path in [p_path,s_path,Path(__file__)]},
       outputs={p.name:sha(p) for p in sorted(files)}),indent=2)+"\n")


if __name__=="__main__":
    main()
