#!/usr/bin/env python3
"""Controlled five-seed ablation of the four RD-Agent Loop-0 factors."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml

from run_23b_alpha20_lgbm_baseline import (
    apply_robust_transform,
    correlation_summary,
    cross_sectional_zscore,
    daily_correlations,
    find_topic_root,
    fit_robust_transform,
    load_or_materialize,
    parse_seed_override,
    portfolio_summary,
    sha256_file,
    topk_dropout_returns,
)

FACTOR_NAMES = [
    "close_momentum_20d",
    "close_reversal_5d",
    "daily_close_location_value",
    "volume_surprise_20d",
]


def resolve_factor_panel(
    topic_root: Path, manifest_path: Path, override: str | None
) -> Path:
    if override:
        path = Path(override).expanduser().resolve()
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        path = (
            Path(manifest["source"]["combined_workspace"])
            / "combined_factors_df.parquet"
        )
    if not path.is_file():
        raise FileNotFoundError(f"factor panel not found: {path}")
    return path


def load_factor_panel(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if list(frame.index.names) == ["instrument", "datetime"]:
        frame = frame.swaplevel()
    frame.index = frame.index.set_names(["datetime", "instrument"])
    if isinstance(frame.columns, pd.MultiIndex):
        if set(frame.columns.get_level_values(0)) != {"feature"}:
            raise ValueError("unexpected factor panel column groups")
        frame.columns = frame.columns.get_level_values(-1)
    missing = sorted(set(FACTOR_NAMES) - set(frame.columns))
    if missing:
        raise ValueError(f"factor panel missing columns: {missing}")
    return (
        frame[FACTOR_NAMES]
        .astype("float64")
        .replace([np.inf, -np.inf], np.nan)
        .sort_index()
    )


def build_variants() -> dict[str, list[str]]:
    variants = {"alpha20": []}
    variants.update({f"plus_{name}": [name] for name in FACTOR_NAMES})
    variants["plus_all_four"] = FACTOR_NAMES
    return variants


def evaluate_variant(
    *,
    variant: str,
    extra_features: list[str],
    alpha_names: list[str],
    split_frames: dict[str, pd.DataFrame],
    targets: dict[str, pd.Series],
    seeds: list[int],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[pd.DataFrame], pd.DataFrame]:
    feature_names = [*alpha_names, *extra_features]
    clip = float(config["baseline"]["robust_zscore_clip"])
    median, scale = fit_robust_transform(
        split_frames["train"][feature_names], clip=clip
    )
    transformed = {
        name: apply_robust_transform(part[feature_names], median, scale, clip)
        for name, part in split_frames.items()
    }

    train_mask = targets["train"].notna()
    valid_mask = targets["validation"].notna()
    X_train = transformed["train"].loc[train_mask]
    y_train = targets["train"].loc[train_mask].astype("float32")
    X_valid = transformed["validation"].loc[valid_mask]
    y_valid = targets["validation"].loc[valid_mask].astype("float32")

    rows: list[dict[str, Any]] = []
    importance_parts: list[pd.DataFrame] = []
    lgb_params = dict(config["baseline"]["lightgbm"])
    minimum_cross_section = int(
        config["baseline"]["minimum_daily_cross_section"]
    )

    for seed in seeds:
        model = lgb.LGBMRegressor(
            **lgb_params,
            random_state=seed,
            bagging_seed=seed,
            feature_fraction_seed=seed,
            data_random_seed=seed,
            verbosity=-1,
        )
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_valid, y_valid)],
            eval_metric="l2",
            callbacks=[
                lgb.early_stopping(
                    int(config["baseline"]["early_stopping_rounds"]),
                    verbose=False,
                ),
                lgb.log_evaluation(period=0),
            ],
        )
        row: dict[str, Any] = {
            "variant": variant,
            "seed": seed,
            "feature_count": len(feature_names),
            "best_iteration": int(model.best_iteration_ or model.n_estimators),
        }
        for split_name in ["validation", "historical_test"]:
            scored = split_frames[split_name][
                ["paper_proxy", "executable_bridge"]
            ].copy()
            scored["prediction"] = model.predict(
                transformed[split_name],
                num_iteration=model.best_iteration_,
            )
            for label_name in ["paper_proxy", "executable_bridge"]:
                daily = daily_correlations(
                    scored,
                    prediction_column="prediction",
                    label_column=label_name,
                    minimum_cross_section=minimum_cross_section,
                )
                for key, value in correlation_summary(daily).items():
                    row[f"{split_name}_{label_name}_{key}"] = value
                if split_name == "historical_test":
                    portfolio = topk_dropout_returns(
                        scored,
                        prediction_column="prediction",
                        label_column=label_name,
                        topk=int(config["portfolio"]["topk"]),
                        n_drop=int(config["portfolio"]["n_drop"]),
                        buy_cost=float(config["portfolio"]["buy_cost"]),
                        sell_cost=float(config["portfolio"]["sell_cost"]),
                    )
                    for key, value in portfolio_summary(
                        portfolio,
                        int(config["portfolio"]["annualization"]),
                    ).items():
                        row[f"historical_test_{label_name}_{key}"] = value
        rows.append(row)
        importance_parts.append(
            pd.DataFrame(
                {
                    "variant": variant,
                    "seed": seed,
                    "feature": feature_names,
                    "gain": model.booster_.feature_importance(
                        importance_type="gain"
                    ),
                    "split_count": model.booster_.feature_importance(
                        importance_type="split"
                    ),
                }
            )
        )

    normalization = pd.DataFrame(
        {
            "variant": variant,
            "feature": feature_names,
            "train_median": median.reindex(feature_names).values,
            "train_scale": scale.reindex(feature_names).values,
        }
    )
    return rows, importance_parts, normalization


def build_comparison(seed_metrics: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "validation_paper_proxy_ic",
        "validation_executable_bridge_ic",
        "historical_test_paper_proxy_ic",
        "historical_test_executable_bridge_ic",
        "historical_test_paper_proxy_net_arr",
        "historical_test_executable_bridge_net_arr",
        "historical_test_paper_proxy_active_ir_vs_universe_equal_weight",
        "historical_test_executable_bridge_active_ir_vs_universe_equal_weight",
        "historical_test_paper_proxy_mdd",
        "historical_test_executable_bridge_mdd",
    ]
    medians = seed_metrics.groupby("variant", sort=False)[metrics].median()
    baseline = medians.loc["alpha20"]
    rows = []
    for variant, values in medians.iterrows():
        for metric in metrics:
            rows.append(
                {
                    "variant": variant,
                    "metric": metric,
                    "median": float(values[metric]),
                    "baseline_median": float(baseline[metric]),
                    "delta": float(values[metric] - baseline[metric]),
                }
            )
    return pd.DataFrame(rows)


def build_matched_seed_stability(
    seed_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [
        "historical_test_paper_proxy_ic",
        "historical_test_executable_bridge_ic",
        "historical_test_paper_proxy_net_arr",
        "historical_test_executable_bridge_net_arr",
    ]
    baseline = seed_metrics[seed_metrics["variant"] == "alpha20"].set_index(
        "seed"
    )
    rows = []
    for variant, group in seed_metrics[
        seed_metrics["variant"] != "alpha20"
    ].groupby("variant", sort=False):
        current = group.set_index("seed")
        for seed in sorted(set(current.index) & set(baseline.index)):
            for metric in metrics:
                rows.append(
                    {
                        "variant": variant,
                        "seed": int(seed),
                        "metric": metric,
                        "current": float(current.loc[seed, metric]),
                        "baseline": float(baseline.loc[seed, metric]),
                        "delta": float(
                            current.loc[seed, metric]
                            - baseline.loc[seed, metric]
                        ),
                    }
                )
    deltas = pd.DataFrame(rows)
    stability = (
        deltas.groupby(["variant", "metric"], sort=False)["delta"]
        .agg(
            positive_seed_count=lambda values: int((values > 0).sum()),
            seed_count="count",
            median_paired_delta="median",
            min_paired_delta="min",
            max_paired_delta="max",
        )
        .reset_index()
    )
    return deltas, stability


def render_report(
    summary: pd.DataFrame,
    coverage: pd.DataFrame,
    stability: pd.DataFrame,
    elapsed: float,
) -> str:
    def value(variant: str, metric: str, column: str = "median") -> float:
        row = summary[
            (summary["variant"] == variant) & (summary["metric"] == metric)
        ].iloc[0]
        return float(row[column])

    variants = [name for name in build_variants() if name != "alpha20"]
    result_rows = []
    for variant in variants:
        result_rows.append(
            "| {variant} | {pic:.6f} | {picd:+.6f} | {pnet:.4%} | "
            "{pnetd:+.4%} | {enet:.4%} | {enetd:+.4%} |".format(
                variant=variant,
                pic=value(variant, "historical_test_paper_proxy_ic"),
                picd=value(
                    variant, "historical_test_paper_proxy_ic", "delta"
                ),
                pnet=value(
                    variant, "historical_test_paper_proxy_net_arr"
                ),
                pnetd=value(
                    variant,
                    "historical_test_paper_proxy_net_arr",
                    "delta",
                ),
                enet=value(
                    variant, "historical_test_executable_bridge_net_arr"
                ),
                enetd=value(
                    variant,
                    "historical_test_executable_bridge_net_arr",
                    "delta",
                ),
            )
        )

    consistent = [
        variant
        for variant in variants
        if value(
            variant, "historical_test_paper_proxy_net_arr", "delta"
        )
        > 0
        and value(
            variant, "historical_test_executable_bridge_net_arr", "delta"
        )
        > 0
    ]
    best = max(
        variants,
        key=lambda variant: value(
            variant, "historical_test_executable_bridge_net_arr", "delta"
        ),
    )
    min_coverage = float(coverage["finite_ratio"].min())
    stability_rows = []
    for variant in variants:
        paper = stability[
            (stability["variant"] == variant)
            & (
                stability["metric"]
                == "historical_test_paper_proxy_net_arr"
            )
        ].iloc[0]
        executable = stability[
            (stability["variant"] == variant)
            & (
                stability["metric"]
                == "historical_test_executable_bridge_net_arr"
            )
        ].iloc[0]
        stability_rows.append(
            f"| {variant} | {int(paper['positive_seed_count'])}/"
            f"{int(paper['seed_count'])} | "
            f"{float(paper['median_paired_delta']):+.4%} | "
            f"{int(executable['positive_seed_count'])}/"
            f"{int(executable['seed_count'])} | "
            f"{float(executable['median_paired_delta']):+.4%} |"
        )
    return f"""# EP23 23C1 Controlled Factor Ablation

