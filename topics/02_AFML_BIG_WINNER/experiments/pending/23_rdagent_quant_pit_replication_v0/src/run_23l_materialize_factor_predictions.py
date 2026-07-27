#!/usr/bin/env python3
"""Materialize frozen static/evolved factor scores for the 23L historical test."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import pandas as pd

from ep23_phase2_common import load_configs, sha256_file
from run_23b_alpha20_lgbm_baseline import (
    apply_robust_transform,
    cross_sectional_zscore,
    fit_robust_transform,
)
from run_23i_matched_confirmation import load_factor_result


BRANCHES = {
    "a20": {
        "output_key": "factor_a20",
        "library_id": "A20_RDAGENT_PINNED",
    },
    "a157": {
        "output_key": "factor_a158",
        "library_id": "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
    },
}


def split(
    frame: pd.DataFrame, segment: list[str], require_label: bool
) -> pd.DataFrame:
    start, end = map(pd.Timestamp, segment)
    result = frame.loc[(slice(start, end), slice(None)), :].copy()
    if require_label:
        result = result[result["paper_proxy"].notna()]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--branch", required=True, choices=sorted(BRANCHES))
    args = parser.parse_args()

    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2, base = load_configs(config_path)
    spec = BRANCHES[args.branch]
    branch_dir = episode_root / phase2["outputs"][spec["output_key"]]
    verdict_path = branch_dir / "confirmation_verdict.json"
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    retained_path = branch_dir / "ep23_retained_library.json"
    retained = json.loads(retained_path.read_text(encoding="utf-8"))
    retained_factors = retained["retained_factors"]

    cache_dir = episode_root / phase2["outputs"]["local_cache"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    panel_path = (
        cache_dir / f"{spec['library_id'].lower()}_dual_label_panel.parquet"
    )
    panel = pd.read_parquet(panel_path).sort_index()
    base_features = [
        column
        for column in panel.columns
        if column not in {"paper_proxy", "executable_bridge"}
    ]
    states: dict[str, pd.DataFrame] = {
        f"{args.branch}_static": panel[base_features].astype("float32")
    }
    if verdict.get("predictive_confirmation_pass") and retained_factors:
        evolved = states[f"{args.branch}_static"]
        for position, factor in enumerate(retained_factors):
            result_path = Path(str(factor["result_h5_path"]))
            if not result_path.is_absolute():
                result_path = branch_dir / result_path
            internal_name = (
                f"EP23_L{int(factor['loop_index']):04d}_"
                f"{position:03d}_{factor['factor_name']}"
            )
            values = load_factor_result(result_path, internal_name)
            evolved = evolved.join(values, how="left")
        states[f"{args.branch}_evolved"] = evolved

    segments = phase2["evolution"]["nested_segments"]
    seeds = list(map(int, phase2["benchmark"]["seeds"]))
    clip = float(base["baseline"]["robust_zscore_clip"])
    early_stopping = int(base["baseline"]["early_stopping_rounds"])
    lgb_params = dict(base["baseline"]["lightgbm"])
    inventory: list[dict[str, Any]] = []
    for state_id, features in states.items():
        joined = features.join(
            panel[["paper_proxy", "executable_bridge"]], how="inner"
        ).sort_index()
        train = split(joined, segments["train"], require_label=True)
        valid = split(
            joined, segments["early_stop_valid"], require_label=True
        )
        confirmation = split(
            joined, segments["selection_confirmation"], require_label=True
        )
        historical = split(
            joined, segments["historical_test"], require_label=False
        )
        feature_names = list(features.columns)
        median, scale = fit_robust_transform(
            train[feature_names], clip=clip
        )
        x_train = apply_robust_transform(
            train[feature_names], median, scale, clip
        )
        x_valid = apply_robust_transform(
            valid[feature_names], median, scale, clip
        )
        x_confirmation = apply_robust_transform(
            confirmation[feature_names], median, scale, clip
        )
        x_historical = apply_robust_transform(
            historical[feature_names], median, scale, clip
        )
        y_train = cross_sectional_zscore(train["paper_proxy"])
        y_valid = cross_sectional_zscore(valid["paper_proxy"])
        train_mask = y_train.notna()
        valid_mask = y_valid.notna()
        for seed in seeds:
            params = {
                **lgb_params,
                "random_state": seed,
                "bagging_seed": seed,
                "feature_fraction_seed": seed,
                "data_random_seed": seed,
                "verbosity": -1,
            }
            model = lgb.LGBMRegressor(**params)
            model.fit(
                x_train.loc[train_mask],
                y_train.loc[train_mask].astype("float32"),
                eval_set=[
                    (
                        x_valid.loc[valid_mask],
                        y_valid.loc[valid_mask].astype("float32"),
                    )
                ],
                eval_metric="l2",
                callbacks=[
                    lgb.early_stopping(early_stopping, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            confirmation_score = pd.DataFrame(
                {
                    "paper_proxy": confirmation["paper_proxy"],
                    "executable_bridge": confirmation["executable_bridge"],
                    "prediction": model.predict(
                        x_confirmation,
                        num_iteration=model.best_iteration_,
                    ),
                    "split": "selection_confirmation",
                    "state_id": state_id,
                    "seed": seed,
                },
                index=confirmation.index,
            )
            historical_score = pd.DataFrame(
                {
                    "paper_proxy": historical["paper_proxy"],
                    "executable_bridge": historical["executable_bridge"],
                    "prediction": model.predict(
                        x_historical,
                        num_iteration=model.best_iteration_,
                    ),
                    "split": "historical_test",
                    "state_id": state_id,
                    "seed": seed,
                },
                index=historical.index,
            )
            scores = pd.concat(
                [confirmation_score, historical_score]
            ).sort_index()
            path = (
                cache_dir
                / f"23l_{state_id}_lgbm_seed_{seed}_predictions.parquet"
            )
            scores.to_parquet(path)
            inventory.append(
                {
                    "branch": args.branch,
                    "state_id": state_id,
                    "seed": seed,
                    "feature_count": len(feature_names),
                    "best_iteration": int(
                        model.best_iteration_ or model.n_estimators
                    ),
                    "row_count": len(scores),
                    "confirmation_row_count": len(confirmation_score),
                    "historical_test_row_count": len(historical_score),
                    "prediction_path": str(path.relative_to(episode_root)),
                    "prediction_sha256": sha256_file(path),
                    "frozen_before_historical_test_read": True,
                    "historical_test_read": True,
                }
            )
            del model, confirmation_score, historical_score, scores
            gc.collect()
        del joined, train, valid, confirmation, historical
        del x_train, x_valid, x_confirmation, x_historical
        gc.collect()

    inventory_path = branch_dir / "23l_prediction_inventory.csv"
    pd.DataFrame(inventory).to_csv(inventory_path, index=False)
    print(
        json.dumps(
            {
                "branch": args.branch,
                "state_count": len(states),
                "prediction_artifact_count": len(inventory),
                "historical_test_read": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
