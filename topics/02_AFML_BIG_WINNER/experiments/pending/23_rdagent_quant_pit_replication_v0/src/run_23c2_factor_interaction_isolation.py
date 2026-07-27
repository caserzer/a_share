#!/usr/bin/env python3
"""Post-hoc interaction isolation for the four RD-Agent Loop-0 factors."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from run_23b_alpha20_lgbm_baseline import (
    cross_sectional_zscore,
    find_topic_root,
    load_or_materialize,
    parse_seed_override,
    sha256_file,
)
from run_23c1_controlled_factor_ablation import (
    FACTOR_NAMES,
    build_comparison,
    evaluate_variant,
    load_factor_panel,
    resolve_factor_panel,
)

MOMENTUM = "close_momentum_20d"
REVERSAL = "close_reversal_5d"
CLOSE_LOCATION = "daily_close_location_value"
VOLUME = "volume_surprise_20d"

VARIANTS = {
    "alpha20": [],
    "plus_momentum": [MOMENTUM],
    "plus_volume": [VOLUME],
    "plus_momentum_volume": [MOMENTUM, VOLUME],
    "plus_core_reversal": [MOMENTUM, REVERSAL, VOLUME],
    "plus_core_close_location": [MOMENTUM, CLOSE_LOCATION, VOLUME],
    "plus_all_four": FACTOR_NAMES,
}

CONTRASTS = {
    "volume_given_momentum": ("plus_momentum_volume", "plus_momentum"),
    "momentum_given_volume": ("plus_momentum_volume", "plus_volume"),
    "reversal_given_core": ("plus_core_reversal", "plus_momentum_volume"),
    "close_location_given_core": (
        "plus_core_close_location",
        "plus_momentum_volume",
    ),
    "both_weak_factors_given_core": (
        "plus_all_four",
        "plus_momentum_volume",
    ),
    "close_location_given_core_reversal": (
        "plus_all_four",
        "plus_core_reversal",
    ),
    "reversal_given_core_close_location": (
        "plus_all_four",
        "plus_core_close_location",
    ),
}

CONTRAST_METRICS = [
    "validation_paper_proxy_ic",
    "validation_executable_bridge_ic",
    "historical_test_paper_proxy_ic",
    "historical_test_executable_bridge_ic",
    "historical_test_paper_proxy_net_arr",
    "historical_test_executable_bridge_net_arr",
]


def build_contrasts(
    seed_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    indexed = seed_metrics.set_index(["variant", "seed"])
    rows = []
    for contrast, (current_name, reference_name) in CONTRASTS.items():
        current = indexed.loc[current_name]
        reference = indexed.loc[reference_name]
        for seed in sorted(set(current.index) & set(reference.index)):
            for metric in CONTRAST_METRICS:
                current_value = float(current.loc[seed, metric])
                reference_value = float(reference.loc[seed, metric])
                rows.append(
                    {
                        "contrast": contrast,
                        "current_variant": current_name,
                        "reference_variant": reference_name,
                        "seed": int(seed),
                        "metric": metric,
                        "current": current_value,
                        "reference": reference_value,
                        "delta": current_value - reference_value,
                    }
                )
    deltas = pd.DataFrame(rows)
    summary = (
        deltas.groupby(
            [
                "contrast",
                "current_variant",
                "reference_variant",
                "metric",
            ],
            sort=False,
        )["delta"]
        .agg(
            positive_seed_count=lambda values: int((values > 0).sum()),
            seed_count="count",
            median_paired_delta="median",
            min_paired_delta="min",
            max_paired_delta="max",
        )
        .reset_index()
    )
    return deltas, summary


def audit_prior_all_four(
    topic_root: Path,
    config: dict[str, Any],
    seed_metrics: pd.DataFrame,
) -> dict[str, Any]:
    prior_path = (
        topic_root
        / config["outputs"]["factor_ablation"]
        / "seed_metrics.csv"
    )
    if not prior_path.is_file():
        return {"status": "not_available", "prior_path": str(prior_path)}
    prior = pd.read_csv(prior_path)
    prior = (
        prior[prior["variant"] == "plus_all_four"]
        .sort_values("seed")
        .reset_index(drop=True)
    )
    current = (
        seed_metrics[seed_metrics["variant"] == "plus_all_four"]
        .sort_values("seed")
        .reset_index(drop=True)
    )
    numeric_columns = sorted(
        (
            set(prior.select_dtypes(include=[np.number]).columns)
            & set(current.select_dtypes(include=[np.number]).columns)
        )
        - {"seed"}
    )
    prior_values = prior[numeric_columns].to_numpy(dtype="float64")
    current_values = current[numeric_columns].to_numpy(dtype="float64")
    max_abs_diff = float(
        np.nanmax(np.abs(prior_values - current_values))
    )
    passed = bool(
        np.allclose(
            prior_values,
            current_values,
            rtol=1e-6,
            atol=1e-8,
            equal_nan=True,
        )
    )
    return {
        "status": "passed" if passed else "failed",
        "prior_path": str(prior_path),
        "rtol": 1e-6,
        "atol": 1e-8,
        "max_abs_diff": max_abs_diff,
        "numeric_metric_count": len(numeric_columns),
    }


def render_report(
    comparison: pd.DataFrame,
    contrast_summary: pd.DataFrame,
    reproduction_audit: dict[str, Any],
    elapsed: float,
) -> str:
    def variant_value(
        variant: str, metric: str, column: str = "median"
    ) -> float:
        return float(
            comparison[
                (comparison["variant"] == variant)
                & (comparison["metric"] == metric)
            ].iloc[0][column]
        )

    def contrast_value(
        contrast: str, metric: str, column: str
    ) -> float:
        return float(
            contrast_summary[
                (contrast_summary["contrast"] == contrast)
                & (contrast_summary["metric"] == metric)
            ].iloc[0][column]
        )

    variant_rows = []
    for variant in VARIANTS:
        variant_rows.append(
            "| {variant} | {paper_ic:.6f} | {paper_arr:.4%} | "
            "{exec_ic:.6f} | {exec_arr:.4%} |".format(
                variant=variant,
                paper_ic=variant_value(
                    variant, "historical_test_paper_proxy_ic"
                ),
                paper_arr=variant_value(
                    variant, "historical_test_paper_proxy_net_arr"
                ),
                exec_ic=variant_value(
                    variant, "historical_test_executable_bridge_ic"
                ),
                exec_arr=variant_value(
                    variant,
                    "historical_test_executable_bridge_net_arr",
                ),
            )
        )

    contrast_rows = []
    for contrast in CONTRASTS:
        paper_count = int(
            contrast_value(
                contrast,
                "historical_test_paper_proxy_net_arr",
                "positive_seed_count",
            )
        )
        paper_delta = contrast_value(
            contrast,
            "historical_test_paper_proxy_net_arr",
            "median_paired_delta",
        )
        exec_count = int(
            contrast_value(
                contrast,
                "historical_test_executable_bridge_net_arr",
                "positive_seed_count",
            )
        )
        exec_delta = contrast_value(
            contrast,
            "historical_test_executable_bridge_net_arr",
            "median_paired_delta",
        )
        contrast_rows.append(
            f"| {contrast} | {paper_count}/5 | {paper_delta:+.4%} | "
            f"{exec_count}/5 | {exec_delta:+.4%} |"
        )

    core_paper = variant_value(
        "plus_momentum_volume", "historical_test_paper_proxy_net_arr"
    )
    core_exec = variant_value(
        "plus_momentum_volume",
        "historical_test_executable_bridge_net_arr",
    )
    all_paper_delta = contrast_value(
        "both_weak_factors_given_core",
        "historical_test_paper_proxy_net_arr",
        "median_paired_delta",
    )
    all_exec_delta = contrast_value(
        "both_weak_factors_given_core",
        "historical_test_executable_bridge_net_arr",
        "median_paired_delta",
    )

    return f"""# EP23 23C2 Factor Interaction Isolation

