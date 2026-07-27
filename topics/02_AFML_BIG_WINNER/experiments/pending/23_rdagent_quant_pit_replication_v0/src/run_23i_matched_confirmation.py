#!/usr/bin/env python3
"""Five-seed 2022/2023 confirmation for RD-Agent accepted factor libraries."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from ep23_phase2_common import load_configs
from run_23b_alpha20_lgbm_baseline import (
    apply_robust_transform,
    correlation_summary,
    cross_sectional_zscore,
    daily_correlations,
    fit_robust_transform,
)
from run_23h_static_factor_library_benchmark import quality_metrics


BRANCH_CONFIG = {
    "a20": {
        "output_key": "factor_a20",
        "library_id": "A20_RDAGENT_PINNED",
    },
    "a157": {
        "output_key": "factor_a158",
        "library_id": "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
    },
}


def load_factor_result(path: Path, internal_name: str) -> pd.Series:
    frame = pd.read_hdf(path, key="data")
    if list(frame.index.names) == ["instrument", "datetime"]:
        frame = frame.swaplevel()
    frame.index = frame.index.set_names(["datetime", "instrument"])
    frame = frame.sort_index()
    if frame.shape[1] != 1:
        raise ValueError(f"{path} must contain one factor column")
    return (
        frame.iloc[:, 0]
        .replace([np.inf, -np.inf], np.nan)
        .astype("float32")
        .rename(internal_name)
    )


def mean_abs_cross_sectional_correlations(
    existing: pd.DataFrame,
    candidate: pd.Series,
    *,
    minimum_cross_section: int,
) -> pd.Series:
    values: list[pd.Series] = []
    aligned = existing.join(candidate, how="inner")
    for _, day in aligned.groupby(level="datetime", sort=False):
        if len(day) < minimum_cross_section:
            continue
        correlations = day.corr(min_periods=minimum_cross_section)[candidate.name]
        values.append(correlations.drop(labels=[candidate.name], errors="ignore").abs())
    if not values:
        return pd.Series(dtype=float)
    return pd.concat(values, axis=1).mean(axis=1)


def split_frame(
    frame: pd.DataFrame, start: str, end: str
) -> pd.DataFrame:
    result = frame.loc[
        (slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :
    ].copy()
    return result[result["paper_proxy"].notna()]


def evaluate_state(
    *,
    state_id: str,
    features: pd.DataFrame,
    label: pd.Series,
    segments: dict[str, list[str]],
    seeds: list[int],
    lgb_params: dict[str, Any],
    clip: float,
    early_stopping_rounds: int,
    minimum_cross_section: int,
) -> tuple[
    list[dict[str, Any]],
    list[pd.DataFrame],
    list[pd.DataFrame],
]:
    panel = features.join(label.rename("paper_proxy"), how="inner").sort_index()
    split_frames = {
        name: split_frame(panel, start, end)
        for name, (start, end) in segments.items()
    }
    feature_names = list(features.columns)
    median, scale = fit_robust_transform(
        split_frames["train"][feature_names], clip=clip
    )
    transformed = {
        name: apply_robust_transform(part[feature_names], median, scale, clip)
        for name, part in split_frames.items()
    }
    targets = {
        name: cross_sectional_zscore(part["paper_proxy"])
        for name, part in split_frames.items()
    }
    train_mask = targets["train"].notna()
    valid_mask = targets["early_stop_valid"].notna()
    rows: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    prediction_parts: list[pd.DataFrame] = []
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
            transformed["train"].loc[train_mask],
            targets["train"].loc[train_mask].astype("float32"),
            eval_set=[
                (
                    transformed["early_stop_valid"].loc[valid_mask],
                    targets["early_stop_valid"].loc[valid_mask].astype("float32"),
                )
            ],
            eval_metric="l2",
            callbacks=[
                lgb.early_stopping(early_stopping_rounds, verbose=False),
                lgb.log_evaluation(period=0),
            ],
        )
        row: dict[str, Any] = {
            "state_id": state_id,
            "seed": seed,
            "feature_count": len(feature_names),
            "best_iteration": int(model.best_iteration_ or model.n_estimators),
        }
        for split_name in ["agent_feedback", "selection_confirmation"]:
            scored = split_frames[split_name][["paper_proxy"]].copy()
            scored["prediction"] = model.predict(
                transformed[split_name],
                num_iteration=model.best_iteration_,
            )
            daily = daily_correlations(
                scored,
                prediction_column="prediction",
                label_column="paper_proxy",
                minimum_cross_section=minimum_cross_section,
            )
            summary = correlation_summary(daily)
            for metric, value in summary.items():
                row[f"{split_name}_{metric}"] = value
            daily = daily.reset_index()
            daily["state_id"] = state_id
            daily["seed"] = seed
            daily["split"] = split_name
            daily_parts.append(daily)
            prediction_part = scored.reset_index()
            prediction_part["state_id"] = state_id
            prediction_part["seed"] = seed
            prediction_part["split"] = split_name
            prediction_parts.append(prediction_part)
        rows.append(row)
    del panel, split_frames, transformed, targets
    gc.collect()
    return rows, daily_parts, prediction_parts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--branch", required=True, choices=sorted(BRANCH_CONFIG))
    args = parser.parse_args()

    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2, base = load_configs(config_path)
    branch = BRANCH_CONFIG[args.branch]
    output_dir = episode_root / phase2["outputs"][branch["output_key"]]
    candidate_path = output_dir / "candidate_inventory.csv"
    if not candidate_path.exists():
        raise FileNotFoundError("run trace collector before confirmation")
    candidates = pd.read_csv(candidate_path)
    accepted = candidates[candidates["decision"].astype(str).str.lower() == "true"].copy()
    accepted = accepted.sort_values(["loop_index", "factor_name"])

    cache_path = (
        episode_root
        / phase2["outputs"]["local_cache"]
        / f"{branch['library_id'].lower()}_dual_label_panel.parquet"
    )
    base_panel = pd.read_parquet(cache_path).sort_index()
    base_feature_names = [
        column
        for column in base_panel.columns
        if column not in {"paper_proxy", "executable_bridge"}
    ]
    features = base_panel[base_feature_names].astype("float32")
    label = base_panel["paper_proxy"].astype("float32")
    nested = phase2["evolution"]["nested_segments"]
    segments = {
        "train": nested["train"],
        "early_stop_valid": nested["early_stop_valid"],
        "agent_feedback": nested["agent_feedback"],
        "selection_confirmation": nested["selection_confirmation"],
    }
    if pd.Timestamp(segments["selection_confirmation"][1]) >= pd.Timestamp(
        nested["historical_test"][0]
    ):
        raise RuntimeError("confirmation overlaps historical-test")

    train_start, train_end = segments["train"]
    train_slice = features.loc[
        (slice(pd.Timestamp(train_start), pd.Timestamp(train_end)), slice(None)), :
    ]
    redundancy_rows: list[dict[str, Any]] = []
    state_additions: list[tuple[str, list[pd.Series], int | None]] = [
        ("static_base", [], None)
    ]
    loop_to_additions: dict[int, list[pd.Series]] = {}
    current = features
    for loop_index, group in accepted.groupby("loop_index", sort=True):
        loop_additions: list[pd.Series] = []
        for _, row in group.iterrows():
            factor_name = str(row["factor_name"])
            internal_name = f"AGENT_L{int(loop_index):04d}_{factor_name}"
            result_path = Path(str(row["result_h5_path"]))
            if not result_path.is_absolute():
                result_path = output_dir / result_path
            candidate = load_factor_result(result_path, internal_name)
            train_candidate = candidate.loc[
                (slice(pd.Timestamp(train_start), pd.Timestamp(train_end)), slice(None))
            ]
            correlations = mean_abs_cross_sectional_correlations(
                train_slice,
                train_candidate,
                minimum_cross_section=int(
                    base["baseline"]["minimum_daily_cross_section"]
                ),
            )
            max_corr = float(correlations.max()) if len(correlations) else np.nan
            closest = str(correlations.idxmax()) if len(correlations) else None
            redundant = bool(np.isfinite(max_corr) and max_corr >= float(
                phase2["evolution"]["factor_dedup_correlation_threshold"]
            ))
            redundancy_rows.append(
                {
                    "loop_index": int(loop_index),
                    "factor_name": factor_name,
                    "internal_name": internal_name,
                    "max_train_mean_abs_cross_sectional_correlation": max_corr,
                    "closest_existing_feature": closest,
                    "redundant_at_0_99": redundant,
                }
            )
            current = current.join(candidate, how="left")
            loop_additions.append(candidate)
            train_slice = current.loc[
                (
                    slice(pd.Timestamp(train_start), pd.Timestamp(train_end)),
                    slice(None),
                ),
                :,
            ]
        state_additions.append(
            (
                f"agent_chain_through_loop_{int(loop_index):04d}",
                loop_additions,
                int(loop_index),
            )
        )
        loop_to_additions[int(loop_index)] = loop_additions
    del current, train_slice
    gc.collect()

    seeds = list(phase2["benchmark"]["seeds"])
    all_seed_rows: list[dict[str, Any]] = []
    all_daily: list[pd.DataFrame] = []
    all_predictions: list[pd.DataFrame] = []
    quality_rows: list[dict[str, Any]] = []
    eval_features = features
    for state_id, additions, _ in state_additions:
        for candidate in additions:
            eval_features = eval_features.join(candidate, how="left")
        rows, daily, predictions = evaluate_state(
            state_id=state_id,
            features=eval_features,
            label=label,
            segments=segments,
            seeds=seeds,
            lgb_params=dict(base["baseline"]["lightgbm"]),
            clip=float(base["baseline"]["robust_zscore_clip"]),
            early_stopping_rounds=int(base["baseline"]["early_stopping_rounds"]),
            minimum_cross_section=int(
                base["baseline"]["minimum_daily_cross_section"]
            ),
        )
        all_seed_rows.extend(rows)
        all_daily.extend(daily)
        all_predictions.extend(predictions)
        train_features = eval_features.loc[
            (
                slice(pd.Timestamp(train_start), pd.Timestamp(train_end)),
                slice(None),
            ),
            :,
        ]
        quality = quality_metrics(state_id, train_features)
        quality["state_id"] = quality.pop("library_id")
        quality["branch"] = args.branch
        quality_rows.append(quality)

    seed_metrics = pd.DataFrame(all_seed_rows)
    seed_metrics.to_csv(output_dir / "confirmation_seed_metrics.csv", index=False)
    pd.concat(all_daily, ignore_index=True).to_csv(
        output_dir / "confirmation_daily_metrics.csv", index=False
    )
    confirmation_prediction_path = (
        cache_path.parent
        / f"23i_{args.branch}_confirmation_predictions.parquet"
    )
    pd.concat(all_predictions, ignore_index=True).to_parquet(
        confirmation_prediction_path, index=False
    )
    redundancy = pd.DataFrame(redundancy_rows)
    redundancy.to_csv(output_dir / "redundancy_audit.csv", index=False)

    state_order = [state_id for state_id, _, _ in state_additions]
    summary_rows: list[dict[str, Any]] = []
    attribution_rows: list[dict[str, Any]] = []
    daily_frame = pd.concat(all_daily, ignore_index=True)
    prediction_frame = pd.concat(all_predictions, ignore_index=True)
    for state_position, state_id in enumerate(state_order):
        group = seed_metrics[seed_metrics["state_id"] == state_id]
        row: dict[str, Any] = {
            "state_id": state_id,
            "feature_count": int(group["feature_count"].iloc[0]),
        }
        for split_name in ["agent_feedback", "selection_confirmation"]:
            for metric in ["IC", "Rank IC", "ICIR", "Rank ICIR"]:
                column = f"{split_name}_{metric}"
                row[f"{column}_median"] = float(group[column].median())
        summary_rows.append(row)
        if state_position == 0:
            continue
        previous_id = state_order[state_position - 1]
        previous = seed_metrics[
            seed_metrics["state_id"] == previous_id
        ].set_index("seed")
        current_metrics = group.set_index("seed")
        loop_index = int(state_id.rsplit("_", 1)[-1])
        attr: dict[str, Any] = {
            "loop_index": loop_index,
            "previous_state_id": previous_id,
            "current_state_id": state_id,
        }
        metric_passes = []
        for split_name in ["agent_feedback", "selection_confirmation"]:
            for metric in ["IC", "Rank IC"]:
                column = f"{split_name}_{metric}"
                delta = current_metrics[column] - previous[column]
                prefix = f"{split_name}_{metric.replace(' ', '_').lower()}"
                attr[f"{prefix}_delta_median"] = float(delta.median())
                attr[f"{prefix}_positive_seeds"] = int((delta > 0).sum())
                if split_name == "selection_confirmation":
                    metric_passes.append(
                        float(delta.median()) > 0 and int((delta > 0).sum()) >= 4
                    )
        feedback_positive = (
            attr["agent_feedback_ic_delta_median"] > 0
            or attr["agent_feedback_rank_ic_delta_median"] > 0
        )
        confirmation_positive = any(metric_passes)
        attr["feedback_improvement"] = feedback_positive
        attr["confirmation_4_of_5_improvement"] = confirmation_positive
        attr["no_feedback_confirmation_sign_reversal"] = (
            feedback_positive and confirmation_positive
        )
        loop_redundancy = redundancy[redundancy["loop_index"] == loop_index]
        attr["all_new_factors_nonredundant"] = bool(
            len(loop_redundancy) > 0
            and not loop_redundancy["redundant_at_0_99"].any()
        )
        selected_daily = daily_frame[
            daily_frame["split"].eq("selection_confirmation")
            & daily_frame["state_id"].isin([previous_id, state_id])
        ]
        daily_pivot = selected_daily.pivot_table(
            index=["seed", "datetime"],
            columns="state_id",
            values="ic",
            aggfunc="first",
        ).dropna()
        daily_delta = (
            daily_pivot[state_id] - daily_pivot[previous_id]
        ).groupby(level="datetime").median()
        daily_abs_sum = float(daily_delta.abs().sum())
        attr["max_abs_daily_delta_share"] = (
            float(daily_delta.abs().max() / daily_abs_sum)
            if daily_abs_sum > 0
            else np.nan
        )
        attr["not_single_day_dominated_at_0_20"] = bool(
            np.isfinite(attr["max_abs_daily_delta_share"])
            and attr["max_abs_daily_delta_share"] <= 0.20
        )

        selected_predictions = prediction_frame[
            prediction_frame["split"].eq("selection_confirmation")
            & prediction_frame["state_id"].isin([previous_id, state_id])
        ]
        instrument_rows: list[dict[str, Any]] = []
        for (
            instrument_state,
            instrument_seed,
            instrument,
        ), instrument_group in selected_predictions.groupby(
            ["state_id", "seed", "instrument"], sort=False
        ):
            valid = instrument_group[
                ["prediction", "paper_proxy"]
            ].dropna()
            instrument_ic = (
                float(valid["prediction"].corr(valid["paper_proxy"]))
                if len(valid) >= 60
                else np.nan
            )
            instrument_rows.append(
                {
                    "state_id": instrument_state,
                    "seed": instrument_seed,
                    "instrument": instrument,
                    "instrument_ic": instrument_ic,
                }
            )
        instrument_frame = pd.DataFrame(instrument_rows)
        instrument_pivot = instrument_frame.pivot_table(
            index=["seed", "instrument"],
            columns="state_id",
            values="instrument_ic",
            aggfunc="first",
        ).dropna()
        instrument_delta = (
            instrument_pivot[state_id] - instrument_pivot[previous_id]
        ).groupby(level="instrument").median()
        instrument_abs_sum = float(instrument_delta.abs().sum())
        attr["max_abs_instrument_delta_share"] = (
            float(
                instrument_delta.abs().max() / instrument_abs_sum
            )
            if instrument_abs_sum > 0
            else np.nan
        )
        attr["not_single_instrument_dominated_at_0_20"] = bool(
            np.isfinite(attr["max_abs_instrument_delta_share"])
            and attr["max_abs_instrument_delta_share"] <= 0.20
        )
        closest_counts = loop_redundancy[
            "closest_existing_feature"
        ].fillna("none").value_counts()
        attr["largest_closest_feature_cluster_share"] = (
            float(closest_counts.max() / closest_counts.sum())
            if len(closest_counts)
            else np.nan
        )
        attr["not_single_factor_cluster_dominated"] = bool(
            len(loop_redundancy) <= 1
            or attr["largest_closest_feature_cluster_share"] < 1.0
        )
        attr["predictive_confirmation_pass"] = bool(
            attr["no_feedback_confirmation_sign_reversal"]
            and attr["all_new_factors_nonredundant"]
            and attr["not_single_day_dominated_at_0_20"]
            and attr["not_single_instrument_dominated_at_0_20"]
            and attr["not_single_factor_cluster_dominated"]
        )
        attribution_rows.append(attr)

    pd.DataFrame(summary_rows).to_csv(
        output_dir / "library_state_summary.csv", index=False
    )
    attribution = pd.DataFrame(attribution_rows)
    confirmed_loop_indices = (
        [
            int(value)
            for value in attribution.loc[
                attribution["predictive_confirmation_pass"],
                "loop_index",
            ].tolist()
        ]
        if len(attribution)
        else []
    )
    retained_features = features
    for loop_index in confirmed_loop_indices:
        for candidate in loop_to_additions.get(loop_index, []):
            retained_features = retained_features.join(candidate, how="left")
    retained_rows, retained_daily, retained_predictions = evaluate_state(
        state_id="ep23_retained",
        features=retained_features,
        label=label,
        segments=segments,
        seeds=seeds,
        lgb_params=dict(base["baseline"]["lightgbm"]),
        clip=float(base["baseline"]["robust_zscore_clip"]),
        early_stopping_rounds=int(base["baseline"]["early_stopping_rounds"]),
        minimum_cross_section=int(
            base["baseline"]["minimum_daily_cross_section"]
        ),
    )
    all_seed_rows.extend(retained_rows)
    all_daily.extend(retained_daily)
    all_predictions.extend(retained_predictions)
    retained_train = retained_features.loc[
        (
            slice(pd.Timestamp(train_start), pd.Timestamp(train_end)),
            slice(None),
        ),
        :,
    ]
    retained_quality = quality_metrics("ep23_retained", retained_train)
    retained_quality["state_id"] = retained_quality.pop("library_id")
    retained_quality["branch"] = args.branch
    quality_rows.append(retained_quality)

    seed_metrics = pd.DataFrame(all_seed_rows)
    retained_group = seed_metrics[
        seed_metrics["state_id"] == "ep23_retained"
    ]
    retained_summary: dict[str, Any] = {
        "state_id": "ep23_retained",
        "feature_count": int(retained_group["feature_count"].iloc[0]),
    }
    for split_name in ["agent_feedback", "selection_confirmation"]:
        for metric in ["IC", "Rank IC", "ICIR", "Rank ICIR"]:
            column = f"{split_name}_{metric}"
            retained_summary[f"{column}_median"] = float(
                retained_group[column].median()
            )
    summary_rows.append(retained_summary)

    seed_metrics.to_csv(
        output_dir / "confirmation_seed_metrics.csv", index=False
    )
    pd.concat(all_daily, ignore_index=True).to_csv(
        output_dir / "confirmation_daily_metrics.csv", index=False
    )
    pd.DataFrame(summary_rows).to_csv(
        output_dir / "library_state_summary.csv", index=False
    )
    pd.DataFrame(quality_rows).to_csv(
        output_dir / "library_quality_metrics.csv", index=False
    )
    attribution.to_csv(
        output_dir / "matched_marginal_attribution.csv", index=False
    )
    retained_factor_rows = accepted[
        accepted["loop_index"].astype(int).isin(confirmed_loop_indices)
    ]
    (output_dir / "ep23_retained_library.json").write_text(
        json.dumps(
            {
                "branch": args.branch,
                "retained_loop_indices": confirmed_loop_indices,
                "retained_factor_count": int(len(retained_factor_rows)),
                "retained_factors": retained_factor_rows[
                    [
                        "loop_index",
                        "factor_name",
                        "code_sha256",
                        "result_h5_sha256",
                        "result_h5_path",
                    ]
                ].to_dict(orient="records"),
                "historical_test_read": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    verdict = {
        "branch": args.branch,
        "accepted_loop_count": int(accepted["loop_index"].nunique()),
        "accepted_factor_count": int(len(accepted)),
        "predictive_confirmation_pass_loops": (
            int(attribution["predictive_confirmation_pass"].sum())
            if len(attribution)
            else 0
        ),
        "predictive_confirmation_pass": bool(confirmed_loop_indices),
        "retained_loop_indices": confirmed_loop_indices,
        "retained_factor_count": int(len(retained_factor_rows)),
        "intermediate_verdict": (
            "predictive_evolution_candidate"
            if len(attribution)
            and bool(attribution["predictive_confirmation_pass"].any())
            else "no_predictive_evolution"
        ),
        "historical_test_read": False,
        "next_open_and_big_winner_pending_23l": True,
        "confirmation_prediction_path": str(
            confirmation_prediction_path.relative_to(episode_root)
        ),
    }
    (output_dir / "confirmation_verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
