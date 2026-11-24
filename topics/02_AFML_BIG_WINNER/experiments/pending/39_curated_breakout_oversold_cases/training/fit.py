"""Train original-label Ridge on the complete weekly pool or matched weekly examples.

Prepare weekly.py first. Each eligible historical quarter uses a single transform and
coefficient vector for both deployment pools. Only the audit reads outer H10 outcomes.
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EP37 = next(HERE.parent.glob("37_*")) / "extensions/original78_rankic_20261118"
sys.path[:0] = [str(HERE), str(EP37)]
from common import MARKET, PANEL, sha
import breakout
import oversold
from model import ridge, predict

OUT = HERE / "results/training_fit"
WEEKLY = HERE / "results/training_weekly/panel.parquet"
NARROW = EP37 / "local_cache/h10_features.parquet"
WIDE = MARKET / "wide_features.parquet"
DICTIONARY = EP37 / "outputs/original_78_features.csv"
COLS = pd.read_csv(DICTIONARY).feature.tolist()
KEY = ["signal_date", "instrument"]
STRATA = ["signal_date", "selected"]
SEEDS = [39, 139, 239, 339, 439]
MIN_ROWS = 78
MIN_DATES = 10


def training_selections(weekly):
    """Pair within dates only. Date-constant label maturities allow safe prefix reuse."""
    dated = weekly.dropna(subset=["score", "score_pct", "selected", "maturity"]).copy()
    assert dated.groupby("signal_date").maturity.nunique().eq(1).all()
    dated["selected"] = dated.selected.astype(bool)
    selections = []
    for task in ["breakout", "oversold"]:
        if task == "breakout":
            cases = breakout.classify(dated)
            pairs = breakout.match_pairs(cases)
            ids = pairs.continued_id.to_list() + pairs.failed_id.to_list()
            chosen = cases.loc[cases.case_id.isin(ids)].copy()
        else:
            cases = oversold.make_cases(dated)
            pairs = oversold.match_outcomes(cases)
            keys = pd.concat([pairs[["signal_date", prefix+"_instrument"]].rename(
                columns={prefix+"_instrument":"instrument"}) for prefix in ["rebound", "fall"]])
            chosen = cases.merge(keys, on=KEY, validate="1:1")
        assert len(chosen) == 2 * len(pairs)
        assert chosen.target_rank.notna().all() and not chosen.duplicated(KEY).any()
        pairs.to_parquet(OUT/(task+"_weekly_pairs.parquet"), index=False)
        # Sampling frame sees only eligibility, OOF state, trigger, and target availability.
        random_frame = cases.dropna(subset=["target_rank"]).sort_values(KEY)
        populations = {key: group for key, group in random_frame.groupby(STRATA, observed=True)}
        counts = chosen.groupby(STRATA, observed=True).size()
        audit_cols = KEY+["maturity","selected","target_rank","label"]
        selections.append(chosen[audit_cols].assign(model=task+"_curated"))
        for seed in SEEDS:
            sampled = []
            for (date, selected), k in counts.items():
                population = populations[date, selected]
                # One independent draw per date and original D10 status. An added date cannot
                # alter which of the already observed names are sampled on an earlier date.
                rng = np.random.default_rng([seed,int(date.strftime("%Y%m%d")),int(selected)])
                sampled.append(population.iloc[rng.choice(len(population), k, replace=False)][audit_cols])
            matched = pd.concat(sampled, ignore_index=True)
            pd.testing.assert_series_equal(matched.groupby(STRATA, observed=True).size(), counts)
            assert not matched.duplicated(KEY).any()
            selections.append(matched.assign(model=f"{task}_random_{seed}"))
    return pd.concat(selections, ignore_index=True).sort_values(["model",*KEY])


def outer_features():
    keys = pd.read_parquet(PANEL, columns=["pool",*KEY,"score","scope","ret10","selected"])
    assert not keys.duplicated(["pool",*KEY]).any()
    pieces = []
    for pool, archive in [("CSI300",NARROW),("CSI800",WIDE)]:
        expected = keys[keys.pool.eq(pool)].copy()
        x = pd.read_parquet(archive, columns=KEY+COLS,
                            filters=[("signal_date","in",list(expected.signal_date.unique()))])
        panel = expected.merge(x, on=KEY, validate="1:1", how="left", indicator=True)
        assert panel._merge.eq("both").all() and len(panel)==len(expected)
        pieces.append(panel.drop(columns="_merge").rename(columns={"score":"archived_full_score"}))
    return pd.concat(pieces, ignore_index=True)


def ranking_audit(scores, outer):
    fields=["pool",*KEY]
    z=scores.merge(outer[fields+["scope","ret10","selected"]],on=fields,validate="m:1")
    group=["pool","model","scope","signal_date"]
    z=z.sort_values(group+["score","instrument"])
    g=z.groupby(group,sort=False,observed=True)
    n=g.score.transform("size")
    z["d10"] = g.cumcount() >= n - n//10
    assert z.loc[z.model.eq("full"),"selected"].eq(z.loc[z.model.eq("full"),"d10"]).all()
    z["overlap"]=z.selected & z.d10
    z["head_ret"]=z.ret10.where(z.d10)
    z["head_known"]=z.head_ret.notna()
    # Pearson of within-day ranks on common finite rows is Spearman, including ties.
    z["a"]=z.score.where(z.ret10.notna()).groupby([z[c] for c in group]).rank()
    z["b"]=g.ret10.rank()
    a=z.a-g.a.transform("mean"); b=z.b-g.b.transform("mean")
    z["ab"]=a*b;z["aa"]=a*a;z["bb"]=b*b
    tab=g.agg(eligible=("instrument","size"), known=("ret10","count"),d10=("d10","sum"),
              head_known=("head_known","sum"),overlap_count=("overlap","sum"),
              gross_d10=("head_ret","mean"), gross_pool=("ret10","mean"),
              ab=("ab","sum"),aa=("aa","sum"),bb=("bb","sum")).reset_index()
    tab["rankic"]=tab.ab/(tab.aa*tab.bb).pow(.5)
    tab["overlap"]=tab.overlap_count/tab.d10
    tab["gross_selection_bp"]=10000*(tab.gross_d10-tab.gross_pool)
    return tab.drop(columns=["aa","ab","bb"])


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    tr=pd.read_parquet(WEEKLY).sort_values(KEY)
    assert len(COLS)==78 and not tr.duplicated(KEY).any()
    assert not tr.dropna(subset=["maturity"]).groupby("signal_date").maturity.nunique().gt(1).any()
    membership=training_selections(tr)
    membership.to_parquet(OUT/"training_membership.parquet",index=False)
    x=outer_features()
    data=tr.set_index(KEY,drop=False)
    all_scores=[];audits=[];fits={};parity=[];coverage=[]
    for q,test in x.groupby(x.signal_date.dt.to_period("Q")):
        cutoff=q.start_time;fits[str(q)]={}
        full=tr[tr.maturity.lt(cutoff)&tr.target_rank.notna()]
        prefix=membership[membership.maturity.lt(cutoff)]
        groups={"full":full}
        for name,rows in prefix.groupby("model",sort=True):
            ix=pd.MultiIndex.from_frame(rows[KEY])
            groups[name]=data.loc[ix].reset_index(drop=True)
        for name,rows in groups.items():
            task=name.split("_")[0]
            side_count=None
            if name!="full":
                selected=prefix[prefix.model.eq(task+"_curated")]
                side_count=selected.label.nunique()
                assert len(rows)==len(selected)
                available=len(selected)>=MIN_ROWS and selected.signal_date.nunique()>=MIN_DATES and side_count==2
            else:
                available=True
            audits.append(dict(quarter=str(q),model=name,available=available,train_rows=len(rows),
                train_dates=rows.signal_date.nunique(),train_names=rows.instrument.nunique(),
                train_start=rows.signal_date.min(),train_end=rows.signal_date.max(),
                train_max_maturity=rows.maturity.max(),cutoff_exclusive=cutoff,
                oof_rows=rows.score.notna().sum(),label_sides=side_count))
            if not available:continue
            assert rows.maturity.max()<cutoff and rows.target_rank.notna().all()
            # Sorting by archive keys keeps the full set in the same row order as the source.
            m=ridge(rows,COLS,"target_rank");fits[str(q)][name]=m
            pred=predict(test[COLS],m)
            assert np.isfinite(pred).all()
            if name=="full":
                for pool,g in test.assign(new_score=pred).groupby("pool"):
                    err=(g.new_score-g.archived_full_score).abs().max()
                    assert err<1e-10,(q,pool,err)
                    parity.append(dict(quarter=str(q),pool=pool,rows=len(g),max_abs_error=err))
            all_scores.append(test[["pool",*KEY]].assign(model=name,score=pred))
        coverage.append(dict(quarter=str(q),available_models=len(fits[str(q)]),planned_models=13))
        print(q,{k:len(v) for k,v in groups.items() if k=="full" or k.endswith("curated")},flush=True)
    scores=pd.concat(all_scores,ignore_index=True)
    assert not scores.duplicated(["pool","model",*KEY]).any()
    pd.DataFrame(audits).to_csv(OUT/"folds.csv",index=False)
    pd.DataFrame(parity).to_csv(OUT/"full_score_parity.csv",index=False)
    pd.DataFrame(coverage).to_csv(OUT/"quarter_coverage.csv",index=False)
    (OUT/"models.json").write_text(json.dumps(fits,allow_nan=False))
    tmp=OUT/"scores.partial.parquet"
    scores.to_parquet(tmp,index=False);tmp.replace(OUT/"scores.parquet")
    tab=ranking_audit(scores,x);tab.to_parquet(OUT/"ranking_by_date.parquet",index=False)
    tab.groupby(["pool","scope","model"]).agg(dates=("signal_date","size"),rankic=("rankic","mean"),
        overlap=("overlap","mean"),gross_selection_bp=("gross_selection_bp","mean")).to_csv(OUT/"ranking_summary.csv")
    outputs=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!="receipt.json"]
    inputs=[WEEKLY,NARROW,WIDE,DICTIONARY,PANEL,EP37/"model.py",HERE/"breakout.py",HERE/"oversold.py",Path(__file__)]
    (OUT/"receipt.json").write_text(json.dumps(dict(seeds=SEEDS,min_unique_stock_dates=MIN_ROWS,min_dates=MIN_DATES,
        curated_requires_both_sides=True,ridge_alpha=10,columns=COLS,inputs={str(p):sha(p) for p in inputs},
        outputs={p.name:sha(p) for p in outputs}),indent=2)+"\n")


if __name__=="__main__":
    main()