## 裁决

```text
core = close_momentum_20d + volume_surprise_20d
comparison = add reversal / add close-location / add both
seeds = 5 matched seeds
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = posthoc_factor_interaction_diagnostic
```

本阶段沿用 23C1 的统一 preprocessing、split、LightGBM、Top50/drop5 和费用，
只改变四个 RD-Agent 因子的组合方式。

## 五 seed 中位数

| variant | PAPER IC | PAPER net ARR | executable IC | executable net ARR |
|---|---:|---:|---:|---:|
{chr(10).join(variant_rows)}

核心二因子组合的 PAPER / executable 净 ARR 分别为 `{core_paper:.4%}` /
`{core_exec:.4%}`。

## Matched-seed interaction contrasts

| contrast | PAPER positive seeds | paired median ΔARR | executable positive seeds | paired median ΔARR |
|---|---:|---:|---:|---:|
{chr(10).join(contrast_rows)}

四因子相对核心二因子组合的 paired median ΔARR 为 PAPER
`{all_paper_delta:+.4%}`、executable `{all_exec_delta:+.4%}`。

## 研究裁决

- `momentum + volume` 是本轮最佳组合，PAPER / executable 净 ARR 中位数为
  `{core_paper:.4%}` / `{core_exec:.4%}`。
- volume 在给定 momentum 后的收益增量为正，但只覆盖 3/5 seed；momentum
  在给定 volume 后覆盖 4/5 seed。因此 momentum 是核心，volume 是较弱的条件增量。
- reversal 或 close-location 单独加入核心组合时，两条 lane 的 paired median
  ARR 都下降；同时加入也下降。因此 23C1 的“可能存在弱因子交互”假设被否定。
- 下一轮 factor library 只保留 momentum + volume；不保留 reversal 与
  close-location。

canonical feature-order 复现审计：
`{reproduction_audit["status"]}`，最大指标绝对偏差
`{reproduction_audit.get("max_abs_diff", float("nan")):.3e}`。

## 解释边界

- 这些组合由 23C1 historical-test readout 驱动，属于 post-hoc interaction
  diagnostic，不能用于新的 true OOS 主张。
