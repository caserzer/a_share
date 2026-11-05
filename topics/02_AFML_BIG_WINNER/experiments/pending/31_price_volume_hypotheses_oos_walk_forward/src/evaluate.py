"""Score only hash-sealed outer predictions; never feed metrics back to training."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import OUT, cache, config, sha, utc_now, write_json
from ep30_adapter import EP30Adapter
from hypothesis_tests import monthly_statistics, summarize
from multiple_testing import bh, infer_effect
from walk_forward import load_outcomes


def quarter_complete(quarter, horizon, days):
    q = pd.Period(quarter, "Q")
    if q.end_time.normalize() > days[-1]:
        return False
    last = days[days <= q.end_time][-1]
    if horizon == "6_calendar_months":
        return last+pd.DateOffset(months=6) <= days[-1]
    return days.get_loc(last)+int(horizon) < len(days)


def score_frame(predictions, outcomes, hypothesis, spec):
    f = predictions.merge(outcomes, on=["date", "security_id"], how="left", validate="one_to_one")
    f["y"] = f.value
    if spec["endpoint"] == "log_variance_mse":
        f["y"] = np.log(f.future_variance+1e-12)
        f["mature_at"] = f.rv_mature_at
    elif spec["endpoint"] == "downside_brier":
        f["y"] = f.value.lt(-0.1).astype(float).where(f.value.notna())
    return f


def slices(frame, spec, hypothesis, scheme):
    records = []
    frame = frame.copy()
    frame["year"] = frame.date.dt.year
    frame["market_state"] = np.where(frame.market_mom20.gt(0), "positive", "nonpositive")
    for domain in ["year", "board", "size_group", "liquidity_group", "market_state"]:
        for level, group in frame.groupby(domain, observed=True):
            r, _ = summarize(group, spec)
            records.append(dict(hypothesis=hypothesis, scheme=scheme, domain=domain, level=str(level), **r))
    for year in sorted(frame.year.unique()):
        r, _ = summarize(frame.loc[frame.year.ne(year)], spec)
        records.append(dict(hypothesis=hypothesis, scheme=scheme, domain="leave_one_year_out", level=str(year), **r))
    for domain, mask in [("exclude_provider_disagreement", ~frame.provider_disagreement),
                         ("exclude_recent_factor_change", ~frame.factor_step_200),
                         ("exclude_share_proxy_change", ~frame.share_proxy_step_20),
                         ("exclude_smallest_cap", frame.size_group.ne("small")),
                         ("exclude_one_price_bar", ~frame.one_price_bar)]:
        r, _ = summarize(frame.loc[mask], spec)
        records.append(dict(hypothesis=hypothesis, scheme=scheme, domain=domain, level="retained", **r))
    # Equal-security weighting is distinct from equal-time weighting.
    f = frame.loc[frame.y.notna()].copy()
    f["residual"] = f.y-f.baseline
    f["xy"] = f.partial_x*f.residual
    f["xx"] = f.partial_x**2
    stock = f.groupby("security_id")[["xy", "xx"]].mean()
    equal_stock = stock.xy.mean()/max(stock.xx.mean(), 1e-15) if spec["endpoint"] == "adjusted_return" else None
    records.append(dict(hypothesis=hypothesis, scheme=scheme, domain="equal_security_descriptive", level="all", estimate=equal_stock, rows=len(f)))
    return records


def main():
    metrics = OUT / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    scoring_started_at = utc_now()
    indexes = [OUT/f"manifests/{h}_folds.json" for h in config()["primary"] if h != "H09"]
    indexes += [OUT/"manifests/big_winner.json", OUT/"manifests/H02_turnover_sensitivity.json", OUT/"manifests/H12_independence.json", OUT/"manifests/auxiliary_baselines.json", OUT/"manifests/constant_baseline.json"]
    for p in indexes[:7]:
        if not json.loads(p.read_text()).get('exact_calendar_admission'):
            raise RuntimeError('exact calendar-history admission required before scoring')
    write_json(OUT/"audits/scoring_start.json", dict(started_at=scoring_started_at,
               prediction_indexes={str(p.relative_to(OUT)):sha(p) for p in indexes},
               all_prediction_families_frozen_before_scores=True))
    days = EP30Adapter().days
    fold_results, pooled, robust, placebo, maturity, secondary, doubles, sample_concurrency, calibration = [], [], [], [], [], [], [], [], []
    specs = config()["primary"]
    secondary_columns=["date", "security_id", "value", "mfe", "mae", "status", "entry_date", "exit_date", "entry_delay_sessions", "exit_delay_sessions"]
    shared_outcomes={}
    for h in [5,10,20,60,120,"6_calendar_months"]:
        cols=secondary_columns+["mature_at"]+(["future_variance","rv_mature_at"] if h==20 else [])
        shared_outcomes[h]=load_outcomes(h,cols)
    for hypothesis, spec in specs.items():
        if hypothesis == "H09":
            continue
        index = json.loads((OUT / f"manifests/{hypothesis}_folds.json").read_text())
        outcomes = shared_outcomes[spec["horizon"]]
        by_scheme = {"expanding": [], "rolling36": []}
        for receipt in index["folds"]:
            if sha(receipt["predictions_path"]) != receipt["predictions_sha256"] or sha(receipt["model_path"]) != receipt["model_sha256"]:
                raise ValueError("frozen model/predictions changed")
            p = pd.read_parquet(receipt["predictions_path"])
            f = score_frame(p, outcomes, hypothesis, spec)
            f["complete_quarter"] = quarter_complete(receipt["fold"], spec["horizon"], days)
            r, _ = summarize(f, spec)
            fold_results.append(dict(hypothesis=hypothesis, scheme=receipt["scheme"], fold=receipt["fold"], complete_quarter=bool(f.complete_quarter.iloc[0]),
                                     factor_coefficient=receipt["factor_coefficient"], **r))
            by_scheme[receipt["scheme"]].append(f)
            # Entry/exit concurrency uses actual observed endpoints, no stock-row independence claim.
            known = f.loc[f.y.notna() & f.entry_date.notna() & f.exit_date.notna()]
            events = pd.concat([pd.Series(1, index=known.entry_date), pd.Series(-1, index=known.exit_date)]).groupby(level=0).sum().sort_index().cumsum()
            sample_concurrency.append(dict(hypothesis=hypothesis, scheme=receipt["scheme"], fold=receipt["fold"], max_concurrency=int(events.max()) if len(events) else 0,
                                           unique_dates=int(f.date.nunique()), rows=len(f), mature=int(f.y.notna().sum())))
        del outcomes
        for scheme, frames in by_scheme.items():
            if not frames:
                continue
            allf = pd.concat(frames, ignore_index=True)
            if allf.duplicated(["date", "security_id"]).any():
                raise AssertionError("episode duplicated between outer folds")
            f = allf.loc[allf.complete_quarter].copy()
            r, months = summarize(f, spec)
            r.update(hypothesis=hypothesis, scheme=scheme, endpoint=spec["endpoint"], direction=spec["direction"] if spec["endpoint"] == "adjusted_return" else 1,
                     complete_quarters=int(f.fold.nunique()), independent_time_blocks_approx=r["months"]/6)
            pooled.append(r)
            months.to_csv(metrics / f"{hypothesis}_{scheme}_monthly.csv", index=False)
            robust.extend(slices(f, spec, hypothesis, scheme))
            if hypothesis=='H10':
                known=f.loc[f.y.notna()].copy()
                for model in ['baseline','augmented']:
                    known['probability']=known[model].clip(0,1)
                    known['bin']=pd.cut(known.probability,[-1e-12,.05,.1,.2,.4,.6,.8,1.0000001],include_lowest=True)
                    for interval,g in known.groupby('bin',observed=True):
                        calibration.append(dict(hypothesis=hypothesis,scheme=scheme,model=model,probability_bin=str(interval),rows=len(g),dates=int(g.date.nunique()),
                                                mean_probability=float(g.probability.mean()),observed_rate=float(g.y.mean()),description='row-weighted descriptive calibration; clustered uncertainty not independent trials'))
            for name in ["shuffle_gain", "permlabel_gain", "lag_gain"]:
                pm = months[["month", name]].rename(columns={name: "loss_gain"})
                pstats = infer_effect(pm, direction=1, ratio=False)
                placebo.append(dict(hypothesis=hypothesis, scheme=scheme, control=name, **pstats))
            if hypothesis == "H03":
                double = f.loc[f.y.notna()].copy()
                double["residual"] = double.y-double.baseline
                g = double.groupby([double.date.dt.to_period("M"), "momentum_group", "turnover_group"]).residual.agg(["mean", "size"]).reset_index()
                g["date"] = g.date.astype(str)
                g["scheme"] = scheme
                doubles.extend(g.to_dict("records"))
            # Labels for each horizon have their own maturation denominator.
            for h in [5, 10, 20, 60, 120, "6_calendar_months"]:
                other = shared_outcomes[h][secondary_columns]
                joined = allf[["date", "security_id", "fold", "factor_raw", "sort_group"]].merge(other, on=["date", "security_id"], how="left", validate="one_to_one")
                joined["status"] = joined.status.fillna("UNKNOWN")
                quarter_status={q:quarter_complete(q,h,days) for q in joined.fold.unique()}
                joined["complete_quarter"] = joined.fold.map(quarter_status)
                for (fold, status), g in joined.groupby(["fold", "status"]):
                    maturity.append(dict(hypothesis=hypothesis, scheme=scheme, horizon=str(h), fold=fold, status=status, rows=len(g), complete_quarter=bool(g.complete_quarter.iloc[0]),
                                         delayed_entry=int(g.entry_delay_sessions.gt(0).sum()), delayed_exit=int(g.exit_delay_sessions.gt(0).sum()), complete_path=int(g.mfe.notna().sum())))
                observable = joined.loc[joined.value.notna() & joined.complete_quarter]
                for group, g in observable.groupby("sort_group"):
                    perdate = g.groupby("date")[["value", "mfe", "mae"]].mean()
                    secondary.append(dict(hypothesis=hypothesis, scheme=scheme, horizon=str(h), factor_quantile=int(group), rows=len(g), dates=int(g.date.nunique()),
                                          return_mean=float(perdate.value.mean()), mfe=float(perdate.mfe.mean()) if perdate.mfe.notna().any() else None,
                                          mae=float(perdate.mae.mean()) if perdate.mae.notna().any() else None,
                                          six_month_loss_below_minus20=float(g.value.lt(-0.2).mean()) if h == "6_calendar_months" else None))
                del other, joined
            print("P2 scored", hypothesis, scheme, r["rows"], "rows", r["months"], "months", flush=True)
            del allf, f
    pooled = pd.DataFrame(pooled)
    pooled["q_bh"] = np.nan
    for scheme in ["expanding", "rolling36"]:
        mask = pooled.scheme.eq(scheme)
        pooled.loc[mask, "q_bh"] = bh(pooled.loc[mask, "p_one_sided"])
    pooled.to_csv(metrics / "pooled_oos_metrics.csv", index=False)
    pd.DataFrame(fold_results).to_csv(metrics / "outer_fold_metrics.csv", index=False)
    pd.DataFrame(robust).to_csv(metrics / "robustness.csv", index=False)
    pd.DataFrame(placebo).to_csv(metrics / "placebo.csv", index=False)
    pd.DataFrame(maturity).to_csv(metrics / "maturity_coverage.csv", index=False)
    pd.DataFrame(secondary).to_csv(metrics / "secondary_endpoints.csv", index=False)
    pd.DataFrame(doubles).to_csv(metrics / "H03_double_sort.csv", index=False)
    pd.DataFrame(sample_concurrency).to_csv(metrics / "label_concurrency.csv", index=False)
    pd.DataFrame(calibration).to_csv(metrics / "H10_calibration.csv",index=False)
    write_json(OUT / "audits/scoring_receipt.json", dict(scoring_started_at=scoring_started_at, scoring_finished_at=utc_now(), frozen_predictions_verified=True,
               eligible_hypotheses=7, h09="BLOCKED_DATA", actual_primary_BH_family=7,
               complete_quarters_only_in_primary=True, partial_quarters_separately_disclosed=True,
               no_actual_execution_certified=True))


if __name__ == "__main__":
    main()
