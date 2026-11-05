"""Nested chronological fit. Outer outcomes are inaccessible to prediction code."""
from __future__ import annotations

import argparse
import json
import pickle

import numpy as np
import pandas as pd

from baselines import HypothesisTransform, Ridge, prediction_loss
from common import OUT, cache, config, frozen, sha, source_manifest, utc_now, write_json

LAG_FIELDS = ["mom20", "mom60", "rv5", "rv20", "rv60", "log_turnover", "log_float_cap_proxy", "log_money",
              "amplitude", "day_return", "breakthrough_strength", "market_mom20", "market_rv20", "atr", "mavd",
              "abnormal_volume", "relative_volume", "relative_turnover", "turnover20", "eff", "trend_decay"]


def permute_within_date_board(frame, column, rng):
    result = frame[column].to_numpy(copy=True)
    for indices in frame.groupby(["date", "board"], sort=False).indices.values():
        result[indices] = result[rng.permutation(indices)]
    return result


def append_lagged_features(features):
    from ep30_adapter import EP30Adapter
    days = EP30Adapter().days
    current_i = days.get_indexer(features.date)
    reference = np.full(len(features), np.datetime64("NaT"), dtype="datetime64[ns]")
    valid = current_i >= 20
    reference[valid] = days.to_numpy()[current_i[valid]-20]
    keys = features[["date", "security_id"]].copy()
    keys["lag_date"] = reference
    old = features[["date", "security_id"]+LAG_FIELDS].rename(columns={"date": "lag_date", **{c: "lag_"+c for c in LAG_FIELDS}})
    add = keys.merge(old, on=["lag_date", "security_id"], how="left", validate="many_to_one")
    result = features.copy()
    for c in LAG_FIELDS:
        result["lag_"+c] = add["lag_"+c].to_numpy()
    result["lag_available"] = add.lag_mom60.notna().to_numpy()
    return result


def training_mask(frame, cutoff, window="expanding"):
    cutoff = pd.Timestamp(cutoff)
    m = frame.date.lt(cutoff) & frame.mature_at.lt(cutoff) & frame.y.notna()
    if window == "rolling36":
        m &= frame.date.ge(cutoff - pd.DateOffset(months=36))
    return m


def history_sufficient(train, months=24):
    return len(train) >= 200 and train.date.nunique() >= 50 and train.date.max() - train.date.min() >= pd.Timedelta(days=365.25*months/12 - 14)


def inner_splits(frame, cutoff, window, horizon=0):
    cutoff = pd.Timestamp(cutoff)
    validation_end = cutoff
    if horizon:
        from ep30_adapter import EP30Adapter
        days = EP30Adapter().days
        index = days.searchsorted(cutoff) - int(horizon)
        validation_end = days[max(0, index)]
    for ago in [6, 3]:
        start = validation_end - pd.DateOffset(months=ago)
        end = min(validation_end, start + pd.DateOffset(months=3))
        train = frame.loc[training_mask(frame, start, window)]
        val = frame.loc[frame.date.ge(start) & frame.date.lt(end) & frame.mature_at.lt(cutoff) & frame.y.notna()]
        # This is a cross-security interval purge, not a same-stock-only filter.
        if len(train) and train.mature_at.max() >= start:
            raise AssertionError("purge leak")
        yield start, train, val


def load_features():
    root = cache() / "data"
    complete = json.loads((root / "COMPLETE.json").read_text())
    pieces = []
    for p in sorted(root.glob("features_*.parquet")):
        if sha(p) != complete["files"][p.name]:
            raise ValueError("feature partition changed")
        pieces.append(pd.read_parquet(p))
    f = pd.concat(pieces, ignore_index=True)
    f = f.merge(pd.read_parquet(root / "market.parquet"), on="date", how="left", validate="many_to_one")
    return f


def load_outcomes(horizon, columns=None):
    root = cache() / "data"
    complete = json.loads((root / "COMPLETE.json").read_text())
    pieces = []
    for p in sorted(root.glob(f"labels_{horizon}_*.parquet")):
        if sha(p) != complete["files"][p.name]:
            raise ValueError("label partition changed")
        pieces.append(pd.read_parquet(p, columns=columns))
    return pd.concat(pieces, ignore_index=True)


def cohort(features, hypothesis):
    mask = features.h10_episode.fillna(False) if hypothesis == "H10" else features.h11_episode.fillna(False) if hypothesis == "H11" else features.weekly.fillna(False)
    return features.loc[mask & features.warmup.fillna(False) & features.observed.fillna(False)].copy()