- `positive seeds` 使用相同 seed 的成对差值；中位数不是两个独立中位数之差。
- 只有当弱单因子在给定核心组合后仍稳定改善，才有理由把它解释为条件贡献；
  单看四因子全量组最好不足以证明每个因子都应晋级。
- 本阶段不调用 LLM，也不计入论文 agent 搜索预算。

运行耗时：`{elapsed:.2f}` 秒。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--factor-panel")
    parser.add_argument("--seeds")
    args = parser.parse_args()

    started = time.monotonic()
    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    topic_root = find_topic_root(config_path)
    output_dir = topic_root / config["outputs"]["factor_interaction"]
    local_cache = topic_root / config["outputs"]["local_cache"]
    output_dir.mkdir(parents=True, exist_ok=True)
    local_cache.mkdir(parents=True, exist_ok=True)

    loop0_manifest = (
        topic_root
        / "experiments/pending/23_rdagent_quant_pit_replication_v0"
        / "outputs/23C_rdagent_factor_loop_0/manifest.json"
    )
    factor_panel_path = resolve_factor_panel(
        topic_root, loop0_manifest, args.factor_panel
    )
    factors = load_factor_panel(factor_panel_path)

    alpha_names = list(config["alpha20"])
    label_names = ["paper_proxy", "executable_bridge"]
    expressions = [config["alpha20"][name] for name in alpha_names]
    expressions.extend(
        config["labels"][name]["expression"] for name in label_names
    )
    columns = [*alpha_names, *label_names]
    config_sha = sha256_file(config_path)
    base_frame = load_or_materialize(
        provider_path=topic_root / config["data"]["provider_uri"],
        market=config["data"]["market"],
        expressions=expressions,
        columns=columns,
        start_time=config["data"]["expected_calendar_start"],
        end_time=config["data"]["expected_calendar_end"],
        cache_path=(
            local_cache
            / f"alpha20_dual_label_panel_{config_sha[:12]}.parquet"
        ),
    )
    frame = base_frame.join(factors, how="left")
    split_frames: dict[str, pd.DataFrame] = {}
    for split_name in ["train", "validation", "historical_test"]:
        start, end = config["split"][split_name]
        part = frame.loc[
            (slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :
        ].copy()
        split_frames[split_name] = part[part["paper_proxy"].notna()]
    targets = {
        name: cross_sectional_zscore(part["paper_proxy"])
        for name, part in split_frames.items()
    }

    seeds = parse_seed_override(args.seeds, list(config["baseline"]["seeds"]))
    metric_rows: list[dict[str, Any]] = []
    importance_parts: list[pd.DataFrame] = []
    normalization_parts: list[pd.DataFrame] = []
    for variant, extra_features in VARIANTS.items():
        canonical_order = [
            factor for factor in FACTOR_NAMES if factor in extra_features
        ]
        if extra_features != canonical_order:
            raise ValueError(
                f"{variant} factor order is not canonical: {extra_features}"
            )
        rows, importances, normalization = evaluate_variant(
            variant=variant,
            extra_features=extra_features,
            alpha_names=alpha_names,
            split_frames=split_frames,
            targets=targets,
            seeds=seeds,
            config=config,
        )
        metric_rows.extend(rows)
        importance_parts.extend(importances)
        normalization_parts.append(normalization)

    seed_metrics = pd.DataFrame(metric_rows)
    comparison = build_comparison(seed_metrics)
    contrast_deltas, contrast_summary = build_contrasts(seed_metrics)
    reproduction_audit = audit_prior_all_four(
        topic_root, config, seed_metrics
    )

    seed_metrics.to_csv(output_dir / "seed_metrics.csv", index=False)
    comparison.to_csv(output_dir / "variant_comparison.csv", index=False)
    contrast_deltas.to_csv(
        output_dir / "interaction_contrasts.csv", index=False
    )
    contrast_summary.to_csv(
        output_dir / "interaction_summary.csv", index=False
    )
    pd.concat(importance_parts, ignore_index=True).to_csv(
        output_dir / "feature_importance.csv", index=False
    )
    pd.concat(normalization_parts, ignore_index=True).to_csv(
        output_dir / "train_only_normalization.csv", index=False
    )

    elapsed = time.monotonic() - started
    manifest = {
        "episode_id": config["episode_id"],
        "stage": "23C2_factor_interaction_isolation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha,
        "factor_panel": str(factor_panel_path),
        "factor_panel_sha256": sha256_file(factor_panel_path),
        "factors": FACTOR_NAMES,
        "variants": VARIANTS,
        "contrasts": CONTRASTS,
        "seeds": seeds,
        "formal_five_seed_run": seeds == list(config["baseline"]["seeds"]),
        "selection": "none; post-hoc matched-seed interaction contrasts",
        "canonical_order_reproduction_audit": reproduction_audit,
        "evidence_class": config["split"]["evidence_class"],
        "claim_ceiling": "posthoc_factor_interaction_diagnostic",
        "elapsed_seconds": elapsed,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "23C2_factor_interaction_isolation_report.md").write_text(
        render_report(
            comparison,
            contrast_summary,
            reproduction_audit,
            elapsed,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
