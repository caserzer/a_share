"""Independently reconcile EP39's fitted scores, selected names, ledgers, and readouts."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIT = RES / "training_fit"
WEEK = RES / "training_weekly"
ACC = RES / "training_accounts"
REVIEW = RES / "training_review"
LOCAL = RES / "training_local"
EP37 = next(ROOT.parent.glob("37_*")) / "extensions/original78_rankic_20261118"
EP38 = next(ROOT.parent.glob("38_*")) / "three_track/results"
MARKET = Path(os.environ.get("EP39_MARKET", Path.home() / ".cache/a_share/ep38_three_track/market"))
POOL = ["CSI300", "CSI800"]
TASKS = ["breakout", "oversold"]
COST = {"zero": 0, "base": 1, "double": 2}
SEEDS = [39, 139, 239, 339, 439]
KEY = ["signal_date", "instrument"]
OUTER = ["pool", *KEY]
DAY = ["pool", "signal_date"]
BOOK = ["pool", "scope", "series", "segment", "model", "cost"]
MODELS = ["full"] + [task+"_"+kind for task in TASKS for kind in ["curated", *[f"random_{s}" for s in SEEDS]]]


def close(a, b):
    np.testing.assert_allclose(a, b, atol=1e-9, rtol=0, equal_nan=True)


def indexed(frame, fields):
    return frame.set_index(fields, verify_integrity=True).sort_index()


def same(left, right, key, fields):
    a, b = indexed(left, key), indexed(right, key)
    pd.testing.assert_index_equal(a.index, b.index, exact=False)
    for field in fields:
        close(a[field], b[field])


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_fits(scores):
    cols = ["target_rank", "target_z", "h10", "maturity", "selected", "score", "score_eligible", *TASKS]
    weekly = pd.read_parquet(WEEK / "panel.parquet", columns=KEY+cols)
    assert not weekly.duplicated(KEY).any() and weekly.score_eligible.all()
    mature = weekly.dropna(subset=["target_rank", "maturity"])
    assert (mature.signal_date < mature.maturity).all()
    h10 = weekly[weekly.target_z.notna()].groupby("signal_date").h10
    close(weekly.loc[weekly.target_z.notna(), "target_rank"], h10.rank()/(h10.transform("count")+1)-.5)
    assert weekly.target_z.isna().equals(weekly.target_rank.isna())
    outer_folds = pd.read_csv(FIT / "folds.csv")
    qtr = scores.index.get_level_values("signal_date").to_period("Q")
    quarters = sorted(set(qtr.astype(str)))
    assert len(quarters) == 23 and set(outer_folds.quarter) == set(quarters)
    assert not outer_folds.duplicated(["model", "quarter"]).any() and outer_folds.available.all()
    selected = pd.read_parquet(FIT / "training_membership.parquet")
    assert not selected.duplicated(["model", *KEY]).any()
    assert set(selected.model) == set(MODELS)-{"full"}
    merged = selected.merge(weekly, on=KEY, how="left", validate="m:1", suffixes=("", "_source"))
    assert merged.score.notna().all() and merged.target_rank.notna().all()
    for field in ["maturity", "target_rank", "selected"]:
        assert merged[field].eq(merged[field+"_source"]).all()
    for task in TASKS:
        rows = merged[merged.model.str.startswith(task+"_")]
        assert rows[task].fillna(False).all()
        strata = rows.groupby(["signal_date", "selected", "model"]).size().unstack()
        assert strata.notna().all().all() and strata.nunique(axis=1).eq(1).all()
        pairs = pd.read_parquet(FIT / (task+"_weekly_pairs.parquet"))
        names = ["continued_id", "failed_id"] if task == "breakout" else ["rebound_instrument", "fall_instrument"]
        sides = [pd.DataFrame({"signal_date":pairs.signal_date, "instrument":pairs[name].str.split("_").str[-1]}) for name in names]
        ids = indexed(pd.concat(sides), KEY).index
        assert ids.equals(indexed(rows[rows.model.eq(task+"_curated")], KEY).index)
    inner_folds = pd.read_csv(WEEK / "oof_folds.csv")
    scored_dates = weekly.signal_date.dt.to_period("Q").astype(str)
    assert set(inner_folds.quarter) == set(scored_dates)
    for r in inner_folds.itertuples():
        past = mature[mature.maturity < pd.Period(r.quarter, freq="Q").start_time]
        now = weekly[scored_dates == r.quarter]
        assert len(past) == r.train_rows and past.signal_date.nunique() == r.train_dates
        assert len(now) == r.eligible_rows and now.score.notna().eq(r.oof_available).all()
        if r.oof_available:
            assert past.maturity.max() == pd.Timestamp(r.max_maturity) < now.signal_date.min()
    for quarter, fold in outer_folds.groupby("quarter"):
        cut = pd.Period(quarter, freq="Q").start_time
        assert set(fold.model) == set(MODELS)
        assert pd.to_datetime(fold.cutoff_exclusive).eq(cut).all()
        data = merged[merged.maturity < cut]
        for r in fold.itertuples():
            rows = mature[mature.maturity < cut] if r.model == "full" else data[data.model.eq(r.model)]
            assert (len(rows), rows.signal_date.nunique(), rows.instrument.nunique()) == (r.train_rows, r.train_dates, r.train_names)
            assert rows.signal_date.min() == pd.Timestamp(r.train_start)
            assert rows.signal_date.max() == pd.Timestamp(r.train_end) < cut
            assert rows.maturity.max() == pd.Timestamp(r.train_max_maturity) < cut
            assert rows.score.notna().sum() == r.oof_rows
    models = json.loads((FIT / "models.json").read_text())
    assert set(models) == set(quarters)
    features = pd.read_csv(EP37 / "outputs/original_78_features.csv").feature.tolist()
    assert len(set(features)) == 78
    err = 0.
    for pool, arch in zip(POOL, [EP37/"local_cache/h10_features.parquet", MARKET/"wide_features.parquet"]):
        here = scores.loc[pool]
        features_by_key = indexed(pd.read_parquet(arch, columns=KEY+features, filters=[
            ("signal_date", "in", here.index.get_level_values(0).unique().tolist())]), KEY).reindex(here.index)
        for q, part in here.groupby(here.index.get_level_values(0).to_period("Q")):
            raw = features_by_key.loc[part.index].to_numpy(float)
            assert set(models[str(q)]) == set(MODELS)
            for name, model in models[str(q)].items():
                assert model["columns"] == features
                transformed = (np.where(np.isnan(raw), model["median"], raw)-model["mean"])/model["sd"]
                pred = transformed @ model["coef"] + model["intercept"]
                err = max(err, np.max(np.abs(pred-part[name].to_numpy())))
                close(part[name], pred)
    return dict(weekly_rows=len(weekly), weekly_oof_quarters=len(inner_folds), outer_quarters=len(quarters),
                arm_folds=len(outer_folds), curated_and_random_membership_rows=len(merged), prediction_recompute_max_abs=float(err))


def verify_decisions(scores, panel, expected):
    swaps = pd.read_parquet(REVIEW / "changed_seats.parquet")
    seat_summary = pd.read_csv(REVIEW / "seat_summary.csv")
    matched = pd.read_parquet(REVIEW / "matched_case_accuracy.parquet")
    decisions = pd.read_csv(REVIEW / "trigger_decisions.csv")
    group = ["pool", "scope", "model"]
    rankic = pd.read_parquet(REVIEW/"trigger_rankic.parquet")
    independently_summed = []
    for name in MODELS[1:]:
        s = swaps[swaps.model.eq(name)]
        picked, full = expected[name], expected.full
        for flag, field in [(picked & ~full, "instrument_new"), (full & ~picked, "instrument_old")]:
            check = s[DAY+[field]].rename(columns={field:"instrument"})
            assert indexed(check, OUTER).index.equals(scores.index[flag])
        close(s.quote_diff, s.ret10_new-s.ret10_old)
        assert (s.fillable == (s.gates_new & s.gates_old)).all()
        close(s.equal_cash_netdiff, ((s.ret10_new-s.ret10_old)*.998/1.001).where(s.fillable))
    seat_calculated = swaps.groupby(group).agg(paired_seats=("slot","count"), both_fillable=("fillable","sum"),
        both_marked=("quote_diff","count"), equal_cash_netdiff=("equal_cash_netdiff","mean"), quote_diff=("quote_diff","mean")).reset_index()
    same(seat_calculated, seat_summary, group, seat_calculated.columns.difference(group))
    for task, good, bad in [("breakout","延续","失败"), ("oversold","止跌反弹","持续下跌")]:
        cases = pd.read_csv(RES / (task+"_cases.csv.gz"), usecols=OUTER+["label"], parse_dates=["signal_date"])
        labels = indexed(cases, OUTER).label
        trigger = panel[panel[task].fillna(False)].join(labels, how="left")
        assert trigger.label.notna().all()
        pairs = pd.read_csv(RES / (task+"_pairs.csv.gz"), parse_dates=["signal_date"])
        fields = ["continued_id", "failed_id"] if task=="breakout" else ["rebound_instrument", "fall_instrument"]
        endpoints = [pd.MultiIndex.from_arrays([pairs.pool, pairs.signal_date, pairs[k].str.split("_").str[-1]], names=OUTER) for k in fields]
        for model in ["full", *[n for n in MODELS if n.startswith(task+"_")]]:
            delta = scores[model].reindex(endpoints[0]).to_numpy() - scores[model].reindex(endpoints[1]).to_numpy()
            assert np.isfinite(delta).all()
            result = pairs.assign(value=(np.sign(delta)+1)/2).groupby(["pool","scope","signal_date","selected"]).value.agg(["sum","size"]).reset_index()
            same(result, matched[(matched.model==model)&(matched.task==task)], ["pool","scope","signal_date","selected"], ["sum","size"])
            ranks = trigger[["ret10"]].assign(score=scores.loc[trigger.index,model]).copy()
            ranks.loc[ranks.ret10.isna(),"score"] = np.nan
            ranks = ranks.groupby(level=DAY).rank()
            centered = ranks - ranks.groupby(level=DAY).transform("mean")
            scale = centered.pow(2).groupby(level=DAY).sum().prod(axis=1).pow(.5)
            covariance = (centered.score*centered.ret10).groupby(level=DAY).sum()
            corr = (covariance/scale).rename("trigger_ic").reset_index()
            same(corr,rankic[(rankic.model==model)&(rankic.task==task)],DAY,["trigger_ic"])
            pick = expected[model].loc[trigger.index]
            for state, mask in [("all",pick|~pick), ("picked",pick), ("retained",pick & trigger.selected),
                                ("added",pick & ~trigger.selected), ("dropped",~pick & trigger.selected)]:
                part = trigger[mask].reset_index()
                counts = part.assign(good=part.label.eq(good),bad=part.label.eq(bad)).groupby(["pool","scope"]).agg(
                    stocks=("instrument","size"), dates=("signal_date","nunique"), good=("good","sum"),
                    bad=("bad","sum"), known_returns=("ret10","count"), mean_ret10=("ret10","mean")).reset_index()
                independently_summed.append(counts.assign(model=model,task=task,state=state))
    same(pd.concat(independently_summed), decisions, group+["task","state"], ["stocks","dates","good","bad","known_returns","mean_ret10"])
    return dict(swapped_seats=len(swaps), seat_summaries=len(seat_summary), matched_outcome_rows=len(matched), decision_rows=len(decisions),trigger_rankic_rows=len(rankic))


def verify_scores():
    panel = indexed(pd.read_parquet(RES / "panel.parquet", columns=OUTER+["score","scope","selected","ret10",*TASKS]), OUTER)
    long = pd.read_parquet(FIT / "scores.parquet")
    scores = long.pivot(index=OUTER, columns="model", values="score").sort_index()
    assert len(scores) * len(MODELS) == len(long) and np.isfinite(scores.to_numpy()).all()
    assert set(scores.columns) == set(MODELS) and scores.index.equals(panel.index)
    assert set(scores.index.get_level_values("pool")) == set(POOL)
    bydate = scores.groupby(level=DAY)
    assert len(bydate)==278
    archived_err = (panel.score-scores.full).abs().max()
    close(panel.score, scores.full)
    rank = bydate.rank(method="first", ascending=True)
    size = bydate.full.transform("size")
    expected = rank.gt(size-size//10, axis=0)
    assert expected.full.equals(panel.selected)
    targets = pd.read_parquet(ACC / "targets.parquet")
    for model, part in targets.groupby("model"):
        part = indexed(part, OUTER)
        flags = expected[model]
        assert part.index.equals(scores.index[flags])
        close(part.score, scores[model][flags])
        close(part.weight, 1/(size[flags]//10))
    assert set(targets.model) == set(MODELS)
    return (dict(rows=len(long), panel_rows=len(panel), dates_per_pool=139, models=len(MODELS), target_rows=len(targets),
                 frozen_full_score_max_abs=float(archived_err)), verify_fits(scores),verify_decisions(scores,panel,expected))


def verify_accounts():
    w = pd.read_parquet(ACC/"windows.parquet")
    d = pd.read_parquet(ACC/"daily.parquet")
    orders = pd.read_parquet(ACC/"orders.parquet")
    assert np.isfinite(w[["net","gross","fee","turnover"]]).all().all()
    assert set(w.cost) == set(COST) and set(w.series) == {"common","native"}
    assert not w.duplicated(BOOK+["signal_date"]).any()
    assert not orders.duplicated(BOOK+["idx","instrument"]).any()
    close(orders.fee, orders.cost.map(COST)*np.where(orders.net_amount>0, .001*orders.net_amount, -.002*orders.net_amount))
    order_days = orders.assign(buy=orders.net_amount.clip(lower=0),sell=-orders.net_amount.clip(upper=0)).groupby(BOOK+["idx"]).agg(
        buy=("buy","sum"),sell=("sell","sum"),fees=("fee","sum"),opening=("pretrade_nav","first"),nav_count=("pretrade_nav","nunique"))
    assert order_days.nav_count.eq(1).all()
    detail = indexed(d, BOOK+["idx"])
    assert order_days.index.isin(detail.index).all()
    aligned = order_days.reindex(detail.index)
    for field in ["buy","sell","fees"]:
        close(detail[field], aligned[field].fillna(0))
    close(detail.cash, 1+(detail.sell-detail.buy-detail.fees).groupby(level=BOOK).cumsum())
    detail["opening"] = aligned.opening
    common = w[w.series=="common"]
    for (pool,scope), chunk in common.groupby(["pool","scope"]):
        reference = chunk[chunk.model.eq("full") & chunk.cost.eq("base")].sort_values("entry_idx")
        for _,candidate in chunk.groupby(["cost","model"]):
            pd.testing.assert_frame_equal(reference[["segment","entry_idx","signal_date","exit_date"]].reset_index(drop=True),
                candidate.sort_values("entry_idx")[["segment","entry_idx","signal_date","exit_date"]].reset_index(drop=True))
        assert not reference.signal_date.duplicated().any() and len(chunk)==len(reference)*len(MODELS)*len(COST)
        expected_counts = [39] if scope=="later" else ([100] if pool=="CSI300" else [35,22,41])
        assert reference.groupby("segment").size().to_list()==expected_counts
    gaps = pd.read_csv(ACC/"gaps.csv", parse_dates=["date"])
    dates = set(gaps[gaps.series=="common"].date.dt.strftime("%Y-%m-%d"))
    assert dates=={"2022-06-30","2023-06-16"}
    summaries = indexed(pd.read_csv(ACC/"account_summary.csv"), BOOK)
    assert len(summaries)==w.groupby(BOOK).ngroups
    for key, wins in w.groupby(BOOK):
        trades = detail.loc[key]
        wins = wins.sort_values("entry_idx")
        ix = wins.entry_idx.to_numpy()
        assert (np.diff(ix)==10).all() and trades.index.equals(pd.Index(range(ix[0],ix[-1]+11)))
        assert np.array_equal(trades.loc[ix,"date"].to_numpy(),wins.entry_date.to_numpy())
        assert np.array_equal(trades.loc[ix+10,"date"].to_numpy(),wins.exit_date.to_numpy())
        opening = trades.loc[ix,"opening"].to_numpy()
        endpoint = np.r_[opening[1:],trades.nav.iloc[-1]]
        close(opening[0],1.)
        close(wins.net,endpoint/opening-1)
        close(wins.gross,wins.net+wins.fee)
        fee = trades.fees.to_numpy()
        flows = (trades.buy+trades.sell).to_numpy()
        for series, published in [(fee,wins.fee), (flows,wins.turnover)]:
            by_window = series[:-1].reshape(-1,10).sum(axis=1)
            by_window[-1] += series[-1]
            close(by_window/opening,published)
        close(np.prod(1+wins.net),trades.nav.iloc[-1])
        summary = summaries.loc[key]
        close([summary.n,summary.net_bp,summary.fee_bp,summary.nav],
              [len(wins),1e4*wins.net.mean(),1e4*wins.fee.mean(),trades.nav.iloc[-1]])
    wide = w.pool.eq("CSI800") & w.cost.eq("base")
    fields = ["outside300_weight","outside300_net","outside300_turnover"]
    assert w.loc[wide,fields].notna().all().all() and w.loc[~wide,fields].isna().all().all()
    assert w.loc[wide,"outside300_weight"].between(-1e-10,1+1e-10).all()
    assert (w.loc[wide,"outside300_turnover"]<=w.loc[wide,"turnover"]+1e-10).all()
    for pool, filename, model in [("CSI300","daily.parquet","original"),("CSI800","wide_daily.parquet","transfer")]:
        baseline = pd.read_parquet(EP38/filename,filters=[("model","=",model)])
        here = d[(d.pool==pool)&(d.series=="native")&(d.model=="full")]
        cols = ["nav","fees","buy","sell","cash"]
        same(here,baseline[baseline.scope.isin(["primary","later"])],["scope","cost","date"],cols)
        if pool == "CSI800":
            restart = d[(d.pool==pool)&(d.series=="common")&(d.model=="full")&(d.scope=="primary")&(d.segment==3)]
            same(restart,baseline[baseline.scope.eq("primary_restart")],["cost","date"],cols)
    base = pd.read_csv(EP38/"wide_coverage.csv",parse_dates=["signal_date"]).query("model=='transfer'").rename(
        columns={"outside300_contribution":"outside300_net","outside300_traded":"outside300_turnover"})
    same(w[wide & w.series.eq("native") & w.model.eq("full")],base[base.scope.isin(["primary","later"])],["scope","signal_date"],fields)
    return common,d[d.series.eq("common") & d.cost.eq("base")],dict(book_segments=len(summaries),H10_windows=len(w),
        daily_nav_rows=len(d),orders=len(orders),wide_base_attribution_rows=int(wide.sum()),wide_primary_common_segments=[35,22,41],
        gap_dates=sorted(dates),full_ep38_daily_reconciled=True)


def reference_models(task, ref):
    return [f"{task}_random_{s}" for s in SEEDS] if ref=="random_mean" else [ref]


def check_ci(group):
    rng = np.random.default_rng(3901)
    sums = np.zeros(10000)
    for _, part in group.groupby("segment"):
        values = part.sort_values("signal_date").net_bp.to_numpy()
        n=len(values)
        step=min(3,n)
        blocks=rng.integers(n,size=(10000,(n+step-1)//step))
        for t in range(n):
            sums+=values[(blocks[:,t//step]+t%step)%n]
    return np.quantile(sums/len(group), [0.025,0.975])


def verify_paired(w, daily):
    p = pd.read_parquet(REVIEW/"paired_windows.parquet")
    summary = pd.read_csv(REVIEW/"paired_summary.csv", dtype={"segment":str})
    by = ["pool","scope","cost","task","reference"]
    cols = ["net","fee","gross","turnover"]
    expected = []
    for (pool,scope,cost), subset in w.groupby(["pool","scope","cost"]):
        tab = subset.set_index(["segment","signal_date","model"])[cols].unstack("model").swaplevel(axis=1)
        for task in TASKS:
            for ref in ["full","random_mean",*reference_models(task,"random_mean")]:
                names = reference_models(task,ref)
                diffs = tab[task+"_curated"] - sum(tab[name] for name in names)/len(names)
                expected.append(diffs.assign(pool=pool,scope=scope,cost=cost,task=task,reference=ref).reset_index())
    rebuilt = pd.concat(expected,ignore_index=True)
    for qty in ["net","gross","fee"]:
        rebuilt[qty+"_bp"] = rebuilt[qty]*1e4
    same(rebuilt,p,by+["segment","signal_date"],["net_bp","fee_bp","gross_bp","turnover"])
    summary_check = []
    ci_checked = 0
    for key, differences in rebuilt.groupby(by):
        for seg, g in [("all",differences), *[(str(i),h) for i,h in differences.groupby("segment")]]:
            summary_check.append(dict(zip(by,key))|dict(segment=seg,n=len(g),net_bp=g.net_bp.mean(),gross_bp=g.gross_bp.mean(),
                                 fee_bp=g.fee_bp.mean(),wins=g.net_bp.gt(0).sum(),turnover=g.turnover.mean()))
            if key[2]=="base" and key[4] in {"full","random_mean"} and seg=="all":
                obs=indexed(summary, by+["segment"]).loc[(*key,seg)]
                close(check_ci(g),[obs.low,obs.high])
                ci_checked+=1
    same(pd.DataFrame(summary_check),summary,by+["segment"],["n","net_bp","gross_bp","fee_bp","wins","turnover"])
    months = pd.read_csv(REVIEW/"paired_months.csv")
    daily = daily.copy()
    daily["month"] = daily.date.dt.strftime("%Y-%m")
    month_keys=["pool","scope","segment","month"]
    ends = daily.sort_values("date").groupby(month_keys+["model"]).nav.last().unstack()
    net = ends/ends.groupby(level=["pool","scope","segment"]).shift().fillna(1.)-1
    checks = []
    for task in TASKS:
        checks.append(pd.DataFrame(dict(vs_full_bp=1e4*(net[task+"_curated"]-net.full),
                       vs_random_bp=1e4*(net[task+"_curated"]-net[reference_models(task,"random_mean")].mean(axis=1)))).reset_index().assign(task=task))
    same(pd.concat(checks),months,month_keys+["task"],["vs_full_bp","vs_random_bp"])
    return dict(paired_windows=len(p),paired_summary_rows=len(summary),paired_months=len(months),principal_95pct_intervals_recomputed=ci_checked)


def main():
    scores, fits, decisions = verify_scores()
    windows, daily, accounts = verify_accounts()
    comparisons = verify_paired(windows,daily)
    digest_files = sorted({*list((ROOT/"training").glob("*.py")),ROOT/"training/PROTOCOL.md",
        *[p for folder in [FIT,WEEK,ACC,REVIEW,LOCAL] for p in folder.rglob("*")
          if p.is_file() and p.name!="verification.json" and p.suffix in {".parquet",".csv",".json",".gz"}]})
    receipt = dict(status="PASS", scores=scores, training=fits, accounts=accounts, decisions=decisions,
                   paired_comparisons=comparisons,sha256={str(p.relative_to(ROOT)):sha(p) for p in digest_files})
    assert receipt["sha256"]["results/training_fit/scores.parquet"] == json.loads((ACC/"parity.json").read_text())["scores_sha256"]
    out = REVIEW/"verification.json"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt,indent=2)+"\n")
    tmp.replace(out)
    print(json.dumps({k:v for k,v in receipt.items() if k!="sha256"},indent=2))


if __name__=="__main__":
    main()
