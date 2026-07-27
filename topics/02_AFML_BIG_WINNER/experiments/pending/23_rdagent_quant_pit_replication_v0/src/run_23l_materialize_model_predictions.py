#!/usr/bin/env python3
"""Retrain the frozen 23K model pair and reveal 23L historical-test scores."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import pandas as pd
import torch
from qlib.contrib.model.pytorch_general_nn import GeneralPTNN

from ep23_phase2_common import load_configs, sha256_file
from run_23k_matched_model_confirmation import (
    build_dataset,
    predict_named_segment,
    register_candidate_module,
    set_seed,
    training_config,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    episode_root = config_path.parent
    phase2, base = load_configs(config_path)
    model_dir = episode_root / phase2["outputs"]["model_a20"]
    verdict = json.loads(
        (model_dir / "verdict.json").read_text(encoding="utf-8")
    )
    if not verdict.get("predictive_model_pass"):
        pd.DataFrame(
            columns=[
                "state_id",
                "seed",
                "prediction_path",
                "prediction_sha256",
                "historical_test_read",
            ]
        ).to_csv(model_dir / "23l_prediction_inventory.csv", index=False)
        print(
            json.dumps(
                {
                    "status": "not_run_by_predictive_model_gate",
                    "historical_test_read": False,
                },
                indent=2,
            )
        )
        return

    confirmation = pd.read_csv(model_dir / "confirmation_seed_metrics.csv")
    passed = set(verdict["selected_candidate_variants"])
    candidate_scores = (
        confirmation[confirmation["variant"].isin(passed)]
        .groupby("variant")["selection_confirmation_IC"]
        .median()
        .sort_values(ascending=False)
    )
    selected_variant = str(candidate_scores.index[0])
    loop_index = int(selected_variant.split("_")[2])
    candidates = pd.read_csv(model_dir / "candidate_inventory.csv")
    candidate = candidates[
        candidates["loop_index"].astype(int).eq(loop_index)
    ].iloc[0]
    candidate_uri, _ = register_candidate_module(
        model_dir / str(candidate["code_path"]), loop_index
    )
    candidate_timeseries = (
        str(candidate["model_type"]).lower() == "timeseries"
    )
    variants = [
        (
            "a20_model_baseline",
            "ep23_model_variants.FlattenedWindowMLP",
            None,
            True,
        ),
        (
            "a20_model_evolved",
            candidate_uri,
            candidate,
            candidate_timeseries,
        ),
    ]

    provider_path = episode_root.parents[2] / base["data"]["provider_uri"]
    timeseries_dataset = build_dataset(
        base=base,
        phase2=phase2,
        provider_path=provider_path,
        end_segment="historical_test",
    )
    tabular_dataset = build_dataset(
        base=base,
        phase2=phase2,
        provider_path=provider_path,
        end_segment="historical_test",
        timeseries=False,
    )
    label_panel = pd.read_parquet(
        episode_root
        / phase2["outputs"]["local_cache"]
        / "a20_rdagent_pinned_dual_label_panel.parquet",
        columns=["paper_proxy", "executable_bridge"],
    ).sort_index()
    seeds = list(map(int, phase2["benchmark"]["seeds"]))
    cache_dir = episode_root / phase2["outputs"]["local_cache"]
    inventory = []
    for state_id, uri, candidate_row, timeseries in variants:
        dataset = (
            timeseries_dataset if timeseries else tabular_dataset
        )
        train_config = training_config(base, candidate_row)
        for seed in seeds:
            set_seed(seed)
            model = GeneralPTNN(
                **train_config,
                metric="loss",
                loss="mse",
                optimizer="adam",
                n_jobs=int(
                    base["model_attribution"]["dataloader_workers"]
                ),
                GPU=0,
                seed=seed,
                pt_model_uri=uri,
                pt_model_kwargs={
                    "num_features": 20,
                    **(
                        {
                            "num_timesteps": int(
                                base["model_attribution"][
                                    "num_timesteps"
                                ]
                            )
                        }
                        if timeseries
                        else {}
                    ),
                },
            )
            model.fit(dataset)
            score_parts = []
            for segment in (
                "selection_confirmation",
                "historical_test",
            ):
                prediction = predict_named_segment(
                    model, dataset, segment
                )
                labels = label_panel.reindex(prediction.index)
                scored = labels.copy()
                scored["prediction"] = prediction
                scored["split"] = segment
                scored["state_id"] = state_id
                scored["seed"] = seed
                score_parts.append(scored)
            scores = pd.concat(score_parts).sort_index()
            path = (
                cache_dir
                / f"23l_{state_id}_seed_{seed}_predictions.parquet"
            )
            scores.to_parquet(path)
            inventory.append(
                {
                    "state_id": state_id,
                    "seed": seed,
                    "selected_23k_candidate_variant": selected_variant,
                    "candidate_loop_index": (
                        loop_index
                        if state_id == "a20_model_evolved"
                        else None
                    ),
                    "runtime_training_config_json": json.dumps(
                        train_config, sort_keys=True
                    ),
                    "prediction_path": str(path.relative_to(episode_root)),
                    "prediction_sha256": sha256_file(path),
                    "frozen_before_historical_test_read": True,
                    "historical_test_read": True,
                }
            )
            del model, scores, score_parts
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    pd.DataFrame(inventory).to_csv(
        model_dir / "23l_prediction_inventory.csv", index=False
    )
    print(
        json.dumps(
            {
                "status": "complete",
                "selected_candidate_variant": selected_variant,
                "prediction_artifact_count": len(inventory),
                "historical_test_read": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
