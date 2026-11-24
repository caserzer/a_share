"""Fit time-separated oversold event probabilities on all naturally occurring cases."""
import json
import os
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":
    for variable in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[variable] = "1"

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
EP39 = HERE.parent
EP37 = next(EP39.parent.glob("37_*")) / "extensions/original78_rankic_20261118"
sys.path[:0] = [str(EP39), str(EP37)]
from common import MARKET, PANEL, sha
from model import Transform
from oversold import make_cases, match_outcomes

OUT = HERE / "results/fit"
WEEKLY = HERE / "results/data/weekly.parquet"
NARROW = EP37 / "local_cache/h10_features.parquet"
WIDE = MARKET / "wide_features.parquet"
DICTIONARY = EP37 / "outputs/original_78_features.csv"
COLS = pd.read_csv(DICTIONARY).feature.tolist()
KEY = ["signal_date", "instrument"]
TEST_KEY = ["pool", *KEY]
SEEDS = [39, 139, 239, 339, 439]
WEIGHTS = ["hard", *[f"random_{seed}" for seed in SEEDS]]
HEADS = {"loss": "terminal_loss", "breach": "breach"}


def training_data():
    weekly = pd.read_parquet(WEEKLY)
    tr = weekly.loc[weekly.oversold.fillna(False)].sort_values(KEY).reset_index(drop=True)
    assert not tr.duplicated(KEY).any() and tr.pool.eq("CSI300").all()
    assert tr.maturity.notna().all() and tr.groupby("signal_date").maturity.nunique().eq(1).all()
    check_loss = tr.ret10.lt(0).astype("boolean").where(tr.ret10.notna())
    check_breach = tr.hold_low10.lt(tr.prior_low5).astype("boolean").where(
        tr.hold_low10.notna() & tr.prior_low5.notna())
    assert tr.terminal_loss.astype("boolean").equals(check_loss)
    assert tr.breach.astype("boolean").equals(check_breach)
    return tr


def extra_weights(tr):
    # Warm-up rows without historical full-model scores retain their natural weight.
    eligible = tr.dropna(subset=["selected", "score_pct", "score"]).copy()
    cases = make_cases(eligible)
    pairs = match_outcomes(cases)
    pairs.to_parquet(OUT/"pairs.parquet", index=False)
    pair_rows = pd.concat([pairs[["signal_date", side+"_instrument"]].rename(
        columns={side+"_instrument":"instrument"}) for side in ["rebound", "fall"]])
    ids = pd.MultiIndex.from_frame(tr[KEY])
    pair_ids = pd.MultiIndex.from_frame(pair_rows)
    assert pair_ids.is_unique and pair_ids.isin(ids).all()
    weights = tr[KEY+["selected", "maturity", "terminal_loss", "breach"]].copy()
    weights["hard"] = ids.isin(pair_ids)
    strata = ["signal_date", "selected"]
    counts = weights[weights.hard].groupby(strata, observed=True).size()
    # Require both targets to be observable for *additional* random weight. This makes
    # added sample mass match the paired arm under both heads; no class is requested.
    eligible = eligible.dropna(subset=["terminal_loss", "breach"])
    populations = {key: group.index.to_numpy() for key, group in eligible.groupby(strata, observed=True)}
    for seed in SEEDS:
        draws = []
        for (date, selected), count in counts.items():
            rng = np.random.default_rng([seed, int(date.strftime("%Y%m%d")), int(selected)])
            draws.extend(rng.choice(populations[date,selected], count, replace=False))
        name = f"random_{seed}"
        weights[name] = weights.index.isin(draws)
        pd.testing.assert_series_equal(weights[weights[name]].groupby(strata, observed=True).size(), counts)
    assert int(weights.hard.sum()) == len(pair_rows)
    assert weights.loc[weights[WEIGHTS].any(axis=1), ["terminal_loss", "breach"]].notna().all().all()
    weights.to_parquet(OUT/"extra_weight_membership.parquet", index=False)
    return weights


def test_data():
    panel = pd.read_parquet(PANEL, columns=TEST_KEY+["scope", "oversold", "selected", "ret10",
                                                  "hold_low10", "prior_low5"])
    frames = []
    for pool, archive in [("CSI300", NARROW), ("CSI800", WIDE)]:
        cases = panel[panel.pool.eq(pool) & panel.oversold.fillna(False)]
        features = pd.read_parquet(archive, columns=KEY+COLS, filters=[
            ("signal_date", "in", list(cases.signal_date.unique()))])
        attached = cases.merge(features, on=KEY, validate="1:1", how="left", indicator=True)
        assert attached._merge.eq("both").all()
        frames.append(attached.drop(columns="_merge"))
    df = pd.concat(frames, ignore_index=True).sort_values(TEST_KEY)
    df["terminal_loss"] = df.ret10.lt(0).astype("boolean").where(df.ret10.notna())
    df["breach"] = df.hold_low10.lt(df.prior_low5).astype("boolean").where(
        df.hold_low10.notna() & df.prior_low5.notna())
    assert not df.duplicated(TEST_KEY).any() and df.groupby("pool").signal_date.nunique().eq(139).all()
    return df


