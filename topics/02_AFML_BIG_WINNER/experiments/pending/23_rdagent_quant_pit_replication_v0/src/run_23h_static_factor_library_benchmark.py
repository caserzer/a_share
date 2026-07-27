#!/usr/bin/env python3
"""EP23 Phase 2 matched static factor-library benchmark."""

from __future__ import annotations

import argparse
import gc
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml

from ep23_phase2_common import (
    canonical_json_sha256,
    get_library_definitions,
    library_hashes,
    load_configs,
    materialize_library,
    sha256_file,
)
from run_23b_alpha20_lgbm_baseline import (
    apply_robust_transform,
    correlation_summary,
    cross_sectional_zscore,
    daily_correlations,
    fit_robust_transform,
    portfolio_summary,
    topk_dropout_returns,
)


def load_or_materialize(
    *,
    cache_path: Path,
    provider_path: Path,
    market: str,
    library: dict[str, Any],
    labels: dict[str, str],
    start_time: str,
    end_time: str,
) -> pd.DataFrame:
    expected_columns = [*library["names"], *labels]
    if cache_path.exists():
        frame = pd.read_parquet(cache_path)
        frame.index = frame.index.set_names(["datetime", "instrument"])
        if list(frame.columns) == expected_columns:
            return frame.sort_index()
    frame = materialize_library(
        provider_path=provider_path,
        market=market,
        library=library,
        labels=labels,
        start_time=start_time,
        end_time=end_time,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(cache_path)
    return frame


def quality_metrics(
    library_id: str,
    train_features: pd.DataFrame,
    *,
    sample_rows: int = 50_000,
) -> dict[str, Any]:
    finite_ratio = train_features.notna().mean()
    unique_count = train_features.nunique(dropna=True)
    usable = [
        name
        for name in train_features
        if finite_ratio[name] > 0 and unique_count[name] > 1
    ]
    sampled = train_features[usable]
    if len(sampled) > sample_rows:
        sampled = sampled.sample(n=sample_rows, random_state=20260727)
    sampled = sampled.replace([np.inf, -np.inf], np.nan)
    corr = sampled.corr(min_periods=100).fillna(0.0)
    if len(corr):
        np.fill_diagonal(corr.values, 1.0)
        eigenvalues = np.linalg.eigvalsh(corr.to_numpy(dtype=float))
        eigenvalues = np.clip(eigenvalues, 0.0, None)
        weights = eigenvalues / eigenvalues.sum() if eigenvalues.sum() > 0 else eigenvalues
        weights = weights[weights > 0]
        effective_rank = (
            float(np.exp(-(weights * np.log(weights)).sum()))
            if len(weights)
            else math.nan
        )
        upper = np.abs(corr.to_numpy()[np.triu_indices(len(corr), k=1)])
        high_corr_pairs = int((upper >= 0.99).sum())
        median_abs_corr = float(np.median(upper)) if len(upper) else 0.0
        max_abs_corr = float(np.max(upper)) if len(upper) else 0.0
        adjacency = np.abs(corr.to_numpy(dtype=float)) >= 0.70
        visited: set[int] = set()
        correlation_cluster_count = 0
        for node in range(len(corr)):
            if node in visited:
                continue
            correlation_cluster_count += 1
            stack = [node]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                stack.extend(
                    int(neighbor)
                    for neighbor in np.flatnonzero(adjacency[current])
                    if int(neighbor) not in visited
                )
    else:
        effective_rank = math.nan
        high_corr_pairs = 0
        median_abs_corr = math.nan
        max_abs_corr = math.nan
        correlation_cluster_count = 0
    return {
        "library_id": library_id,
        "nominal_feature_count": int(train_features.shape[1]),
        "usable_feature_count": len(usable),
        "empty_feature_count": int((finite_ratio == 0).sum()),
        "constant_or_empty_feature_count": int((unique_count <= 1).sum()),
        "minimum_feature_finite_ratio": float(finite_ratio.min()),
        "median_feature_finite_ratio": float(finite_ratio.median()),
        "correlation_sample_rows": int(len(sampled)),
        "effective_rank": effective_rank,
        "effective_rank_per_feature": (
            effective_rank / len(usable) if usable and np.isfinite(effective_rank) else math.nan
        ),
        "abs_corr_ge_0_99_pairs": high_corr_pairs,
        "median_abs_pairwise_corr": median_abs_corr,
        "max_abs_pairwise_corr": max_abs_corr,
        "correlation_cluster_threshold": 0.70,
        "correlation_cluster_count": correlation_cluster_count,
    }


def annual_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    frame = daily.copy()
    frame["year"] = pd.to_datetime(frame["datetime"]).dt.year
    rows = []
    for keys, group in frame.groupby(
        ["library_id", "seed", "split", "label_lane", "year"], sort=True
    ):
        library_id, seed, split, lane, year = keys
        summary = correlation_summary(group.set_index("datetime")[["ic", "rank_ic"]])
        rows.append(
            {
                "library_id": library_id,
                "seed": seed,
                "split": split,
                "label_lane": lane,
                "year": year,
                **summary,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--libraries",
        help="optional comma-separated registered library IDs",
    )
    parser.add_argument(
        "--seeds",
        help="optional comma-separated seeds; default is frozen five",
    )
    args = parser.parse_args()

    started = time.monotonic()
    phase2_path = Path(args.config).resolve()
    episode_root = phase2_path.parent
    phase2, base = load_configs(phase2_path)
    topic_root = episode_root.parents[2]
    output_dir = episode_root / phase2["outputs"]["benchmark"]
    cache_dir = episode_root / phase2["outputs"]["local_cache"]
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    preflight_path = (
        episode_root / phase2["outputs"]["preflight"] / "preflight_verdict.json"
    )
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight["ready_for_primary_static_benchmark"]:
        raise RuntimeError("23G did not authorize 23H")

    library_ids = (
        [item.strip() for item in args.libraries.split(",") if item.strip()]
        if args.libraries
        else list(phase2["benchmark"]["libraries"])
    )
    seeds = (
        [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
        if args.seeds
        else list(phase2["benchmark"]["seeds"])
    )
    definitions = get_library_definitions(base)
    unknown = sorted(set(library_ids) - set(definitions))
    if unknown:
        raise ValueError(f"unknown library IDs: {unknown}")

    labels = {
        name: base["labels"][name]["expression"]
        for name in ["paper_proxy", "executable_bridge"]
    }
    provider_path = topic_root / base["data"]["provider_uri"]
    split_names = ["train", "validation", "historical_test"]
    lgb_params = dict(base["baseline"]["lightgbm"])
    clip = float(base["baseline"]["robust_zscore_clip"])
    early_stopping_rounds = int(base["baseline"]["early_stopping_rounds"])
    minimum_cross_section = int(base["baseline"]["minimum_daily_cross_section"])

    seed_rows: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    portfolio_parts: list[pd.DataFrame] = []
    importance_parts: list[pd.DataFrame] = []
    normalization_parts: list[pd.DataFrame] = []
    inventory_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    prediction_paths: list[str] = []

    for library_id in library_ids:
        library_started = time.monotonic()
        library = definitions[library_id]
        names = list(library["names"])
        cache_path = cache_dir / f"{library_id.lower()}_dual_label_panel.parquet"
        frame = load_or_materialize(
            cache_path=cache_path,
            provider_path=provider_path,
            market=base["data"]["market"],
            library=library,
            labels=labels,
            start_time=base["data"]["expected_calendar_start"],
            end_time=base["data"]["expected_calendar_end"],
        )
        split_frames: dict[str, pd.DataFrame] = {}
        for split_name in split_names:
            start, end = base["split"][split_name]
            part = frame.loc[
                (slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :
            ].copy()
            part = part[part["paper_proxy"].notna()]
            split_frames[split_name] = part
            dates = part.index.get_level_values("datetime")
            inventory_rows.append(
                {
                    "library_id": library_id,
                    "split": split_name,
                    "rows": len(part),
                    "dates": dates.nunique(),
                    "instruments": part.index.get_level_values(
                        "instrument"
                    ).nunique(),
                    "date_start": dates.min().date().isoformat(),
                    "date_end": dates.max().date().isoformat(),
                    "feature_count": len(names),
                    "finite_ratio": float(
                        part[names].notna().to_numpy().mean()
                    ),
                }
            )
        quality_rows.append(
            quality_metrics(library_id, split_frames["train"][names])
        )
        median, scale = fit_robust_transform(
            split_frames["train"][names], clip=clip
        )
        normalization_parts.append(
            pd.DataFrame(
                {
                    "library_id": library_id,
                    "feature": names,
                    "train_median": median.reindex(names).values,
                    "train_scale": scale.reindex(names).values,
                }
            )
        )
        transformed = {
            split_name: apply_robust_transform(
                part[names], median, scale, clip
            )
            for split_name, part in split_frames.items()
        }
        targets = {
            split_name: cross_sectional_zscore(part["paper_proxy"])
            for split_name, part in split_frames.items()
        }
        train_mask = targets["train"].notna()
        valid_mask = targets["validation"].notna()
        X_train = transformed["train"].loc[train_mask]
        y_train = targets["train"].loc[train_mask].astype("float32")
        X_valid = transformed["validation"].loc[valid_mask]
        y_valid = targets["validation"].loc[valid_mask].astype("float32")

        for seed in seeds:
            model_params = {
                **lgb_params,
                "random_state": seed,
                "bagging_seed": seed,
                "feature_fraction_seed": seed,
                "data_random_seed": seed,
                "verbosity": -1,
            }
            model = lgb.LGBMRegressor(**model_params)
            model.fit(
                X_train,
                y_train,
                eval_set=[(X_valid, y_valid)],
                eval_metric="l2",
                callbacks=[
                    lgb.early_stopping(early_stopping_rounds, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            seed_summary: dict[str, Any] = {
                "library_id": library_id,
                "seed": seed,
                "best_iteration": int(
                    model.best_iteration_ or model.n_estimators
                ),
            }
            prediction_parts = []
            for split_name in ["validation", "historical_test"]:
                scored = split_frames[split_name][
                    ["paper_proxy", "executable_bridge"]
                ].copy()
                scored["prediction"] = model.predict(
                    transformed[split_name],
                    num_iteration=model.best_iteration_,
                )
                scored["library_id"] = library_id
                scored["split"] = split_name
                scored["seed"] = seed
                prediction_parts.append(scored)
                for label_name in labels:
                    daily = daily_correlations(
                        scored,
                        prediction_column="prediction",
                        label_column=label_name,
                        minimum_cross_section=minimum_cross_section,
                    )
                    summary = correlation_summary(daily)
                    prefix = f"{split_name}_{label_name}"
                    seed_summary.update(
                        {
                            f"{prefix}_{key}": value
                            for key, value in summary.items()
                        }
                    )
                    daily = daily.reset_index()
                    daily["library_id"] = library_id
                    daily["split"] = split_name
                    daily["label_lane"] = label_name
                    daily["seed"] = seed
                    daily_parts.append(daily)

                if split_name == "historical_test":
                    for label_name in labels:
                        portfolio = topk_dropout_returns(
                            scored,
                            prediction_column="prediction",
                            label_column=label_name,
                            topk=int(base["portfolio"]["topk"]),
                            n_drop=int(base["portfolio"]["n_drop"]),
                            buy_cost=float(base["portfolio"]["buy_cost"]),
                            sell_cost=float(base["portfolio"]["sell_cost"]),
                        )
                        summary = portfolio_summary(
                            portfolio,
                            int(base["portfolio"]["annualization"]),
                        )
                        seed_summary.update(
                            {
                                f"historical_test_{label_name}_{key}": value
                                for key, value in summary.items()
                            }
                        )
                        portfolio = portfolio.reset_index()
                        portfolio["library_id"] = library_id
                        portfolio["label_lane"] = label_name
                        portfolio["seed"] = seed
                        portfolio_parts.append(portfolio)

            predictions = pd.concat(prediction_parts).sort_index()
            prediction_path = (
                cache_dir
                / f"{library_id.lower()}_lgbm_seed_{seed}_predictions.parquet"
            )
            predictions.to_parquet(prediction_path)
            prediction_paths.append(str(prediction_path.relative_to(episode_root)))
            seed_summary["library_elapsed_seconds_at_seed_end"] = (
                time.monotonic() - library_started
            )
            seed_rows.append(seed_summary)
            importance_parts.append(
                pd.DataFrame(
                    {
                        "library_id": library_id,
                        "feature": names,
                        "gain": model.booster_.feature_importance(
                            importance_type="gain"
                        ),
                        "split_count": model.booster_.feature_importance(
                            importance_type="split"
                        ),
                        "seed": seed,
                    }
                )
            )
            del model, predictions
            gc.collect()
        del frame, split_frames, transformed, X_train, X_valid, y_train, y_valid
        gc.collect()

    seed_metrics = pd.DataFrame(seed_rows).sort_values(["library_id", "seed"])
    seed_metrics.to_csv(output_dir / "seed_metrics.csv", index=False)
    daily = pd.concat(daily_parts, ignore_index=True)
    daily.to_csv(output_dir / "daily_predictive_metrics.csv", index=False)
    annual_metrics(daily).to_csv(
        output_dir / "annual_predictive_metrics.csv", index=False
    )
    pd.concat(portfolio_parts, ignore_index=True).to_csv(
        output_dir / "portfolio_daily.csv", index=False
    )
    pd.concat(importance_parts, ignore_index=True).to_csv(
        output_dir / "feature_importance.csv", index=False
    )
    pd.concat(normalization_parts, ignore_index=True).to_csv(
        output_dir / "train_only_normalization.csv", index=False
    )
    pd.DataFrame(inventory_rows).to_csv(
        output_dir / "library_materialization_inventory.csv", index=False
    )
    quality = pd.DataFrame(quality_rows).sort_values("library_id")
    quality.to_csv(output_dir / "library_quality_metrics.csv", index=False)

    numeric_columns = [
        column
        for column in seed_metrics.select_dtypes(include=[np.number]).columns
        if column != "seed"
    ]
    summary = (
        seed_metrics.groupby("library_id")[numeric_columns]
        .median()
        .reset_index()
    )
    summary["completed_seed_count"] = (
        seed_metrics.groupby("library_id")["seed"]
        .nunique()
        .reindex(summary["library_id"])
        .to_numpy()
    )
    summary = summary.merge(quality, on="library_id", how="left")
    summary["validation_ic_per_usable_factor"] = (
        summary["validation_paper_proxy_ic"]
        / summary["usable_feature_count"]
    )
    summary["historical_test_net_arr_per_usable_factor"] = (
        summary["historical_test_paper_proxy_net_arr"]
        / summary["usable_feature_count"]
    )
    summary.to_csv(output_dir / "library_summary.csv", index=False)

    baseline = seed_metrics[
        seed_metrics["library_id"] == "A20_RDAGENT_PINNED"
    ].set_index("seed")
    delta_parts = []
    for library_id in library_ids:
        current = seed_metrics[
            seed_metrics["library_id"] == library_id
        ].set_index("seed")
        common = sorted(set(baseline.index) & set(current.index))
        for seed in common:
            row = {"library_id": library_id, "seed": seed}
            for column in numeric_columns:
                if column in current and column in baseline:
                    row[f"delta_{column}"] = float(
                        current.at[seed, column] - baseline.at[seed, column]
                    )
            delta_parts.append(row)
    deltas = pd.DataFrame(delta_parts)
    deltas.to_csv(output_dir / "matched_seed_deltas_vs_a20.csv", index=False)

    selected_library = (
        summary.sort_values(
            ["validation_paper_proxy_ic", "library_id"],
            ascending=[False, True],
        )
        .iloc[0]["library_id"]
    )
    completed_five = bool(
        (summary["completed_seed_count"] == len(phase2["benchmark"]["seeds"])).all()
    )
    empty_retained = int(quality["empty_feature_count"].sum())

    phase1_seed_path = (
        topic_root
        / base["outputs"]["baseline"]
        / "seed_metrics.csv"
    )
    phase1_seed = pd.read_csv(phase1_seed_path).set_index("seed")
    phase2_a20 = baseline
    reconcile_columns = [
        "validation_paper_proxy_ic",
        "historical_test_paper_proxy_ic",
        "historical_test_paper_proxy_rank_ic",
        "historical_test_paper_proxy_net_arr",
    ]
    reconcile_max_abs = 0.0
    reconcile_ok = True
    reconcile_common_seeds = sorted(
        set(phase2_a20.index) & set(phase1_seed.index)
    )
    if "A20_RDAGENT_PINNED" in library_ids and reconcile_common_seeds:
        for column in reconcile_columns:
            current = phase2_a20.loc[
                reconcile_common_seeds, column
            ].to_numpy(dtype=float)
            reference = phase1_seed.loc[
                reconcile_common_seeds, column
            ].to_numpy(dtype=float)
            values = np.abs(current - reference)
            reconcile_max_abs = max(reconcile_max_abs, float(values.max()))
            reconcile_ok = reconcile_ok and bool(
                np.isclose(
                    current,
                    reference,
                    rtol=1e-6,
                    atol=5e-7,
                    equal_nan=True,
                ).all()
            )
    elif "A20_RDAGENT_PINNED" in library_ids:
        reconcile_ok = False

    gates = {
        "preflight_authorized": True,
        "all_registered_libraries_materialized": len(quality) == len(library_ids),
        "formal_five_seed_complete": completed_five,
        "no_empty_retained_feature": empty_retained == 0,
        "alpha20_reconciliation": reconcile_ok,
        "validation_only_library_selection": True,
    }
    passed = all(gates.values())
    terminal_state = (
        "static_library_benchmark_complete"
        if passed
        else "static_library_benchmark_failed_gate"
    )
    verdict = {
        "stage": "23H_static_factor_library_benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "terminal_state": terminal_state,
        "gates": gates,
        "selected_library_by_validation_median_ic": str(selected_library),
        "selection_rule": "maximum five-seed median validation PAPER_PROXY IC; lexical tie break",
        "alpha20_reconciliation_max_abs_difference": reconcile_max_abs,
        "alpha20_reconciliation_common_seeds": reconcile_common_seeds,
        "exact_library_blockers_inherited": {
            "A158_QLIB_PINNED": "replication_blocked_by_missing_vwap",
            "A360_QLIB_PINNED": "replication_blocked_by_missing_vwap",
            "A101_CANONICAL_REBUILT": "A101_REPLICATION_BLOCKED",
            "AUTOALPHA_EXACT_ARTIFACT": "AUTOALPHA_DEFINITION_BLOCKED",
        },
        "deployment_authorized": False,
    }
    (output_dir / "verdict.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    resolved = {
        "phase2_config": phase2,
        "base_config_sha256": sha256_file(
            episode_root / phase2["base_config"]
        ),
        "phase2_config_sha256": sha256_file(phase2_path),
        "library_hashes": {
            library_id: library_hashes(definitions[library_id])
            for library_id in library_ids
        },
        "library_ids": library_ids,
        "seeds": seeds,
    }
    (output_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(resolved, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    manifest = {
        "episode_id": phase2["episode_id"],
        "stage": "23H_static_factor_library_benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "library_ids": library_ids,
        "seeds": seeds,
        "prediction_paths": prediction_paths,
        "selected_library_by_validation_median_ic": str(selected_library),
        "input_contract_sha256": canonical_json_sha256(resolved),
        "elapsed_seconds": time.monotonic() - started,
        "evidence_class": base["split"]["evidence_class"],
        "claim_ceiling": "static_registered_library_comparison_complete",
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    display_columns = [
        "library_id",
        "usable_feature_count",
        "validation_paper_proxy_ic",
        "validation_paper_proxy_rank_ic",
        "historical_test_paper_proxy_ic",
        "historical_test_paper_proxy_rank_ic",
        "historical_test_paper_proxy_net_arr",
        "historical_test_executable_bridge_net_arr",
        "historical_test_paper_proxy_mean_one_way_turnover",
        "effective_rank",
    ]
    table = summary[display_columns].to_markdown(index=False, floatfmt=".6f")
    report = f"""# EP23 23H 静态多因子库 Matched Benchmark

## 裁决

```text
terminal_state = {terminal_state}
selected_library_by_validation_median_ic = {selected_library}
evidence = {base["split"]["evidence_class"]}
deployment_authorized = false
```

## 五 seed 中位数

{table}

## 关键解释

- 所有 headline 都是五 seed 中位数；没有用 historical test 选择 library。
- A157/A300 是显式 no-VWAP adaptation，不是完整 Alpha158/Alpha360。
- 完整 Alpha158/360、Alpha101 和 AutoAlpha 维持 23G blocked 裁决。
- 本阶段只说明静态信息集差异，不证明 RD-Agent 进化有效。
- Alpha20 与 23B 的最大绝对复现差为 `{reconcile_max_abs:.3e}`。

运行耗时：`{manifest["elapsed_seconds"]:.2f}` 秒。
"""
    (output_dir / "23H_static_factor_library_benchmark_report.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print(summary[display_columns].to_string(index=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
