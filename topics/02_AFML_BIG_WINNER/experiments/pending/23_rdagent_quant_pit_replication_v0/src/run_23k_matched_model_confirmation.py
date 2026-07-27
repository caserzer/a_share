#!/usr/bin/env python3
"""Matched five-seed 2022/2023 confirmation for accepted RD-Model candidates."""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import pandas as pd
import qlib
import torch
from qlib.contrib.model.pytorch_general_nn import GeneralPTNN
from qlib.data.dataset import TSDatasetH
from qlib.data.dataset.handler import DataHandlerLP
from qlib.utils import init_instance_by_config
from torch.utils.data import DataLoader

from ep23_phase2_common import load_configs, sha256_file
from run_23b_alpha20_lgbm_baseline import (
    correlation_summary,
    daily_correlations,
)


BASELINES = {
    "flattened_mlp": "ep23_model_variants.FlattenedWindowMLP",
    "last_state_gru": "ep23_model_variants.LastStateGRU128",
    "attentive_gru": "ep23_model_variants.AttentiveGRU128",
}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def build_dataset(
    *,
    base: dict[str, Any],
    phase2: dict[str, Any],
    provider_path: Path,
    end_segment: str = "selection_confirmation",
    timeseries: bool = True,
) -> Any:
    names = list(base["alpha20"])
    expressions = [base["alpha20"][name] for name in names]
    nested = phase2["evolution"]["nested_segments"]
    end_time = nested[end_segment][1]
    data_loader = {
        "class": "NestedDataLoader",
        "kwargs": {
            "dataloader_l": [
                {
                    "class": "Alpha158DL",
                    "module_path": "qlib.contrib.data.loader",
                    "kwargs": {
                        "config": {
                            "label": [
                                [base["labels"]["paper_proxy"]["expression"]],
                                ["LABEL0"],
                            ],
                            "feature": [expressions, names],
                        }
                    },
                }
            ]
        },
    }
    handler = {
        "class": "DataHandlerLP",
        "module_path": "qlib.contrib.data.handler",
        "kwargs": {
            "start_time": nested["train"][0],
            "end_time": end_time,
            "instruments": base["data"]["market"],
            "data_loader": data_loader,
            "infer_processors": [
                {
                    "class": "RobustZScoreNorm",
                    "kwargs": {
                        "fields_group": "feature",
                        "clip_outlier": True,
                        "fit_start_time": nested["train"][0],
                        "fit_end_time": nested["train"][1],
                    },
                },
                {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
            ],
            "learn_processors": [
                {"class": "DropnaLabel"},
                {
                    "class": "CSZScoreNorm",
                    "kwargs": {"fields_group": "label"},
                },
            ],
        },
    }
    dataset_config = {
        "class": "TSDatasetH" if timeseries else "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler,
            "segments": {
                "train": nested["train"],
                "valid": nested["early_stop_valid"],
                "agent_feedback": nested["agent_feedback"],
                "selection_confirmation": nested[
                    "selection_confirmation"
                ],
                **(
                    {"historical_test": nested["historical_test"]}
                    if end_segment == "historical_test"
                    else {}
                ),
            },
            **(
                {
                    "step_len": int(
                        base["model_attribution"]["num_timesteps"]
                    )
                }
                if timeseries
                else {}
            ),
        },
    }
    qlib.init(provider_uri=str(provider_path), region="cn")
    return init_instance_by_config(dataset_config)


def predict_named_segment(
    model: GeneralPTNN, dataset: Any, segment: str
) -> pd.Series:
    prepared = dataset.prepare(
        segment,
        col_set=["feature", "label"],
        data_key=DataHandlerLP.DK_I,
    )
    if isinstance(dataset, TSDatasetH):
        prepared.config(fillna_type="ffill+bfill")
        index = prepared.get_index()
        loader_data = prepared
    else:
        index = prepared.index
        loader_data = prepared.values
    loader = DataLoader(
        loader_data,
        batch_size=model.batch_size,
        num_workers=model.n_jobs,
        shuffle=False,
    )
    model.dnn_model.eval()
    predictions: list[np.ndarray] = []
    for data in loader:
        feature, _ = model._get_fl(data)
        feature = feature.to(model.device)
        with torch.no_grad():
            prediction = (
                model.dnn_model(feature.float()).detach().cpu().numpy()
            )
        predictions.append(prediction)
    values = np.concatenate(predictions).reshape(-1)
    return pd.Series(values, index=index, name="prediction")


