#!/usr/bin/env python3
"""Matched-seed marginal attribution for the corrected RD-Agent factor batch."""

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
    build_comparison,
    evaluate_variant,
)

MOMENTUM = "close_momentum_20d"
VOLUME = "volume_surprise_20d"
REVERSAL = "reversal_5d"
VOLATILITY = "volatility_20d"
INTRADAY_RANGE = "intraday_range_1d"

CORE_FACTORS = [MOMENTUM, VOLUME]
NEW_FACTORS = [REVERSAL, VOLATILITY, INTRADAY_RANGE]
CANONICAL_ORDER = [*CORE_FACTORS, *NEW_FACTORS]

VARIANTS = {
    "core": CORE_FACTORS,
    "core_plus_reversal": [*CORE_FACTORS, REVERSAL],
    "core_plus_volatility": [*CORE_FACTORS, VOLATILITY],
    "core_plus_intraday_range": [*CORE_FACTORS, INTRADAY_RANGE],
    "core_plus_reversal_volatility": [
        *CORE_FACTORS,
        REVERSAL,
        VOLATILITY,
    ],
    "core_plus_reversal_intraday_range": [
        *CORE_FACTORS,
        REVERSAL,
        INTRADAY_RANGE,
    ],
    "core_plus_volatility_intraday_range": [
        *CORE_FACTORS,
        VOLATILITY,
        INTRADAY_RANGE,
    ],
    "core_plus_all_three": CANONICAL_ORDER,
}

CONTRASTS = {
    "reversal_given_core": ("core_plus_reversal", "core"),
    "volatility_given_core": ("core_plus_volatility", "core"),
    "intraday_range_given_core": ("core_plus_intraday_range", "core"),
    "all_three_given_core": ("core_plus_all_three", "core"),
    "reversal_volatility_given_core": (
        "core_plus_reversal_volatility",
        "core",
    ),
    "reversal_intraday_range_given_core": (
        "core_plus_reversal_intraday_range",
        "core",
    ),
    "volatility_intraday_range_given_core": (
        "core_plus_volatility_intraday_range",
        "core",
    ),
    "reversal_given_core_and_other_two": (
        "core_plus_all_three",
        "core_plus_volatility_intraday_range",
    ),
    "volatility_given_core_and_other_two": (
        "core_plus_all_three",
        "core_plus_reversal_intraday_range",
    ),
    "intraday_range_given_core_and_other_two": (
        "core_plus_all_three",
        "core_plus_reversal_volatility",
    ),
    "other_two_given_core_and_reversal": (
        "core_plus_all_three",
        "core_plus_reversal",
    ),
    "other_two_given_core_and_volatility": (
        "core_plus_all_three",
        "core_plus_volatility",
    ),
    "other_two_given_core_and_intraday_range": (
        "core_plus_all_three",
        "core_plus_intraday_range",
    ),
    "intraday_range_vs_volatility": (
        "core_plus_intraday_range",
        "core_plus_volatility",
    ),
}

CONTRAST_METRICS = [
    "validation_paper_proxy_ic",
    "validation_executable_bridge_ic",
    "historical_test_paper_proxy_ic",
    "historical_test_executable_bridge_ic",
    "historical_test_paper_proxy_net_arr",
    "historical_test_executable_bridge_net_arr",
    "historical_test_paper_proxy_mdd",
    "historical_test_executable_bridge_mdd",
]

PRIMARY_SINGLE_CONTRASTS = {
    REVERSAL: "reversal_given_core",
    VOLATILITY: "volatility_given_core",
    INTRADAY_RANGE: "intraday_range_given_core",
}

PRIMARY_LEAVE_ONE_OUT_CONTRASTS = {
    REVERSAL: "reversal_given_core_and_other_two",
    VOLATILITY: "volatility_given_core_and_other_two",
    INTRADAY_RANGE: "intraday_range_given_core_and_other_two",
}