## 裁决

```text
preprocessing = matched train-only robust z-score + fill-zero
seeds = 5 matched seeds
variants = Alpha20 + 4 single-factor additions + all-four addition
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = controlled_factor_attribution_diagnostic
```

23C 原始 RD-Agent loop 存在 preprocessing 漂移，本阶段在统一数据、split、
LightGBM、train-only normalization、组合规则和费用下重新进行归因。

## 五 seed 中位数

| variant | PAPER IC | ΔIC | PAPER net ARR | ΔARR | executable net ARR | ΔARR |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(result_rows)}

两条标签 lane 的净 ARR 均优于 Alpha20 的变体：
`{", ".join(consistent) if consistent else "none"}`。

以 executable bridge 净 ARR 增量排序，当前最佳变体为 `{best}`。这仍是被反复
观察过的 historical test，只用于定位首轮组合改善的来源，不构成 true OOS 晋级。

## Matched-seed stability

| variant | PAPER positive seeds | paired median ΔARR | executable positive seeds | paired median ΔARR |
|---|---:|---:|---:|---:|
{chr(10).join(stability_rows)}

## 下一项研究决策

- `close_momentum_20d` 是最明确的单因子贡献者：两条 lane 的 ARR 和 IC 均改善，
  收益改善在两条 lane 都覆盖 4/5 seed。