def register_candidate_module(
    path: Path, loop_index: int
) -> tuple[str, Any]:
    module_name = f"ep23_rdmodel_loop_{loop_index:04d}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load model candidate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "model_cls"):
        raise AttributeError(f"{path} has no model_cls")
    return f"{module_name}.model_cls", module


def training_config(
    base: dict[str, Any],
    candidate: pd.Series | None,
) -> dict[str, Any]:
    frozen = base["model_attribution"]
    result = {
        "n_epochs": int(frozen["n_epochs"]),
        "lr": float(frozen["learning_rate"]),
        "early_stop": int(frozen["early_stop"]),
        "batch_size": int(frozen["batch_size"]),
        "weight_decay": float(frozen["weight_decay"]),
    }
    if candidate is None:
        return result
    declared = json.loads(str(candidate["training_hyperparameters_json"]))
    if isinstance(declared, dict):
        mappings = {
            "n_epochs": int,
            "lr": float,
            "early_stop": int,
            "batch_size": int,
            "weight_decay": float,
        }
        for key, caster in mappings.items():
            if key in declared and declared[key] is not None:
                result[key] = caster(declared[key])
    return result


def evaluate_variant(
    *,
    variant: str,
    uri: str,
    candidate: pd.Series | None,
    dataset: Any,
    seeds: list[int],
    base: dict[str, Any],
    cache_dir: Path,
    label_panel: pd.DataFrame,
    timeseries: bool,
) -> tuple[list[dict[str, Any]], list[pd.DataFrame]]:
    rows: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    config = training_config(base, candidate)
    minimum_cross_section = int(
        base["baseline"]["minimum_daily_cross_section"]
    )
    for seed in seeds:
        set_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        model = GeneralPTNN(
            **config,
            metric="loss",
            loss="mse",
            optimizer="adam",
            n_jobs=int(base["model_attribution"]["dataloader_workers"]),
            GPU=0,
            seed=seed,
            pt_model_uri=uri,
            pt_model_kwargs={
                "num_features": 20,
                **(
                    {
                        "num_timesteps": int(
                            base["model_attribution"]["num_timesteps"]
                        )
                    }
                    if timeseries
                    else {}
                ),
            },
        )
        parameter_count = int(
            sum(parameter.numel() for parameter in model.dnn_model.parameters())
        )
        started = time.monotonic()
        model.fit(dataset)
        training_seconds = time.monotonic() - started
        row: dict[str, Any] = {
            "variant": variant,
            "seed": seed,
            "parameter_count": parameter_count,
            "training_seconds": training_seconds,
            "peak_gpu_memory_bytes": (
                int(torch.cuda.max_memory_allocated())
                if torch.cuda.is_available()
                else 0
            ),
            **{f"runtime_{key}": value for key, value in config.items()},
        }
        prediction_frames: list[pd.DataFrame] = []
        for segment in ("agent_feedback", "selection_confirmation"):
            prediction = predict_named_segment(model, dataset, segment)
            scored = label_panel[["paper_proxy"]].reindex(
                prediction.index
            )
            scored["prediction"] = prediction
            scored = scored.dropna()
            daily = daily_correlations(
                scored,
                prediction_column="prediction",
                label_column="paper_proxy",
                minimum_cross_section=minimum_cross_section,
            )
            summary = correlation_summary(daily)
            for metric, value in summary.items():
                row[f"{segment}_{metric}"] = value
            daily = daily.reset_index()
            daily["variant"] = variant
            daily["seed"] = seed
            daily["split"] = segment
            daily_parts.append(daily)
            scored["variant"] = variant
            scored["seed"] = seed
            scored["split"] = segment
            prediction_frames.append(scored)
        prediction_path = (
            cache_dir
            / f"23k_{variant}_seed_{seed}_confirmation_predictions.parquet"
        )
        pd.concat(prediction_frames).to_parquet(prediction_path)
        row["confirmation_prediction_path"] = str(prediction_path)
        row["confirmation_prediction_sha256"] = sha256_file(prediction_path)
        rows.append(row)
        del model, prediction_frames
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return rows, daily_parts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2, base = load_configs(config_path)
    output_dir = episode_root / phase2["outputs"]["model_a20"]
    candidates = pd.read_csv(output_dir / "candidate_inventory.csv")
    accepted = candidates[
        candidates["decision"].astype(str).str.lower().eq("true")
    ].copy()
    accepted = accepted.sort_values(["loop_index", "model_name"])
    provider_path = episode_root.parents[2] / base["data"]["provider_uri"]
    timeseries_dataset = build_dataset(
        base=base, phase2=phase2, provider_path=provider_path
    )
    tabular_dataset = build_dataset(
        base=base,
        phase2=phase2,
        provider_path=provider_path,
        timeseries=False,
    )
    seeds = list(map(int, phase2["benchmark"]["seeds"]))
    cache_dir = episode_root / phase2["outputs"]["local_cache"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    label_panel = pd.read_parquet(
        cache_dir / "a20_rdagent_pinned_dual_label_panel.parquet",
        columns=["paper_proxy"],
    ).sort_index()

    variants: list[tuple[str, str, pd.Series | None, bool]] = [
        (name, uri, None, True) for name, uri in BASELINES.items()
    ]
    for _, candidate in accepted.iterrows():
        code_path = output_dir / str(candidate["code_path"])
        uri, _ = register_candidate_module(
            code_path, int(candidate["loop_index"])
        )
        variants.append(
            (
                f"agent_loop_{int(candidate['loop_index']):04d}_"
                f"{candidate['model_name']}",
                uri,
                candidate,
                str(candidate["model_type"]).lower() == "timeseries",
            )
        )

    all_rows: list[dict[str, Any]] = []
    all_daily: list[pd.DataFrame] = []
    for variant, uri, candidate, timeseries in variants:
        rows, daily = evaluate_variant(
            variant=variant,
            uri=uri,
            candidate=candidate,
            dataset=timeseries_dataset if timeseries else tabular_dataset,
            seeds=seeds,
            base=base,
            cache_dir=cache_dir,
            label_panel=label_panel,
            timeseries=timeseries,
        )
        all_rows.extend(rows)
        all_daily.extend(daily)

    # Frozen LightGBM is imported from the factor confirmation that uses the
    # identical nested segments and seed set.
    factor_dir = episode_root / phase2["outputs"]["factor_a20"]
    lgb = pd.read_csv(factor_dir / "confirmation_seed_metrics.csv")
    lgb = lgb[lgb["state_id"].eq("static_base")]
    for _, row in lgb.iterrows():
        all_rows.append(
            {
                "variant": "frozen_lightgbm",
                "seed": int(row["seed"]),
                "parameter_count": np.nan,
                "training_seconds": np.nan,
                "peak_gpu_memory_bytes": 0,
                "agent_feedback_IC": row["agent_feedback_IC"],
                "agent_feedback_Rank IC": row["agent_feedback_Rank IC"],
                "agent_feedback_ICIR": row["agent_feedback_ICIR"],
                "agent_feedback_Rank ICIR": row[
                    "agent_feedback_Rank ICIR"
                ],
                "selection_confirmation_IC": row[
                    "selection_confirmation_IC"
                ],
                "selection_confirmation_Rank IC": row[
                    "selection_confirmation_Rank IC"
                ],
                "selection_confirmation_ICIR": row[
                    "selection_confirmation_ICIR"
                ],
                "selection_confirmation_Rank ICIR": row[
                    "selection_confirmation_Rank ICIR"
                ],
            }
        )

    metrics = pd.DataFrame(all_rows)
    # Use flattened MLP as the frozen parameter-scale neural control, matching
    # the EP23 23D preregistration.
    capacity = metrics[metrics["variant"].eq("flattened_mlp")].copy()
    capacity["variant"] = "capacity_matched_neural_baseline"
    metrics = pd.concat([metrics, capacity], ignore_index=True)
    metrics.to_csv(
        output_dir / "confirmation_seed_metrics.csv", index=False
    )
    pd.concat(all_daily, ignore_index=True).to_csv(
        output_dir / "confirmation_daily_metrics.csv", index=False
    )

    candidate_variants = [
        name
        for name, _, _, _ in variants
        if name.startswith("agent_loop_")
    ]
    attribution_rows: list[dict[str, Any]] = []
    baseline_variants = [
        "frozen_lightgbm",
        "flattened_mlp",
        "last_state_gru",
        "attentive_gru",
        "capacity_matched_neural_baseline",
    ]
    indexed = metrics.set_index(["variant", "seed"])
    for candidate_variant in candidate_variants:
        for baseline_variant in baseline_variants:
            for seed in seeds:
                for segment in (
                    "agent_feedback",
                    "selection_confirmation",
                ):
                    for metric in ("IC", "Rank IC"):
                        column = f"{segment}_{metric}"
                        baseline_value = float(
                            indexed.loc[(baseline_variant, seed), column]
                        )
                        candidate_value = float(
                            indexed.loc[(candidate_variant, seed), column]
                        )
                        attribution_rows.append(
                            {
                                "candidate_variant": candidate_variant,
                                "baseline_variant": baseline_variant,
                                "seed": seed,
                                "split": segment,
                                "metric": metric,
                                "baseline_value": baseline_value,
                                "candidate_value": candidate_value,
                                "delta": candidate_value - baseline_value,
                            }
                        )
    attribution = pd.DataFrame(attribution_rows)
    attribution.to_csv(
        output_dir / "matched_model_attribution.csv", index=False
    )

    annual_daily = pd.concat(all_daily, ignore_index=True)
    annual_daily["year"] = pd.to_datetime(
        annual_daily["datetime"]
    ).dt.year
    annual = (
        annual_daily.groupby(
            ["variant", "seed", "split", "year"], as_index=False
        )
        .agg(IC=("ic", "mean"), Rank_IC=("rank_ic", "mean"))
    )
    annual.to_csv(output_dir / "annual_metrics.csv", index=False)

    candidate_verdicts: list[dict[str, Any]] = []
    for candidate_variant in candidate_variants:
        candidate_attrs = attribution[
            attribution["candidate_variant"].eq(candidate_variant)
            & attribution["baseline_variant"].eq(
                "capacity_matched_neural_baseline"
            )
        ]
        stats: dict[str, Any] = {}
        confirmation_passes = []
        feedback_positive = False
        for segment in ("agent_feedback", "selection_confirmation"):
            for metric in ("IC", "Rank IC"):
                values = candidate_attrs[
                    candidate_attrs["split"].eq(segment)
                    & candidate_attrs["metric"].eq(metric)
                ]["delta"]
                key = f"{segment}_{metric.replace(' ', '_').lower()}"
                stats[f"{key}_delta_median"] = float(values.median())
                stats[f"{key}_positive_seeds"] = int(values.gt(0).sum())
                if segment == "agent_feedback":
                    feedback_positive = feedback_positive or bool(
                        values.median() > 0
                    )
                else:
                    confirmation_passes.append(
                        bool(values.median() > 0 and values.gt(0).sum() >= 4)
                    )
        confirmation_positive = any(confirmation_passes)
        candidate_verdicts.append(
            {
                "candidate_variant": candidate_variant,
                **stats,
                "feedback_improvement": feedback_positive,
                "confirmation_4_of_5_improvement": confirmation_positive,
                "no_feedback_confirmation_sign_reversal": (
                    feedback_positive and confirmation_positive
                ),
                "predictive_model_pass": (
                    feedback_positive and confirmation_positive
                ),
            }
        )
    candidate_verdict_frame = pd.DataFrame(candidate_verdicts)
    candidate_verdict_frame.to_csv(
        output_dir / "candidate_verdicts.csv", index=False
    )
    predictive_pass = bool(
        len(candidate_verdict_frame)
        and candidate_verdict_frame["predictive_model_pass"].any()
    )
    selected_candidates = (
        candidate_verdict_frame[
            candidate_verdict_frame["predictive_model_pass"]
        ]["candidate_variant"].tolist()
        if predictive_pass
        else []
    )
    verdict = {
        "intermediate_verdict": (
            "predictive_model_evolution_candidate"
            if predictive_pass
            else "no_predictive_model_evolution"
        ),
        "predictive_model_pass": predictive_pass,
        "selected_candidate_variants": selected_candidates,
        "accepted_agent_model_count": len(candidate_variants),
        "historical_test_read": False,
        "next_open_economic_gate_pending_23l": True,
    }
    (output_dir / "verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
