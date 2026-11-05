"""P3: fixed breakout-cohort incremental diagnostics; no executable-P&L claim."""
from __future__ import annotations

import json
import pickle

import numpy as np
import pandas as pd

from baselines import CONTROLS, HypothesisTransform, Ridge
from common import OUT, cache, config, sha, utc_now, write_json
from evaluate import quarter_complete
from ep30_adapter import EP30Adapter
from walk_forward import cohort, inner_splits, load_features, load_outcomes, target_frame, training_mask


def main():
    all_features = load_features()
    features = cohort(all_features, "H11")
    del all_features
    frame = target_frame(features, load_outcomes(20), "H11", "adjusted_return")
    specs = config()["primary"]
    factors = {h: s["feature"] for h, s in specs.items() if h != "H09"}
    root = cache() / "big_winner"
    root.mkdir(parents=True, exist_ok=True)
    timeline = json.loads((OUT / "manifests/H11_folds.json").read_text())["folds"]
    receipts = []
    for fold in timeline:
        cutoff, scheme = pd.Timestamp(fold["fit_cutoff"]), fold["scheme"]
        train = frame.loc[training_mask(frame, cutoff, scheme)]
        test = features.loc[features.date.dt.to_period("Q").astype(str).eq(fold["fold"])]
        gains = {h: [] for h in factors}
        # Each factor's inclusion is based exclusively on the existing nested inner splits.
        for start, itrain, val in inner_splits(frame, cutoff, scheme, 20):
            transform = HypothesisTransform().fit(itrain)
            a, v = transform.apply(itrain, "H11"), transform.apply(val, "H11")
            base = Ridge().fit(a[CONTROLS], a.y, a.date, fold["alpha"])
            baseline_loss = (v.y-base.predict(v[CONTROLS]))**2
            for h, factor in factors.items():
                model = Ridge().fit(a[CONTROLS+[factor]], a.y, a.date, fold["alpha"])
                loss = (v.y-model.predict(v[CONTROLS+[factor]]))**2
                gain = pd.DataFrame(dict(date=v.date, gain=baseline_loss-loss)).groupby("date").gain.mean().mean()
                gains[h].append(float(gain))
        selected = [h for h, values in gains.items() if len(values) == 2 and np.mean(values) > 0]
        transform = HypothesisTransform().fit(train)
        a, v = transform.apply(train, "H11"), transform.apply(test, "H11")
        baseline = Ridge().fit(a[CONTROLS], a.y, a.date, fold["alpha"])
        base_train = baseline.predict(a[CONTROLS])
        candidate_threshold = float(np.quantile(base_train, 0.9))
        predictions = v[["date", "security_id", "board"]].copy()
        predictions["baseline_prediction"] = baseline.predict(v[CONTROLS])
        predictions["baseline_candidate"] = predictions.baseline_prediction.ge(candidate_threshold)
        models, thresholds = {}, {}
        for name, included in [(h, [factor]) for h, factor in factors.items()] + [("combined", [factors[h] for h in selected])]:
            model = Ridge().fit(a[CONTROLS+included], a.y, a.date, fold["alpha"])
            threshold = float(np.quantile(model.predict(a[CONTROLS+included]), 0.2))
            predictions[name+"_prediction"] = model.predict(v[CONTROLS+included])
            predictions[name+"_retain"] = predictions[name+"_prediction"].ge(threshold)
            models[name], thresholds[name] = model, threshold
        predictions["scheme"], predictions["fold"] = scheme, fold["fold"]
        name = scheme+"_"+fold["fold"]
        predpath, modelpath = root/(name+".parquet"), root/(name+".pkl")
        if predpath.exists():
            raise RuntimeError("immutable Big Winner predictions already exist")
        predictions.to_parquet(predpath, index=False)
        modelpath.write_bytes(pickle.dumps(dict(transform=transform, baseline=baseline, models=models, thresholds=thresholds, candidate_threshold=candidate_threshold), protocol=5))
        receipts.append(dict(fold=fold["fold"], scheme=scheme, cutoff=str(cutoff), max_mature_at=str(train.mature_at.max()),
                             inner_gains=gains, selected=selected, prediction_path=str(predpath), predictions_sha256=sha(predpath),
                             model_path=str(modelpath), model_sha256=sha(modelpath), frozen_at=utc_now(), rows=len(predictions)))
        print("P3 frozen", name, "selected", selected, flush=True)
    write_json(OUT / "manifests/big_winner.json", dict(folds=receipts, frozen_at=utc_now(), original_EP20_EP28_comparison="BLOCKED_DIFFERENT_COHORT",
               cohort="new_EP31_price_breakout_episodes_train_top_decile_baseline", hypothetical_execution_only=True))