- `volume_surprise_20d` 是次级贡献者：两条 lane 收益均改善 4/5 seed，但
  PAPER IC 的稳定性弱于 momentum。
- `close_reversal_5d` 出现“IC 上升、组合收益下降”，不能仅凭 IC 纳入。
- `daily_close_location_value` 单独加入时明显拖累，不应单独晋级。
- 四因子联合的 executable ARR 最好且 5/5 seed 改善，说明可能存在交互项；
  下一实验应固定测试 `momentum + volume`、再分别加入 reversal/close-location，
  判断联合改善是否需要两个单独表现较差的因子。

## 解释边界

- 所有变体使用相同的五个 seed；主表报告跨 seed 中位数，不按 historical test
  选择 seed。
- 每个变体的 normalization 都只在 train split 拟合，然后应用于 validation 和
  historical test。
- 最低因子有限值覆盖率为 `{min_coverage:.4%}`；缺失值在 train-only robust
  normalization 后按既定 baseline 规则填零。
- 单因子结果用于归因，`plus_all_four` 用于检查组合交互，不将消融数量包装成
  agent 搜索预算。

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
    output_dir = topic_root / config["outputs"]["factor_ablation"]
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
    for variant, extra_features in build_variants().items():
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
    matched_deltas, stability = build_matched_seed_stability(seed_metrics)
    coverage_rows = []
    for split_name, part in split_frames.items():
        for factor in FACTOR_NAMES:
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
    matched_deltas.to_csv(
        output_dir / "matched_seed_deltas.csv", index=False
    )
    stability.to_csv(
        output_dir / "matched_seed_stability.csv", index=False
    )
    coverage.to_csv(output_dir / "factor_coverage.csv", index=False)
    pd.concat(importance_parts, ignore_index=True).to_csv(
        output_dir / "feature_importance.csv", index=False
    )
    pd.concat(normalization_parts, ignore_index=True).to_csv(
        output_dir / "train_only_normalization.csv", index=False
    )

    elapsed = time.monotonic() - started
    manifest = {
        "episode_id": config["episode_id"],
        "stage": "23C1_controlled_factor_ablation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha,
        "factor_panel": str(factor_panel_path),
        "factor_panel_sha256": sha256_file(factor_panel_path),
        "factors": FACTOR_NAMES,
        "variants": build_variants(),
        "seeds": seeds,
        "formal_five_seed_run": seeds == list(config["baseline"]["seeds"]),
        "preprocessing": "train-only robust z-score and fill-zero for all variants",
        "selection": "none; report matched-seed medians",
        "evidence_class": config["split"]["evidence_class"],
        "claim_ceiling": "controlled_factor_attribution_diagnostic",
        "elapsed_seconds": elapsed,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "23C1_controlled_factor_ablation_report.md").write_text(
        render_report(comparison, coverage, stability, elapsed),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