def target_frame(features, outcomes, hypothesis, endpoint):
    columns = ["date", "security_id", "value", "mature_at", "status", "entry_date", "exit_date"]
    if hypothesis == "H07":
        columns += ["future_variance", "rv_mature_at"]
    f = features.merge(outcomes[columns], on=["date", "security_id"], validate="one_to_one", how="left")
    f["y"] = f.value
    if endpoint == "log_variance_mse":
        f["y"] = np.log(f.future_variance + 1e-12)
        f["mature_at"] = f.rv_mature_at
    elif endpoint == "downside_brier":
        f["y"] = f.value.lt(-0.1).astype(float).where(f.value.notna())
    return f


def fit_pair(train, hypothesis, factor, alpha, placebo=False):
    transform = HypothesisTransform().fit(train)
    a = transform.apply(train, hypothesis)
    controls = transform.controls(hypothesis)
    base = Ridge().fit(a[controls], a.y, a.date, alpha)
    augmented = Ridge().fit(a[controls + [factor]], a.y, a.date, alpha)
    # Residualization of the factor is also train-only and frozen per fold.
    fm = a[factor].notna()
    factor_model = Ridge().fit(a.loc[fm, controls], a.loc[fm, factor], a.loc[fm, "date"], alpha)
    factor_scale = float(a.loc[fm, factor].std())
    sort_low, sort_high = a.loc[fm, factor].quantile([0.1, 0.9]).tolist()
    output = dict(transform=transform, base=base, augmented=augmented, factor_model=factor_model,
                factor_scale=max(1e-12, factor_scale), sort_low=sort_low, sort_high=sort_high,
                controls=controls, factor=factor)
    if placebo:
        rng = np.random.default_rng(310021)
        yp = permute_within_date_board(a, "y", rng)
        output["label_permuted_base"] = Ridge().fit(a[controls], yp, a.date, alpha)
        output["label_permuted_augmented"] = Ridge().fit(a[controls+[factor]], yp, a.date, alpha)
        shuffled = a.copy()
        shuffled[factor] = permute_within_date_board(a, factor, rng)
        output["shuffled_model"] = Ridge().fit(shuffled[controls+[factor]], a.y, a.date, alpha)
    return output


def predict_pair(model, features, hypothesis):
    # No outcome columns accepted by the prediction entry point.
    forbidden = {"y", "value", "future_variance", "status", "mature_at", "exit_date"}
    if forbidden.intersection(features.columns):
        raise ValueError("outer labels passed to prediction")
    a = model["transform"].apply(features, hypothesis)
    controls, factor = model["controls"], model["factor"]
    out = a[["date", "security_id", "board", "log_float_cap_proxy", "log_money", "market_mom20",
             "is_delisted", "provider_disagreement", "factor_step_200", "share_proxy_step_20", "one_price_bar",
             "momentum_group", "turnover_group", "size_group", "liquidity_group"]].copy()
    out["baseline"] = model["base"].predict(a[controls])
    out["augmented"] = model["augmented"].predict(a[controls + [factor]])
    out["factor_raw"] = a[factor]
    out["partial_x"] = (a[factor] - model["factor_model"].predict(a[controls])) / model["factor_scale"]
    out["sort_group"] = np.select([a[factor].le(model["sort_low"]), a[factor].ge(model["sort_high"])], [-1, 1], default=0)
    out["applicable"] = a[factor].notna()
    out["alternative_factor"] = a.mavd_turnover if hypothesis == "H02" else np.nan
    if "label_permuted_base" in model:
        out["label_permuted_base"] = model["label_permuted_base"].predict(a[controls])
        out["label_permuted_augmented"] = model["label_permuted_augmented"].predict(a[controls+[factor]])
        shuffled = a.copy()
        shuffled[factor] = permute_within_date_board(a, factor, np.random.default_rng(310021))
        out["shuffled_augmented"] = model["shuffled_model"].predict(shuffled[controls+[factor]])
        lagged = features.copy()
        for c in LAG_FIELDS:
            lagged[c] = features["lag_"+c]
        la = model["transform"].apply(lagged, hypothesis)
        out["lagged_base"] = model["base"].predict(la[controls])
        out["lagged_augmented"] = model["augmented"].predict(la[controls+[factor]])
        out["lag_available"] = features.lag_available
    return out


def select_alpha(frame, cutoff, window, hypothesis, spec):
    results, times = [], []
    for start, train, val in inner_splits(frame, cutoff, window, spec["horizon"]):
        ready = history_sufficient(train) and len(val) >= 50
        times.append(dict(start=str(start), train_rows=len(train), validation_rows=len(val),
                          train_min=str(train.date.min()), train_max=str(train.date.max()),
                          max_maturity=str(train.mature_at.max()), ready=ready))
        if not ready:
            return None, results, times
        for alpha in [1.0, 100.0]:
            model = fit_pair(train, hypothesis, spec["feature"], alpha)
            a = model["transform"].apply(val, hypothesis)
            pred = model["augmented"].predict(a[model["controls"] + [spec["feature"]]])
            loss = prediction_loss(val.y, pred, spec["endpoint"])
            mean_loss = pd.Series(loss, index=val.date).groupby(level=0).mean().mean()
            results.append(dict(start=str(start), alpha=alpha, loss=float(mean_loss)))
    selected = pd.DataFrame(results).groupby("alpha").loss.mean().idxmin()
    return float(selected), results, times