def predict_all(tr, weights, outer):
    records = []
    predictions = []
    coefficients = {}
    model_names = ["natural", *WEIGHTS]
    for q, current in outer.groupby(outer.signal_date.dt.to_period("Q")):
        cutoff = q.start_time
        mature = tr.maturity.lt(cutoff)
        assert tr.loc[mature, "signal_date"].max() < cutoff <= current.signal_date.min()
        book = {name: current[TEST_KEY+["scope", "selected"]].assign(model=name, quarter=str(q)).copy()
                for name in model_names}
        coefficients[str(q)] = {}
        for tag, target in HEADS.items():
            known = mature & tr[target].notna()
            subset = tr.loc[known]
            outcomes = subset[target].astype(int).to_numpy()
            assert np.unique(outcomes).size == 2 and subset.maturity.max() < cutoff
            transform = Transform().fit(subset[COLS])
            xs = transform.transform(subset[COLS])
            future = transform.transform(current[COLS])
            natural_rate = outcomes.mean()
            head_record = dict(columns=COLS, transform=transform.record(), models={})
            for name in model_names:
                sample_weight = np.ones(len(subset)) if name == "natural" else (
                    1. + weights.loc[known, name].to_numpy(float))
                clf = LogisticRegression(C=1., solver="lbfgs", max_iter=1000, tol=1e-8)
                clf.fit(xs, outcomes, sample_weight=sample_weight)
                prob = clf.predict_proba(future)[:,1]
                assert np.isfinite(prob).all() and np.all((prob >= 0) & (prob <= 1))
                record = dict(coef=clf.coef_[0].tolist(), intercept=float(clf.intercept_[0]))
                head_record["models"][name] = record
                np.testing.assert_allclose(prob, expit(future@record["coef"]+record["intercept"]), atol=1e-13)
                book[name][tag+"_prob"] = prob
                book[name][tag+"_prior"] = natural_rate
                extra = sample_weight > 1
                records.append(dict(quarter=str(q), cutoff_exclusive=cutoff, model=name, head=tag,
                    mature_oversold=int(mature.sum()), known=len(subset), unknown=int(mature.sum()-known.sum()),
                    positives=int(outcomes.sum()), negatives=int(len(subset)-outcomes.sum()), natural_rate=natural_rate,
                    training_dates=subset.signal_date.nunique(), instruments=subset.instrument.nunique(),
                    max_maturity=subset.maturity.max(), warmup_rows=int(subset.selected.isna().sum()),
                    doubled=int(extra.sum()), doubled_positive=int(outcomes[extra].sum()),
                    weighted_rate=np.average(outcomes,weights=sample_weight), iterations=int(clf.n_iter_[0])))
            coefficients[str(q)][tag] = head_record
        predictions.extend(book.values())
        print(f"{q} 训练自然超跌 {mature.sum()}，验证 {len(current)}", flush=True)
    folds = pd.DataFrame(records)
    scores = pd.concat(predictions,ignore_index=True)
    assert len(coefficients)==23 and len(records)==322
    assert scores.groupby("model").size().eq(len(outer)).all() and not scores.duplicated(TEST_KEY+["model"]).any()
    folds.to_csv(OUT/"folds.csv", index=False)
    (OUT/"models.json").write_text(json.dumps(coefficients, allow_nan=False)+"\n")
    scores.to_parquet(OUT/"scores.parquet", index=False)
    return scores


def metrics(record):
    keys = ["pool", "scope", "model", "head", "universe"]
    group = record.groupby(keys+["signal_date"], observed=True)
    record["rank"] = group.prob.rank(method="average")
    record["rank_sum"] = record["rank"] * record.outcome
    record["err"] = (record.prob-record.outcome)**2
    record["prior_err"] = (record.prior-record.outcome)**2
    daily = group.agg(n=("outcome","size"), positive=("outcome","sum"), rank_sum=("rank_sum","sum"),
                       brier=("err","mean"), prior_brier=("prior_err","mean")).reset_index()
    n_pos = daily.positive
    n_neg = daily.n - n_pos
    daily["auc"] = (daily.rank_sum-n_pos*(n_pos+1)/2) / (n_pos*n_neg).replace(0,np.nan)
    daily["prior_auc"] = np.where(daily.auc.notna(), .5, np.nan)
    daily = daily.drop(columns="rank_sum")
    rows = []
    for key, g in record.groupby(keys):
        days = daily.set_index(keys).loc[[key]]
        rows.append(dict(zip(keys,key))|dict(n=len(g),dates=g.signal_date.nunique(),
            positive=int(g.outcome.sum()),positive_rate=g.outcome.mean(),
            mean_predicted=g.prob.mean(), brier=g.err.mean(), prior_brier=g.prior_err.mean(),
            pooled_auc=roc_auc_score(g.outcome,g.prob), pooled_prior_auc=roc_auc_score(g.outcome,g.prior),
            days_with_auc=days.auc.notna().sum(), mean_daily_auc=days.auc.mean(),
            mean_daily_brier=days.brier.mean(), mean_daily_prior_brier=days.prior_brier.mean()))
    return pd.DataFrame(rows),daily