def resolve_factor_panel(
    topic_root: Path,
    config: dict[str, Any],
    override: str | None,
) -> Path:
    if override:
        path = Path(override).expanduser().resolve()
    else:
        manifest_path = (
            topic_root
            / config["outputs"]["corrected_factor_loop"]
            / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        workspace_id = manifest["corrected_candidate"]["workspace_id"]
        path = (
            Path(config["rdagent"]["checkout"])
            / "git_ignore_folder/RD-Agent_workspace"
            / workspace_id
            / "combined_factors_df.parquet"
        )
    if not path.is_file():
        raise FileNotFoundError(f"factor panel not found: {path}")
    return path


def normalize_factor_panel(path: Path, factors: list[str]) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if list(frame.index.names) == ["instrument", "datetime"]:
        frame = frame.swaplevel()
    frame.index = frame.index.set_names(["datetime", "instrument"])
    if isinstance(frame.columns, pd.MultiIndex):
        if set(frame.columns.get_level_values(0)) != {"feature"}:
            raise ValueError("unexpected factor panel column groups")
        frame.columns = frame.columns.get_level_values(-1)
    missing = sorted(set(factors) - set(frame.columns))
    if missing:
        raise ValueError(f"factor panel missing columns: {missing}")
    return (
        frame[factors]
        .astype("float64")
        .replace([np.inf, -np.inf], np.nan)
        .sort_index()
    )


def build_contrasts(
    seed_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    indexed = seed_metrics.set_index(["variant", "seed"])
    rows: list[dict[str, Any]] = []
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


def audit_core_factor_values(
    topic_root: Path,
    config: dict[str, Any],
    current: pd.DataFrame,
) -> dict[str, Any]:
    prior_manifest_path = (
        topic_root / config["outputs"]["factor_interaction"] / "manifest.json"
    )
    prior_manifest = json.loads(
        prior_manifest_path.read_text(encoding="utf-8")
    )
    prior_path = Path(prior_manifest["factor_panel"])
    prior = normalize_factor_panel(prior_path, CORE_FACTORS)
    current_core = current[CORE_FACTORS]
    common_index = prior.index.intersection(current_core.index)
    prior_values = prior.loc[common_index].to_numpy(dtype="float64")
    current_values = current_core.loc[common_index].to_numpy(dtype="float64")
    finite = np.isfinite(prior_values) & np.isfinite(current_values)
    max_abs_diff = float(
        np.max(np.abs(prior_values[finite] - current_values[finite]))
    )
    nan_pattern_match = bool(
        np.array_equal(np.isnan(prior_values), np.isnan(current_values))
    )
    passed = bool(
        nan_pattern_match
        and np.allclose(
            prior_values,
            current_values,
            rtol=0.0,
            atol=0.0,
            equal_nan=True,
        )
    )
    return {
        "status": "passed" if passed else "failed",
        "prior_factor_panel": str(prior_path),
        "common_rows": len(common_index),
        "nan_pattern_match": nan_pattern_match,
        "max_abs_diff": max_abs_diff,
    }


def audit_core_metrics(
    topic_root: Path,
    config: dict[str, Any],
    seed_metrics: pd.DataFrame,
) -> dict[str, Any]:
    prior_path = (
        topic_root
        / config["outputs"]["factor_interaction"]
        / "seed_metrics.csv"
    )
    prior = pd.read_csv(prior_path)
    prior = (
        prior[prior["variant"] == "plus_momentum_volume"]
        .sort_values("seed")
        .reset_index(drop=True)
    )
    current = (
        seed_metrics[seed_metrics["variant"] == "core"]
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
    metric_atol = 5e-7
    passed = bool(
        np.allclose(
            prior_values,
            current_values,
            rtol=1e-6,
            atol=metric_atol,
            equal_nan=True,
        )
    )
    return {
        "status": "passed" if passed else "failed",
        "prior_seed_metrics": str(prior_path),
        "prior_variant": "plus_momentum_volume",
        "current_variant": "core",
        "rtol": 1e-6,
        "atol": metric_atol,
        "max_abs_diff": max_abs_diff,
        "numeric_metric_count": len(numeric_columns),
    }


def contrast_record(
    summary: pd.DataFrame,
    contrast: str,
    metric: str,
) -> pd.Series:
    return summary[
        (summary["contrast"] == contrast) & (summary["metric"] == metric)
    ].iloc[0]


def factor_decisions(contrast_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor in NEW_FACTORS:
        single_name = PRIMARY_SINGLE_CONTRASTS[factor]
        leaveout_name = PRIMARY_LEAVE_ONE_OUT_CONTRASTS[factor]
        record: dict[str, Any] = {"factor": factor}
        single_gates = []
        for lane in ["paper_proxy", "executable_bridge"]:
            for metric_suffix in [
                "validation_{lane}_ic",
                "historical_test_{lane}_ic",
                "historical_test_{lane}_net_arr",
            ]:
                metric = metric_suffix.format(lane=lane)
                result = contrast_record(
                    contrast_summary,
                    single_name,
                    metric,
                )
                median_delta = float(result["median_paired_delta"])
                positive_count = int(result["positive_seed_count"])
                record[f"given_core_{metric}_median_delta"] = median_delta
                record[f"given_core_{metric}_positive_seed_count"] = (
                    positive_count
                )
                single_gates.append(median_delta > 0 and positive_count >= 3)
        for lane in ["paper_proxy", "executable_bridge"]:
            metric = f"historical_test_{lane}_net_arr"
            result = contrast_record(
                contrast_summary,
                leaveout_name,
                metric,
            )
            record[
                f"leave_one_out_{lane}_median_delta_arr"
            ] = float(result["median_paired_delta"])
            record[
                f"leave_one_out_{lane}_positive_seed_count"
            ] = int(result["positive_seed_count"])
        record["single_addition_decision"] = (
            "individually_supported" if all(single_gates) else "reject"
        )
        rows.append(record)
    decisions = pd.DataFrame(rows)
    decisions["library_action"] = decisions[
        "single_addition_decision"
    ].map(
        {
            "individually_supported": "supported_not_selected",
            "reject": "reject",
        }
    )

    supported = set(
        decisions[
            decisions["single_addition_decision"]
            == "individually_supported"
        ]["factor"]
    )
    if {VOLATILITY, INTRADAY_RANGE}.issubset(supported):
        pair_paper = contrast_record(
            contrast_summary,
            "volatility_intraday_range_given_core",
            "historical_test_paper_proxy_net_arr",
        )
        pair_executable = contrast_record(
            contrast_summary,
            "volatility_intraday_range_given_core",
            "historical_test_executable_bridge_net_arr",
        )
        pair_supported = all(
            float(result["median_paired_delta"]) > 0
            and int(result["positive_seed_count"]) >= 3
            for result in [pair_paper, pair_executable]
        )
        if pair_supported:
            decisions.loc[
                decisions["factor"].isin([VOLATILITY, INTRADAY_RANGE]),
                "library_action",
            ] = "retain_compatible_pair"
        else:
            direct_metrics = [
                "validation_paper_proxy_ic",
                "historical_test_paper_proxy_net_arr",
                "historical_test_executable_bridge_net_arr",
            ]
            range_wins = []
            volatility_wins = []
            for metric in direct_metrics:
                result = contrast_record(
                    contrast_summary,
                    "intraday_range_vs_volatility",
                    metric,
                )
                median_delta = float(result["median_paired_delta"])
                positive_count = int(result["positive_seed_count"])
                range_wins.append(
                    median_delta > 0 and positive_count >= 3
                )
                volatility_wins.append(
                    median_delta < 0 and positive_count <= 2
                )
            if all(range_wins) or all(volatility_wins):
                selected = (
                    INTRADAY_RANGE
                    if all(range_wins)
                    else VOLATILITY
                )
                alternative = (
                    VOLATILITY
                    if selected == INTRADAY_RANGE
                    else INTRADAY_RANGE
                )
                decisions.loc[
                    decisions["factor"] == selected,
                    "library_action",
                ] = "retain_primary"
                decisions.loc[
                    decisions["factor"] == alternative,
                    "library_action",
                ] = "supported_alternative_not_combined"
            else:
                decisions.loc[
                    decisions["factor"].isin(
                        [VOLATILITY, INTRADAY_RANGE]
                    ),
                    "library_action",
                ] = "supported_no_unique_selection"
    elif len(supported) == 1:
        selected = next(iter(supported))
        decisions.loc[
            decisions["factor"] == selected,
            "library_action",
        ] = "retain_primary"
    return decisions


def render_report(
    comparison: pd.DataFrame,
    contrast_summary: pd.DataFrame,
    decisions: pd.DataFrame,
    factor_audit: dict[str, Any],
    metric_audit: dict[str, Any],
    elapsed: float,
) -> str:
    def variant_value(variant: str, metric: str) -> float:
        return float(
            comparison[
                (comparison["variant"] == variant)
                & (comparison["metric"] == metric)
            ].iloc[0]["median"]
        )

    variant_rows = []
    for variant in VARIANTS:
        variant_rows.append(
            "| {variant} | {paper_ic:.6f} | {paper_arr:.4%} | "
            "{exec_ic:.6f} | {exec_arr:.4%} |".format(
                variant=variant,
                paper_ic=variant_value(
                    variant,
                    "historical_test_paper_proxy_ic",
                ),
                paper_arr=variant_value(
                    variant,
                    "historical_test_paper_proxy_net_arr",
                ),
                exec_ic=variant_value(
                    variant,
                    "historical_test_executable_bridge_ic",
                ),
                exec_arr=variant_value(
                    variant,
                    "historical_test_executable_bridge_net_arr",
                ),
            )
        )

    contrast_rows = []
    key_contrasts = [
        *PRIMARY_SINGLE_CONTRASTS.values(),
        "all_three_given_core",
        "reversal_volatility_given_core",
        "reversal_intraday_range_given_core",
        "volatility_intraday_range_given_core",
        *PRIMARY_LEAVE_ONE_OUT_CONTRASTS.values(),
        "intraday_range_vs_volatility",
    ]
    for contrast in key_contrasts:
        paper = contrast_record(
            contrast_summary,
            contrast,
            "historical_test_paper_proxy_net_arr",
        )
        executable = contrast_record(
            contrast_summary,
            contrast,
            "historical_test_executable_bridge_net_arr",
        )
        contrast_rows.append(
            f"| {contrast} | "
            f"{int(paper['positive_seed_count'])}/5 | "
            f"{float(paper['median_paired_delta']):+.4%} | "
            f"{int(executable['positive_seed_count'])}/5 | "
            f"{float(executable['median_paired_delta']):+.4%} |"
        )

    decision_rows = []
    for row in decisions.itertuples(index=False):
        decision_rows.append(
            f"| {row.factor} | {row.single_addition_decision} | "
            f"{row.library_action} | "
            f"{row.given_core_historical_test_paper_proxy_net_arr_median_delta:+.4%} | "
            f"{row.given_core_historical_test_executable_bridge_net_arr_median_delta:+.4%} | "
            f"{row.leave_one_out_paper_proxy_median_delta_arr:+.4%} | "
            f"{row.leave_one_out_executable_bridge_median_delta_arr:+.4%} |"
        )

    retained = decisions[
        decisions["library_action"].isin(
            ["retain_primary", "retain_compatible_pair"]
        )
    ]["factor"].tolist()
    alternatives = decisions[
        decisions["library_action"]
        == "supported_alternative_not_combined"
    ]["factor"].tolist()
    no_unique_selection = decisions[
        decisions["library_action"] == "supported_no_unique_selection"
    ]["factor"].tolist()
    rejected = decisions[decisions["library_action"] == "reject"][
        "factor"
    ].tolist()

    return f"""# EP23 23C4 New Factor Marginal Attribution

## 裁决

```text
core = close_momentum_20d + volume_surprise_20d
new_batch = reversal_5d + volatility_20d + intraday_range_1d
design = five-seed single-addition + leave-one-out
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = posthoc_marginal_attribution_diagnostic
```

本阶段不再调用 LLM；它冻结 23C3 生成的因子实现，沿用 23C2 的 Alpha20、
双 label lane、LightGBM、train-only normalization、Top50/drop5 和费用，
只改变三个新增因子的组合。

## 五 seed 中位数

| variant | PAPER IC | PAPER net ARR | executable IC | executable net ARR |
|---|---:|---:|---:|---:|
{chr(10).join(variant_rows)}

## Matched-seed marginal contrasts

| contrast | PAPER positive seeds | paired median ΔARR | executable positive seeds | paired median ΔARR |
|---|---:|---:|---:|---:|
{chr(10).join(contrast_rows)}

## 因子级裁决

single-addition gate 要求因子相对核心的 validation IC、historical-test IC 和
historical-test ARR 在 PAPER 与 executable 两条 lane 中 paired median 均为正，
且至少覆盖 3/5 seed。leave-one-out 用作交互压力测试，不在全量包已经有害时
反向否决单因子。

| factor | single-addition | library action | core PAPER ΔARR | core executable ΔARR | LOO PAPER ΔARR | LOO executable ΔARR |
|---|---|---|---:|---:|---:|---:|
{chr(10).join(decision_rows)}

- 最终保留：`{", ".join(retained) if retained else "none"}`。
- 有单因子证据但与入选因子不兼容：
  `{", ".join(alternatives) if alternatives else "none"}`。
- 有单因子证据但直接比较无法唯一选择：
  `{", ".join(no_unique_selection) if no_unique_selection else "none"}`。
- 拒绝：`{", ".join(rejected) if rejected else "none"}`。

当 volatility 与 range 均通过 single-addition gate、但二者联合未通过双 lane
gate 时，使用相同 seed 直接比较两者；PAPER validation IC 是首要选择信号，
historical-test 两条 ARR lane 只检查方向一致性。

## 复现审计

- 23C3 与 23C2 核心因子数值：`{factor_audit["status"]}`，
  common rows `{factor_audit["common_rows"]}`，最大绝对差
  `{factor_audit["max_abs_diff"]:.3e}`。
- 23C4 core 与 23C2 `plus_momentum_volume` 指标：
  `{metric_audit["status"]}`，最大绝对差
  `{metric_audit["max_abs_diff"]:.3e}`。

## 解释边界

- 该实验由 23C3 historical-test 联合结果触发，只是 post-hoc attribution，
  不产生新的 true OOS 证据。
- positive seed count 基于相同 seed 的配对差值；paired median 不是两个独立
  中位数之差。
- 23C3 的 Qlib 单次含成本超额 ARR 与本报告五 seed 策略绝对净 ARR 语义不同，
  不能直接比较数值。
- 本阶段不计入论文 Agent LLM 搜索预算。

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
    output_dir = topic_root / config["outputs"]["factor_marginal_attribution"]
    local_cache = topic_root / config["outputs"]["local_cache"]
    output_dir.mkdir(parents=True, exist_ok=True)
    local_cache.mkdir(parents=True, exist_ok=True)

    factor_panel_path = resolve_factor_panel(
        topic_root,
        config,
        args.factor_panel,
    )
    factors = normalize_factor_panel(factor_panel_path, CANONICAL_ORDER)
    factor_audit = audit_core_factor_values(topic_root, config, factors)
    if factor_audit["status"] != "passed":
        raise ValueError(f"core factor value audit failed: {factor_audit}")

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
            (slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)),
            :,
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
        canonical = [
            factor for factor in CANONICAL_ORDER if factor in extra_features
        ]
        if extra_features != canonical:
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
    comparison = build_comparison(
        pd.concat(
            [
                seed_metrics.assign(
                    variant=seed_metrics["variant"].replace({"core": "alpha20"})
                ),
                seed_metrics[seed_metrics["variant"] == "core"],
            ],
            ignore_index=True,
        )
    )
    comparison = comparison[comparison["variant"] != "alpha20"].copy()
    core_medians = (
        seed_metrics[seed_metrics["variant"] == "core"]
        .select_dtypes(include=[np.number])
        .median()
    )
    comparison["baseline_median"] = comparison["metric"].map(core_medians)
    comparison["delta"] = (
        comparison["median"] - comparison["baseline_median"]
    )
    contrast_deltas, contrast_summary = build_contrasts(seed_metrics)
    decisions = factor_decisions(contrast_summary)
    metric_audit = audit_core_metrics(topic_root, config, seed_metrics)
    if metric_audit["status"] != "passed":
        raise ValueError(f"core metric audit failed: {metric_audit}")

    coverage_rows = []
    for split_name, part in split_frames.items():
        for factor in CANONICAL_ORDER:
            coverage_rows.append(
                {
                    "split": split_name,
                    "factor": factor,
                    "rows": len(part),
                    "finite_rows": int(np.isfinite(part[factor]).sum()),
                    "finite_ratio": float(np.isfinite(part[factor]).mean()),
                }
            )
    coverage = pd.DataFrame(coverage_rows)

    seed_metrics.to_csv(output_dir / "seed_metrics.csv", index=False)
    comparison.to_csv(output_dir / "variant_comparison.csv", index=False)
    contrast_deltas.to_csv(
        output_dir / "marginal_contrasts.csv",
        index=False,
    )
    contrast_summary.to_csv(
        output_dir / "marginal_summary.csv",
        index=False,
    )
    decisions.to_csv(output_dir / "factor_decisions.csv", index=False)
    coverage.to_csv(output_dir / "factor_coverage.csv", index=False)
    pd.concat(importance_parts, ignore_index=True).to_csv(
        output_dir / "feature_importance.csv",
        index=False,
    )
    pd.concat(normalization_parts, ignore_index=True).to_csv(
        output_dir / "train_only_normalization.csv",
        index=False,
    )

    elapsed = time.monotonic() - started
    manifest = {
        "episode_id": config["episode_id"],
        "stage": "23C4_new_factor_marginal_attribution",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "config_sha256": config_sha,
        "factor_panel": str(factor_panel_path),
        "factor_panel_sha256": sha256_file(factor_panel_path),
        "core_factors": CORE_FACTORS,
        "new_factors": NEW_FACTORS,
        "canonical_factor_order": CANONICAL_ORDER,
        "variants": VARIANTS,
        "contrasts": CONTRASTS,
        "seeds": seeds,
        "formal_five_seed_run": seeds == list(config["baseline"]["seeds"]),
        "preprocessing": (
            "train-only robust z-score and fill-zero for all variants"
        ),
        "core_factor_value_audit": factor_audit,
        "core_metric_reproduction_audit": metric_audit,
        "factor_decisions": decisions[
            [
                "factor",
                "single_addition_decision",
                "library_action",
            ]
        ].to_dict(orient="records"),
        "selection": "strict matched-seed marginal attribution gate",
        "evidence_class": config["split"]["evidence_class"],
        "claim_ceiling": "posthoc_marginal_attribution_diagnostic",
        "elapsed_seconds": elapsed,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = render_report(
        comparison,
        contrast_summary,
        decisions,
        factor_audit,
        metric_audit,
        elapsed,
    )
    (output_dir / "23C4_new_factor_marginal_attribution_report.md").write_text(
        report,
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