def run(hypothesis, all_features=None):
    run_sources = source_manifest()
    spec = config()["primary"][hypothesis]
    full_features = load_features() if all_features is None else all_features
    features = cohort(append_lagged_features(full_features), hypothesis)
    del full_features
    factor_valid = features[spec["feature"]].notna() if hypothesis != "H10" else features.eff.notna() & features.relative_turnover.notna()
    features = features.loc[factor_valid].copy()
    outcomes = load_outcomes(spec["horizon"])
    frame = target_frame(features, outcomes, hypothesis, spec["endpoint"])
    del outcomes
    payload = cache() / "fold_predictions" / hypothesis
    payload.mkdir(parents=True, exist_ok=True)
    modelroot = cache() / "models" / hypothesis
    modelroot.mkdir(parents=True, exist_ok=True)
    receipts, blocked = [], []
    quarters = pd.period_range("2021Q1", frame.date.max().to_period("Q"), freq="Q")
    for scheme in ["expanding", "rolling36"]:
        for q in quarters:
            cutoff = q.start_time
            test_features = features.loc[features.date.dt.to_period("Q").eq(q)]
            train = frame.loc[training_mask(frame, cutoff, scheme)]
            if not len(test_features) or not history_sufficient(train):
                blocked.append(dict(hypothesis=hypothesis, scheme=scheme, fold=str(q), reason="BLOCKED_INSUFFICIENT_HISTORY", train_rows=len(train), test_rows=len(test_features)))
                continue
            alpha, cv, times = select_alpha(frame, cutoff, scheme, hypothesis, spec)
            if alpha is None:
                blocked.append(dict(hypothesis=hypothesis, scheme=scheme, fold=str(q), reason="BLOCKED_INNER_HISTORY", inner=times))
                continue
            model = fit_pair(train, hypothesis, spec["feature"], alpha, placebo=True)
            key = f"{scheme}_{q}"
            modelpath = modelroot / (key + ".pkl")
            if modelpath.exists():
                raise RuntimeError("frozen fold already exists: " + key)
            modelpath.write_bytes(pickle.dumps(model, protocol=5))
            predictions = predict_pair(model, test_features, hypothesis)
            predictions["fold"], predictions["scheme"], predictions["hypothesis"] = str(q), scheme, hypothesis
            predpath = payload / (key + ".parquet")
            predictions.to_parquet(predpath, index=False)
            # Verification replay uses serialized model against feature-only input.
            replay = predict_pair(pickle.loads(modelpath.read_bytes()), test_features, hypothesis)
            if not np.allclose(replay.baseline, predictions.baseline, equal_nan=True) or not np.allclose(replay.augmented, predictions.augmented, equal_nan=True):
                raise AssertionError("model replay mismatch")
            receipt = dict(hypothesis=hypothesis, scheme=scheme, fold=str(q), fit_cutoff=str(cutoff),
                           train_rows=len(train), train_start=str(train.date.min()), train_end=str(train.date.max()),
                           max_train_mature_at=str(train.mature_at.max()), alpha=alpha, cv=cv, inner_timeline=times,
                           factor_coefficient=float(model["augmented"].coef[1+len(model["controls"])]),
                           test_rows=len(predictions), model_path=str(modelpath), model_sha256=sha(modelpath),
                           predictions_path=str(predpath), predictions_sha256=sha(predpath),
                           predictions_written_at=utc_now(), outer_outcomes_scored=False,
                           model_replay="PASS", quality="Historical-proxy", preregistration_id=frozen()["preregistration_id"])
            write_json(modelroot / (key + ".json"), receipt)
            receipts.append(receipt)
            print("P2 frozen", hypothesis, key, "train", len(train), "test", len(predictions), flush=True)
    write_json(OUT / f"manifests/{hypothesis}_folds.json", dict(folds=receipts, blocked=blocked, sources=run_sources, revision="EP31-P0-R01",
               prediction_freeze_completed_at=utc_now(), outcome_scoring_started=False))
    pd.DataFrame([{k: v for k, v in r.items() if k not in {"cv", "inner_timeline"}} for r in receipts]).to_csv(OUT / f"audits/{hypothesis}_fold_timeline.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hypothesis", required=True, choices=["H01", "H02", "H03", "H07", "H10", "H11", "H12"])
    run(parser.parse_args().hypothesis)