def evaluate():
    root = cache() / "big_winner"
    receipt = json.loads((OUT / "manifests/big_winner.json").read_text())
    pieces = []
    for fold in receipt["folds"]:
        if sha(fold["prediction_path"]) != fold["predictions_sha256"]:
            raise ValueError("Big Winner prediction changed")
        pieces.append(pd.read_parquet(fold["prediction_path"]))
    f = pd.concat(pieces, ignore_index=True)
    for h in [10, 20, 60, 120]:
        y = load_outcomes(h, ["date", "security_id", "value", "status"])
        f = f.merge(y.rename(columns={"value": f"r{h}", "status": f"status{h}"}), on=["date", "security_id"], how="left", validate="many_to_one")
    days = EP30Adapter().days
    f["joint_mature"] = f[["r10", "r20", "r60", "r120"]].notna().all(axis=1)
    f["complete_quarter"] = f.fold.map(lambda q: quarter_complete(q, 120, days))
    results, costs, coverage = [], [], []
    variants = ["baseline", "H01", "H02", "H03", "H07", "H10", "H11", "H12", "combined"]
    for scheme, schemef in f.groupby("scheme"):
        for fold, g in schemef.groupby("fold"):
            coverage.append(dict(scheme=scheme, fold=fold, total=len(g), baseline_candidates=int(g.baseline_candidate.sum()),
                                 joint_mature=int(g.joint_mature.sum()), complete_quarter=bool(g.complete_quarter.iloc[0])))
        base = schemef.loc[schemef.baseline_candidate & schemef.joint_mature & schemef.complete_quarter].copy()
        total_winners = int(base.r120.gt(0.5).sum())
        for variant in variants:
            retain = np.ones(len(base), bool) if variant == "baseline" else base[variant+"_retain"].to_numpy(bool)
            kept, killed = base.loc[retain], base.loc[~retain]
            winners = int(kept.r120.gt(0.5).sum())
            failures = int(kept.r10.lt(-0.05).sum())
            result = dict(scheme=scheme, variant=variant, baseline_candidates=len(base), retained=len(kept), removed=len(killed),
                          baseline_winners=total_winners, retained_winners=winners, retained_failures_10=failures,
                          winner_recall=winners/total_winners if total_winners else np.nan,
                          winner_false_kill_rate=(total_winners-winners)/total_winners if total_winners else np.nan,
                          failure_10_rate=float(kept.r10.lt(-0.05).mean()), confirm_20_rate=float(kept.r20.gt(0.05).mean()),
                          continuation_60_rate=float(kept.r60.gt(0.1).mean()), additional_failures_per_additional_winner=(failures-int(base.r10.lt(-0.05).sum()))/(winners-total_winners) if winners != total_winners else np.nan,
                          removed_return_20_mean=float(killed.r20.mean()) if len(killed) else 0.0,
                          cash_opportunity_per_original_candidate=float(killed.r20.sum()/len(base)) if len(base) else np.nan)
            results.append(result)
            # Equal date cohorts and original slots; unfilled/filtered slots earn zero cash return.
            for bps in [0, 20, 50, 100]:
                net = np.where(retain, base.r20-bps/10000, 0.0)
                perdate = pd.Series(net, index=base.date).groupby(level=0).mean()
                costs.append(dict(scheme=scheme, variant=variant, round_trip_bps=bps,
                                  hypothetical_cohort_net_mean=float(perdate.mean()), dates=len(perdate),
                                  annualized=False, compounding=False, overlapping_capital_ledger="BLOCKED_NOT_A_STRATEGY_PNL"))
    pd.DataFrame(results).to_csv(OUT / "metrics/big_winner_incremental.csv", index=False)
    pd.DataFrame(costs).to_csv(OUT / "metrics/cost_scenarios.csv", index=False)
    pd.DataFrame(coverage).to_csv(OUT / "metrics/big_winner_coverage.csv", index=False)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--evaluate", action="store_true")
    evaluate() if p.parse_args().evaluate else main()