def evaluate(scores, outer):
    tested = scores.merge(outer[TEST_KEY+list(HEADS.values())], on=TEST_KEY, validate="m:1")
    summary = []
    daily = []
    for head, target in HEADS.items():
        valid = tested.dropna(subset=[target])
        records = valid[["pool", "scope", "model", "signal_date", "selected", target, head+"_prob", head+"_prior"]].rename(
            columns={target:"outcome", head+"_prob":"prob", head+"_prior":"prior"}).copy()
        records["outcome"] = records.outcome.astype(int)
        for universe, frame in [("all_oversold", records), ("original_D10_oversold", records[records.selected])]:
            s, d = metrics(frame.assign(head=head, universe=universe))
            summary.append(s)
            daily.append(d)
    pd.concat(summary, ignore_index=True).to_csv(OUT/"metrics.csv", index=False)
    pd.concat(daily, ignore_index=True).to_parquet(OUT/"metrics_daily.parquet", index=False)


def audit_persisted(tr, weights, outer):
    models = json.loads((OUT/"models.json").read_text())
    scores = pd.read_parquet(OUT/"scores.parquet").set_index(TEST_KEY+["model"]).sort_index()
    folds = pd.read_csv(OUT/"folds.csv", parse_dates=["max_maturity"]).set_index(["quarter","head","model"])
    checked = 0
    maximum = 0.
    checked_folds = 0
    for quarter, period_rows in outer.groupby(outer.signal_date.dt.to_period("Q")):
        cutoff = quarter.start_time
        for head, target in HEADS.items():
            # Derive the legal prefix by sorting maturity dates independently of the fit mask.
            dates = tr.dropna(subset=[target]).sort_values("maturity")
            prefix = dates.iloc[:dates.maturity.searchsorted(cutoff)]
            raw = period_rows[COLS].to_numpy(dtype=float)
            record = models[str(quarter)][head]
            assert record["columns"] == COLS
            t = record["transform"]
            restored = (np.where(np.isnan(raw),t["median"],raw)-t["mean"])/t["sd"]
            for model, coef in record["models"].items():
                f = folds.loc[str(quarter),head,model]
                assert (f.known, f.positives, f.max_maturity) == (
                    len(prefix), int(prefix[target].sum()), prefix.maturity.max())
                assert f.training_dates == prefix.signal_date.nunique() and f.max_maturity < cutoff
                doubled = 0 if model == "natural" else int(weights.loc[prefix.index, model].sum())
                assert f.doubled == doubled
                restored_probs = expit(restored@coef["coef"]+coef["intercept"])
                keys = pd.MultiIndex.from_frame(period_rows[TEST_KEY].assign(model=model))
                saved = scores.loc[keys,head+"_prob"].to_numpy()
                np.testing.assert_allclose(saved, restored_probs, atol=1e-13, rtol=0)
                maximum = max(maximum, np.abs(saved-restored_probs).max())
                checked += len(saved)
                checked_folds += 1
    assert checked == 2*len(scores) and checked_folds == 322
    return dict(persisted_probabilities_recomputed=checked, maximum_absolute_error=maximum,
                independent_maturity_prefix_checks=checked_folds)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert len(COLS)==78 and len(set(COLS))==78
    tr = training_data()
    weights = extra_weights(tr)
    outer = test_data()
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        scores = predict_all(tr, weights, outer)
    evaluate(scores, outer)
    audit = audit_persisted(tr, weights, outer)
    paths=[Path(__file__),WEEKLY,PANEL,NARROW,WIDE,DICTIONARY,EP39/"oversold.py",EP37/"model.py"]
    receipt=dict(n_scores=len(scores),quarters=23,models=7,heads=2,logistic_fits=322,
                 C=1.,independent_checks=audit,solver="lbfgs",tolerance=1e-8,natural_weight=1,additional_weight=1,seeds=SEEDS,
                 trigger_counts=outer.groupby("pool").size().to_dict(),
                 inputs={str(p):sha(p) for p in paths},
                 outputs={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.name!="receipt.json"})
    (OUT/"receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n")


if __name__ == "__main__":
    main()
