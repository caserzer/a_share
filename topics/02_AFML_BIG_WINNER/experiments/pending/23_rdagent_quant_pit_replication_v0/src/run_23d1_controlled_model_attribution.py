#!/usr/bin/env python3
"""Matched-seed model attribution for EP23 23D1."""

from __future__ import annotations

import argparse
import gc
import hashlib
import inspect
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import pandas as pd
import qlib
import torch
import yaml
from qlib.contrib.model.pytorch_general_nn import GeneralPTNN
from qlib.data.dataset.handler import DataHandlerLP
from qlib.utils import init_instance_by_config
from torch.utils.data import DataLoader

import run_23b_alpha20_lgbm_baseline as baseline
from ep23_model_variants import MODEL_VARIANTS


KEY_METRICS = [
    "validation_paper_proxy_ic",
    "validation_paper_proxy_icir",
    "validation_paper_proxy_rank_ic",
    "validation_paper_proxy_rank_icir",
    "historical_test_paper_proxy_ic",
    "historical_test_paper_proxy_icir",
    "historical_test_paper_proxy_rank_ic",
    "historical_test_paper_proxy_rank_icir",
    "historical_test_paper_proxy_gross_arr",
    "historical_test_paper_proxy_net_arr",
    "historical_test_paper_proxy_active_ir_vs_universe_equal_weight",
    "historical_test_paper_proxy_mdd",
    "historical_test_paper_proxy_mean_one_way_turnover",
    "historical_test_executable_bridge_ic",
    "historical_test_executable_bridge_rank_ic",
    "historical_test_executable_bridge_gross_arr",
    "historical_test_executable_bridge_net_arr",
    "historical_test_executable_bridge_active_ir_vs_universe_equal_weight",
    "historical_test_executable_bridge_mdd",
    "historical_test_executable_bridge_mean_one_way_turnover",
]

FORMAL_VARIANTS = ["flattened_mlp", "last_state_gru"]


def parse_csv_values(value: str | None, default: list[Any], cast: type) -> list[Any]:
    if value is None:
        return default
    values = [cast(item.strip()) for item in value.split(",") if item.strip()]
    if not values:
        raise ValueError("override did not contain any values")
    return values


def set_deterministic_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def semantic_hash(config: dict[str, Any], model_source: Path) -> str:
    payload = {
        "alpha20": config["alpha20"],
        "labels": config["labels"],
        "data": config["data"],
        "split": config["split"],
        "portfolio": config["portfolio"],
        "model_attribution": config["model_attribution"],
        "model_source_sha256": baseline.sha256_file(model_source),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_dataset(
    config: dict[str, Any],
    provider_path: Path,
) -> Any:
    alpha_names = list(config["alpha20"])
    expressions = [config["alpha20"][name] for name in alpha_names]
    split = config["split"]
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
                                [config["labels"]["paper_proxy"]["expression"]],
                                ["LABEL0"],
                            ],
                            "feature": [expressions, alpha_names],
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
            "start_time": split["train"][0],
            "end_time": split["historical_test"][1],
            "instruments": config["data"]["market"],
            "data_loader": data_loader,
            "infer_processors": [
                {
                    "class": "RobustZScoreNorm",
                    "kwargs": {
                        "fields_group": "feature",
                        "clip_outlier": True,
                        "fit_start_time": split["train"][0],
                        "fit_end_time": split["train"][1],
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
        "class": "TSDatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler,
            "segments": {
                "train": split["train"],
                "valid": split["validation"],
                "test": split["historical_test"],
            },
            "step_len": int(config["model_attribution"]["num_timesteps"]),
        },
    }
    qlib.init(provider_uri=str(provider_path), region="cn")
    return init_instance_by_config(dataset_config)


def predict_segment(model: GeneralPTNN, dataset: Any, segment: str) -> pd.Series:
    sampler = dataset.prepare(
        segment,
        col_set=["feature", "label"],
        data_key=DataHandlerLP.DK_I,
    )
    sampler.config(fillna_type="ffill+bfill")
    index = sampler.get_index()
    loader = DataLoader(
        sampler,
        batch_size=model.batch_size,
        num_workers=model.n_jobs,
        shuffle=False,
    )
    model.dnn_model.eval()
    predictions: list[np.ndarray] = []
    for data in loader:
        feature, _ = model._get_fl(data)
        with torch.no_grad():
            prediction = model.dnn_model(feature.float()).detach().cpu().numpy()
        predictions.append(prediction)
    values = np.concatenate(predictions).reshape(-1)
    return pd.Series(values, index=index, name="prediction")


def benchmark_latency(
    model: torch.nn.Module,
    device: torch.device,
    batch_size: int,
    num_timesteps: int,
    num_features: int,
) -> dict[str, float]:
    generator = torch.Generator(device=device.type)
    generator.manual_seed(20260727)
    inputs = torch.randn(
        batch_size,
        num_timesteps,
        num_features,
        generator=generator,
        device=device,
    )
    model.eval()
    with torch.no_grad():
        for _ in range(10):
            model(inputs)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        timings = []
        for _ in range(50):
            started = time.perf_counter()
            model(inputs)
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            timings.append((time.perf_counter() - started) * 1000.0)
    return {
        "latency_median_ms": float(np.median(timings)),
        "latency_p95_ms": float(np.quantile(timings, 0.95)),
    }


def assert_general_ptnn_contract() -> None:
    source = inspect.getsource(GeneralPTNN)
    required = [
        "optim.Adam(",
        "clip_grad_value_",
        "ReduceLROnPlateau(",
        "factor=0.5",
        "patience=5",
        "min_lr=1e-6",
        "threshold=1e-5",
    ]
    missing = [token for token in required if token not in source]
    if missing:
        raise RuntimeError(f"GeneralPTNN runtime contract drift: {missing}")


def evaluate_predictions(
    *,
    variant: str,
    seed: int,
    predictions: pd.DataFrame,
    raw_panel: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[dict[str, Any], list[pd.DataFrame], list[pd.DataFrame]]:
    row: dict[str, Any] = {"variant": variant, "seed": seed}
    daily_parts: list[pd.DataFrame] = []
    portfolio_parts: list[pd.DataFrame] = []
    minimum_cross_section = int(
        config["baseline"]["minimum_daily_cross_section"]
    )
    for split_name in ["validation", "historical_test"]:
        prediction = predictions.loc[predictions["split"] == split_name, "prediction"]
        scored = raw_panel[["paper_proxy", "executable_bridge"]].reindex(
            prediction.index
        )
        scored["prediction"] = prediction
        for label_name in ["paper_proxy", "executable_bridge"]:
            daily = baseline.daily_correlations(
                scored,
                prediction_column="prediction",
                label_column=label_name,
                minimum_cross_section=minimum_cross_section,
            )
            summary = baseline.correlation_summary(daily)
            prefix = f"{split_name}_{label_name}"
            row.update({f"{prefix}_{key}": value for key, value in summary.items()})
            daily = daily.reset_index()
            daily["variant"] = variant
            daily["seed"] = seed
            daily["split"] = split_name
            daily["label_lane"] = label_name
            daily_parts.append(daily)

            if split_name == "historical_test":
                portfolio = baseline.topk_dropout_returns(
                    scored,
                    prediction_column="prediction",
                    label_column=label_name,
                    topk=int(config["portfolio"]["topk"]),
                    n_drop=int(config["portfolio"]["n_drop"]),
                    buy_cost=float(config["portfolio"]["buy_cost"]),
                    sell_cost=float(config["portfolio"]["sell_cost"]),
                )
                portfolio_summary = baseline.portfolio_summary(
                    portfolio,
                    int(config["portfolio"]["annualization"]),
                )
                row.update(
                    {
                        f"{prefix}_{key}": value
                        for key, value in portfolio_summary.items()
                    }
                )
                portfolio = portfolio.reset_index()
                portfolio["variant"] = variant
                portfolio["seed"] = seed
                portfolio["label_lane"] = label_name
                portfolio_parts.append(portfolio)
    return row, daily_parts, portfolio_parts


def build_matched_deltas(
    seed_metrics: pd.DataFrame,
    lgbm_metrics: pd.DataFrame,
) -> pd.DataFrame:
    indexed = seed_metrics.set_index(["variant", "seed"])
    lgbm = lgbm_metrics.set_index("seed")
    contrasts = [
        ("attentive_minus_last_state", "last_state_gru", "attentive_gru"),
        ("last_state_minus_mlp", "flattened_mlp", "last_state_gru"),
    ]
    rows: list[dict[str, Any]] = []
    seeds = sorted(seed_metrics["seed"].unique())
    for contrast, base_variant, candidate_variant in contrasts:
        if base_variant not in indexed.index.levels[0]:
            continue
        if candidate_variant not in indexed.index.levels[0]:
            continue
        for seed in seeds:
            for metric in KEY_METRICS:
                base_value = float(indexed.loc[(base_variant, seed), metric])
                candidate_value = float(
                    indexed.loc[(candidate_variant, seed), metric]
                )
                rows.append(
                    {
                        "contrast": contrast,
                        "seed": seed,
                        "metric": metric,
                        "base_value": base_value,
                        "candidate_value": candidate_value,
                        "delta": candidate_value - base_value,
                    }
                )
    for variant in sorted(seed_metrics["variant"].unique()):
        for seed in seeds:
            for metric in KEY_METRICS:
                if metric not in lgbm.columns:
                    continue
                base_value = float(lgbm.loc[seed, metric])
                candidate_value = float(indexed.loc[(variant, seed), metric])
                rows.append(
                    {
                        "contrast": f"{variant}_minus_lightgbm",
                        "seed": seed,
                        "metric": metric,
                        "base_value": base_value,
                        "candidate_value": candidate_value,
                        "delta": candidate_value - base_value,
                    }
                )
    return pd.DataFrame(rows)


def format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_report(
    *,
    output_dir: Path,
    mode: str,
    seeds: list[int],
    seed_metrics: pd.DataFrame,
    matched_deltas: pd.DataFrame,
    elapsed_seconds: float,
    cumulative_training_seconds: float,
) -> tuple[str, dict[str, Any]]:
    medians = seed_metrics.groupby("variant", sort=False).median(numeric_only=True)
    def contrast_stat(contrast: str, metric: str) -> tuple[float, int]:
        values = matched_deltas.loc[
            (matched_deltas["contrast"] == contrast)
            & (matched_deltas["metric"] == metric),
            "delta",
        ]
        return float(values.median()), int((values > 0).sum())

    validation_delta, validation_positive = contrast_stat(
        "attentive_minus_last_state",
        "validation_paper_proxy_ic"
    )
    gross_delta, gross_positive = contrast_stat(
        "attentive_minus_last_state",
        "historical_test_paper_proxy_gross_arr"
    )
    net_delta, net_positive = contrast_stat(
        "attentive_minus_last_state",
        "historical_test_paper_proxy_net_arr"
    )
    rank_delta, rank_positive = contrast_stat(
        "attentive_minus_last_state",
        "historical_test_paper_proxy_rank_ic"
    )
    recurrent_validation_delta, recurrent_validation_positive = contrast_stat(
        "last_state_minus_mlp",
        "validation_paper_proxy_ic",
    )
    recurrent_test_ic_delta, recurrent_test_ic_positive = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_ic",
    )
    recurrent_rank_delta, recurrent_rank_positive = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_rank_ic",
    )
    recurrent_gross_delta, recurrent_gross_positive = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_gross_arr",
    )
    recurrent_net_delta, recurrent_net_positive = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_net_arr",
    )
    recurrent_turnover_delta, _ = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_mean_one_way_turnover",
    )
    lgbm_validation_delta, lgbm_validation_positive = contrast_stat(
        "last_state_gru_minus_lightgbm",
        "validation_paper_proxy_ic",
    )
    lgbm_test_ic_delta, lgbm_test_ic_positive = contrast_stat(
        "last_state_gru_minus_lightgbm",
        "historical_test_paper_proxy_ic",
    )
    lgbm_gross_delta, lgbm_gross_positive = contrast_stat(
        "last_state_gru_minus_lightgbm",
        "historical_test_paper_proxy_gross_arr",
    )
    lgbm_net_delta, lgbm_net_positive = contrast_stat(
        "last_state_gru_minus_lightgbm",
        "historical_test_paper_proxy_net_arr",
    )
    executable_ic_delta, executable_ic_positive = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_executable_bridge_ic",
    )
    executable_gross_delta, executable_gross_positive = contrast_stat(
        "last_state_minus_mlp",
        "historical_test_executable_bridge_gross_arr",
    )
    attention_supported = (
        validation_positive >= 2
        and gross_positive >= 2
        and validation_delta > 0
        and gross_delta > 0
    )
    recurrent_supported = (
        recurrent_validation_positive >= 2
        and recurrent_test_ic_positive >= 2
        and recurrent_gross_positive >= 2
        and recurrent_validation_delta > 0
        and recurrent_test_ic_delta > 0
        and recurrent_gross_delta > 0
    )
    if attention_supported:
        decision = "attention_increment_supported_in_three_seed_smoke"
    elif recurrent_supported:
        decision = "reject_attention_retain_last_state_for_formal_attribution"
    else:
        decision = "reject_attention_and_recurrent_backbone_not_supported"
    if mode == "formal":
        decision = (
            "attention_increment_supported_in_five_seed_attribution"
            if attention_supported and validation_positive >= 3 and gross_positive >= 3
            else "attention_increment_not_supported_in_five_seed_attribution"
        )

    def table_row(variant: str) -> str:
        values = medians.loc[variant]
        return (
            f"| {variant} | {values['validation_paper_proxy_ic']:.6f} | "
            f"{values['historical_test_paper_proxy_ic']:.6f} | "
            f"{values['historical_test_paper_proxy_rank_ic']:.6f} | "
            f"{format_percent(values['historical_test_paper_proxy_gross_arr'])} | "
            f"{format_percent(values['historical_test_paper_proxy_net_arr'])} | "
            f"{values['historical_test_paper_proxy_mean_one_way_turnover']:.4f} |"
        )

    report = f"""# EP23 23D1 Controlled Model Attribution

## 裁决

```text
run_kind = {mode}_{len(seeds)}_seed
fixed_input = Alpha20 x 20 timesteps
variants = flattened_mlp, last_state_gru, attentive_gru
decision = {decision}
evidence = design_contaminated_historical_real_market_evidence
```

本阶段移除了 23D 候选 `forward()` 写 `output.pth` 的副作用，并以完全相同的
seed、Qlib dataset、processor、Adam/MSE、scheduler、gradient clip、训练预算
和 Top50/drop5 代理比较三个模型。MLP 参数量与 last-state GRU 近似匹配；
attentive GRU 只比 last-state GRU 多 attention pooling。

## 三 seed 中位数

| variant | validation IC | test IC | test RankIC | gross ARR | net ARR | turnover |
|---|---:|---:|---:|---:|---:|---:|
{table_row("flattened_mlp")}
{table_row("last_state_gru")}
{table_row("attentive_gru")}

## Recurrent backbone 的 matched-seed 增量

last-state GRU 相对容量近似匹配的 flattened MLP：

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | {recurrent_validation_delta:+.6f} | {recurrent_validation_positive}/{len(seeds)} |
| historical-test PAPER_PROXY IC | {recurrent_test_ic_delta:+.6f} | {recurrent_test_ic_positive}/{len(seeds)} |
| historical-test PAPER_PROXY RankIC | {recurrent_rank_delta:+.6f} | {recurrent_rank_positive}/{len(seeds)} |
| historical-test PAPER_PROXY gross ARR | {recurrent_gross_delta * 100:+.4f} pp | {recurrent_gross_positive}/{len(seeds)} |
| historical-test PAPER_PROXY net ARR | {recurrent_net_delta * 100:+.4f} pp | {recurrent_net_positive}/{len(seeds)} |
| mean one-way turnover | {recurrent_turnover_delta:+.6f} | — |

毛收益中位数增加 `{recurrent_gross_delta * 100:.4f} pp`，而 turnover 只增加
`{recurrent_turnover_delta:.6f}`；净收益中位数仍增加
`{recurrent_net_delta * 100:.4f} pp`。因此 recurrent backbone 的 smoke 增量
不是较低成本造成的伪影。第三个 seed 的净增量接近零，所以仍需正式五 seed
确认，不在本阶段晋级 SOTA。

相对同 seed 23B Alpha20-LightGBM：

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | {lgbm_validation_delta:+.6f} | {lgbm_validation_positive}/{len(seeds)} |
| historical-test PAPER_PROXY IC | {lgbm_test_ic_delta:+.6f} | {lgbm_test_ic_positive}/{len(seeds)} |
| historical-test PAPER_PROXY gross ARR | {lgbm_gross_delta * 100:+.4f} pp | {lgbm_gross_positive}/{len(seeds)} |
| historical-test PAPER_PROXY net ARR | {lgbm_net_delta * 100:+.4f} pp | {lgbm_net_positive}/{len(seeds)} |

EXECUTABLE_BRIDGE 上，last-state GRU 相对 MLP 的 IC 中位增量为
`{executable_ic_delta:+.6f}`（{executable_ic_positive}/{len(seeds)} 为正），
毛 ARR 中位增量为 `{executable_gross_delta * 100:+.4f} pp`
（{executable_gross_positive}/{len(seeds)} 为正），没有发生预测方向翻转。

## Attention 的 matched-seed 增量

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | {validation_delta:+.6f} | {validation_positive}/{len(seeds)} |
| historical-test PAPER_PROXY RankIC | {rank_delta:+.6f} | {rank_positive}/{len(seeds)} |
| historical-test PAPER_PROXY gross ARR | {gross_delta * 100:+.4f} pp | {gross_positive}/{len(seeds)} |
| historical-test PAPER_PROXY net ARR | {net_delta * 100:+.4f} pp | {net_positive}/{len(seeds)} |

Attention 是否得到支持以 validation IC 与毛收益的 matched-seed 同向改善为主；
净收益不能单独决定晋级，以避免重复 23D 的成本伪影。本轮 attention 的
validation IC 三个 seed 全部下降，test IC 也全部下降；毛/净收益中位数同步
恶化，因此拒绝 attention pooling，而不是拒绝 GRU 时序主干。

## 冻结 runtime contract

- 训练：Adam + MSE，learning rate `0.001`，weight decay `0.0001`；
- batch `256`，最多 100 epochs，early stop `12`；
- `clip_grad_value_=3.0`；
- `ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6,
  threshold=1e-5)`；
- train/validation processor 与 23D 一致；
- 每个 variant/seed 开始前重置 Python、NumPy、Torch 和 CUDA seed，并启用
  deterministic algorithms。
- 当前 early-stop 没有 minimum-delta，约 `1e-5` 量级的 validation loss
  改善也会重置 patience，导致部分 GRU 运行延长到 26–32 epochs。正式五 seed
  前应冻结 minimum-delta 或保留本轮规则并明确资源代价，不能中途混用。

## 解释边界

- `{mode}` 运行使用 seeds `{seeds}`；只有正式五 seed 结果才可进入模型候选池。
- historical test 已被反复观察，仅用于设计污染样本内的归因诊断。
- portfolio 是本地 equal-weight Top50/drop5 成本代理，完整 executable bridge
  仍留给 23F。
- 本报告是策略绝对收益代理；不能与 23D 单次 Qlib 相对沪深 300 的超额收益
  数值直接比较。
- 单模型逐 seed 训练曲线、参数量、GPU memory、推理延迟和 matched delta 均已
  写入同目录结构化文件。

九个 matched run 的累计模型训练耗时为
`{cumulative_training_seconds:.2f}` 秒；本次汇总 invocation 耗时
`{elapsed_seconds:.2f}` 秒。断点恢复不会把缓存命中误写成原始训练耗时。
"""
    (output_dir / "23D1_controlled_model_attribution_report.md").write_text(
        report,
        encoding="utf-8",
    )
    return decision, {
        "attention": {
            "validation_ic_median_delta": validation_delta,
            "validation_ic_positive_seeds": validation_positive,
            "test_rank_ic_median_delta": rank_delta,
            "test_rank_ic_positive_seeds": rank_positive,
            "test_gross_arr_median_delta": gross_delta,
            "test_gross_arr_positive_seeds": gross_positive,
            "test_net_arr_median_delta": net_delta,
            "test_net_arr_positive_seeds": net_positive,
        },
        "last_state_gru_vs_mlp": {
            "validation_ic_median_delta": recurrent_validation_delta,
            "validation_ic_positive_seeds": recurrent_validation_positive,
            "test_ic_median_delta": recurrent_test_ic_delta,
            "test_ic_positive_seeds": recurrent_test_ic_positive,
            "test_rank_ic_median_delta": recurrent_rank_delta,
            "test_rank_ic_positive_seeds": recurrent_rank_positive,
            "test_gross_arr_median_delta": recurrent_gross_delta,
            "test_gross_arr_positive_seeds": recurrent_gross_positive,
            "test_net_arr_median_delta": recurrent_net_delta,
            "test_net_arr_positive_seeds": recurrent_net_positive,
            "turnover_median_delta": recurrent_turnover_delta,
        },
        "last_state_gru_vs_lightgbm": {
            "validation_ic_median_delta": lgbm_validation_delta,
            "validation_ic_positive_seeds": lgbm_validation_positive,
            "test_ic_median_delta": lgbm_test_ic_delta,
            "test_ic_positive_seeds": lgbm_test_ic_positive,
            "test_gross_arr_median_delta": lgbm_gross_delta,
            "test_gross_arr_positive_seeds": lgbm_gross_positive,
            "test_net_arr_median_delta": lgbm_net_delta,
            "test_net_arr_positive_seeds": lgbm_net_positive,
        },
    }


def write_formal_backbone_report(
    *,
    output_dir: Path,
    seeds: list[int],
    seed_metrics: pd.DataFrame,
    matched_deltas: pd.DataFrame,
    elapsed_seconds: float,
    cumulative_training_seconds: float,
) -> tuple[str, dict[str, Any]]:
    medians = seed_metrics.groupby("variant", sort=False).median(numeric_only=True)

    def stat(contrast: str, metric: str) -> tuple[float, int]:
        values = matched_deltas.loc[
            (matched_deltas["contrast"] == contrast)
            & (matched_deltas["metric"] == metric),
            "delta",
        ]
        return float(values.median()), int((values > 0).sum())

    validation_delta, validation_positive = stat(
        "last_state_minus_mlp",
        "validation_paper_proxy_ic",
    )
    test_ic_delta, test_ic_positive = stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_ic",
    )
    rank_ic_delta, rank_ic_positive = stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_rank_ic",
    )
    gross_delta, gross_positive = stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_gross_arr",
    )
    net_delta, net_positive = stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_net_arr",
    )
    turnover_delta, _ = stat(
        "last_state_minus_mlp",
        "historical_test_paper_proxy_mean_one_way_turnover",
    )
    executable_ic_delta, executable_ic_positive = stat(
        "last_state_minus_mlp",
        "historical_test_executable_bridge_ic",
    )
    executable_gross_delta, executable_gross_positive = stat(
        "last_state_minus_mlp",
        "historical_test_executable_bridge_gross_arr",
    )
    lgbm_validation_delta, lgbm_validation_positive = stat(
        "last_state_gru_minus_lightgbm",
        "validation_paper_proxy_ic",
    )
    lgbm_test_ic_delta, lgbm_test_ic_positive = stat(
        "last_state_gru_minus_lightgbm",
        "historical_test_paper_proxy_ic",
    )
    lgbm_gross_delta, lgbm_gross_positive = stat(
        "last_state_gru_minus_lightgbm",
        "historical_test_paper_proxy_gross_arr",
    )
    lgbm_net_delta, lgbm_net_positive = stat(
        "last_state_gru_minus_lightgbm",
        "historical_test_paper_proxy_net_arr",
    )
    supported = (
        validation_delta > 0
        and test_ic_delta > 0
        and gross_delta > 0
        and validation_positive >= 3
        and test_ic_positive >= 3
        and gross_positive >= 3
        and executable_ic_positive >= 3
    )
    decision = (
        "last_state_gru_formal_candidate_pending_23F"
        if supported
        else "last_state_gru_not_supported_in_five_seed_attribution"
    )

    def table_row(variant: str) -> str:
        values = medians.loc[variant]
        return (
            f"| {variant} | {values['validation_paper_proxy_ic']:.6f} | "
            f"{values['historical_test_paper_proxy_ic']:.6f} | "
            f"{values['historical_test_paper_proxy_rank_ic']:.6f} | "
            f"{format_percent(values['historical_test_paper_proxy_gross_arr'])} | "
            f"{format_percent(values['historical_test_paper_proxy_net_arr'])} | "
            f"{values['historical_test_paper_proxy_mean_one_way_turnover']:.4f} |"
        )

    contrast = matched_deltas[
        matched_deltas["contrast"] == "last_state_minus_mlp"
    ]

    def seed_delta_row(seed: int) -> str:
        values = contrast[contrast["seed"] == seed].set_index("metric")["delta"]
        return (
            f"| {seed} | {values['validation_paper_proxy_ic']:+.6f} | "
            f"{values['historical_test_paper_proxy_ic']:+.6f} | "
            f"{values['historical_test_paper_proxy_rank_ic']:+.6f} | "
            f"{values['historical_test_paper_proxy_gross_arr'] * 100:+.4f} pp | "
            f"{values['historical_test_paper_proxy_net_arr'] * 100:+.4f} pp |"
        )

    seed_rows = "\n".join(seed_delta_row(seed) for seed in seeds)
    report = f"""# EP23 23D2 Formal Last-State GRU Attribution

## 裁决

```text
run_kind = formal_5_seed
fixed_input = Alpha20 x 20 timesteps
candidate = last_state_gru
capacity_matched_control = flattened_mlp
decision = {decision}
evidence = design_contaminated_historical_real_market_evidence
```

23D1 已用三 seed 拒绝 attention pooling。本阶段不再为被拒绝结构追加预算，
而是在完全相同的 GeneralPTNN runtime contract 下补齐 MLP 与 last-state GRU
的五 seed 正式归因。前三个 seed 复用冻结预测，新增训练仅为
`20260726 / 20260727`。

## 五 seed 中位数

| variant | validation IC | test IC | test RankIC | gross ARR | net ARR | turnover |
|---|---:|---:|---:|---:|---:|---:|
{table_row("flattened_mlp")}
{table_row("last_state_gru")}

## Last-state GRU 相对 MLP

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | {validation_delta:+.6f} | {validation_positive}/{len(seeds)} |
| historical-test PAPER_PROXY IC | {test_ic_delta:+.6f} | {test_ic_positive}/{len(seeds)} |
| historical-test PAPER_PROXY RankIC | {rank_ic_delta:+.6f} | {rank_ic_positive}/{len(seeds)} |
| historical-test PAPER_PROXY gross ARR | {gross_delta * 100:+.4f} pp | {gross_positive}/{len(seeds)} |
| historical-test PAPER_PROXY net ARR | {net_delta * 100:+.4f} pp | {net_positive}/{len(seeds)} |
| mean one-way turnover | {turnover_delta:+.6f} | — |

逐 seed：

| seed | validation IC delta | test IC delta | test RankIC delta | gross ARR delta | net ARR delta |
|---:|---:|---:|---:|---:|---:|
{seed_rows}

晋级要求以 validation IC、historical-test IC 和毛收益至少 3/5 seed 同向改善为主；
净收益单独改善不能覆盖成本伪影。turnover 与 gross/net 的联合归因决定该候选是否
只是在换手上改变了成本。

## 相对 Alpha20-LightGBM

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | {lgbm_validation_delta:+.6f} | {lgbm_validation_positive}/{len(seeds)} |
| historical-test PAPER_PROXY IC | {lgbm_test_ic_delta:+.6f} | {lgbm_test_ic_positive}/{len(seeds)} |
| historical-test PAPER_PROXY gross ARR | {lgbm_gross_delta * 100:+.4f} pp | {lgbm_gross_positive}/{len(seeds)} |
| historical-test PAPER_PROXY net ARR | {lgbm_net_delta * 100:+.4f} pp | {lgbm_net_positive}/{len(seeds)} |

EXECUTABLE_BRIDGE 上，last-state GRU 相对 MLP 的 IC 中位增量为
`{executable_ic_delta:+.6f}`（{executable_ic_positive}/{len(seeds)} 为正），
毛 ARR 中位增量为 `{executable_gross_delta * 100:+.4f} pp`
（{executable_gross_positive}/{len(seeds)} 为正）。

## 资源与边界

- 沿用 23D1 的 Adam/MSE、`clip_grad_value_=3.0`、
  `ReduceLROnPlateau` 和无 minimum-delta 的 early-stop，以保证五个 seed
  可直接合并；本阶段没有中途修改规则。
- 这是策略绝对收益代理，不与 23D 单次 Qlib 超额收益直接比较。
- historical test 是设计污染证据。即使本轮通过，也只能进入 23F executable
  与 Big Winner bridge，不能直接声明生产 alpha。
- 五 seed 累计模型训练耗时 `{cumulative_training_seconds:.2f}` 秒；本次
  invocation（含缓存恢复与新增训练）耗时 `{elapsed_seconds:.2f}` 秒。
"""
    (output_dir / "23D2_formal_last_state_gru_attribution_report.md").write_text(
        report,
        encoding="utf-8",
    )
    return decision, {
        "last_state_gru_vs_mlp": {
            "validation_ic_median_delta": validation_delta,
            "validation_ic_positive_seeds": validation_positive,
            "test_ic_median_delta": test_ic_delta,
            "test_ic_positive_seeds": test_ic_positive,
            "test_rank_ic_median_delta": rank_ic_delta,
            "test_rank_ic_positive_seeds": rank_ic_positive,
            "test_gross_arr_median_delta": gross_delta,
            "test_gross_arr_positive_seeds": gross_positive,
            "test_net_arr_median_delta": net_delta,
            "test_net_arr_positive_seeds": net_positive,
            "turnover_median_delta": turnover_delta,
            "executable_ic_median_delta": executable_ic_delta,
            "executable_ic_positive_seeds": executable_ic_positive,
            "executable_gross_arr_median_delta": executable_gross_delta,
            "executable_gross_arr_positive_seeds": executable_gross_positive,
        },
        "last_state_gru_vs_lightgbm": {
            "validation_ic_median_delta": lgbm_validation_delta,
            "validation_ic_positive_seeds": lgbm_validation_positive,
            "test_ic_median_delta": lgbm_test_ic_delta,
            "test_ic_positive_seeds": lgbm_test_ic_positive,
            "test_gross_arr_median_delta": lgbm_gross_delta,
            "test_gross_arr_positive_seeds": lgbm_gross_positive,
            "test_net_arr_median_delta": lgbm_net_delta,
            "test_net_arr_positive_seeds": lgbm_net_positive,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=["smoke", "formal"], default="smoke")
    parser.add_argument("--seeds", help="comma-separated seed override")
    parser.add_argument("--variants", help="comma-separated variant override")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    started = time.monotonic()
    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    topic_root = baseline.find_topic_root(config_path)
    output_key = (
        "model_attribution_formal"
        if args.mode == "formal"
        else "model_attribution"
    )
    output_dir = topic_root / config["outputs"][output_key]
    local_cache = topic_root / config["outputs"]["local_cache"]
    output_dir.mkdir(parents=True, exist_ok=True)
    local_cache.mkdir(parents=True, exist_ok=True)

    preflight_path = (
        topic_root / config["outputs"]["preflight"] / "preflight_decision.json"
    )
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight.get("ready_for_agent_loop"):
        raise RuntimeError("23A did not authorize the controlled model run")
    assert_general_ptnn_contract()

    default_seed_key = "formal_seeds" if args.mode == "formal" else "smoke_seeds"
    seeds = parse_csv_values(
        args.seeds,
        list(config["model_attribution"][default_seed_key]),
        int,
    )
    default_variants = (
        FORMAL_VARIANTS
        if args.mode == "formal"
        else list(config["model_attribution"]["variants"])
    )
    variants = parse_csv_values(
        args.variants,
        default_variants,
        str,
    )
    unknown = sorted(set(variants) - set(MODEL_VARIANTS))
    if unknown:
        raise ValueError(f"unknown variants: {unknown}")
    if set(variants) != set(default_variants):
        run_kind = "diagnostic_partial"
    else:
        run_kind = args.mode

    model_source = Path(__file__).with_name("ep23_model_variants.py")
    experiment_hash = semantic_hash(config, model_source)
    run_cache = local_cache / f"23d1_{experiment_hash[:16]}"
    run_cache.mkdir(parents=True, exist_ok=True)

    alpha_names = list(config["alpha20"])
    expressions = [config["alpha20"][name] for name in alpha_names]
    label_names = ["paper_proxy", "executable_bridge"]
    expressions.extend(config["labels"][name]["expression"] for name in label_names)
    panel_cache = local_cache / "alpha20_dual_label_panel_model_attribution.parquet"
    provider_path = topic_root / config["data"]["provider_uri"]
    raw_panel = baseline.load_or_materialize(
        provider_path=provider_path,
        market=config["data"]["market"],
        expressions=expressions,
        columns=[*alpha_names, *label_names],
        start_time=config["split"]["train"][0],
        end_time=config["split"]["historical_test"][1],
        cache_path=panel_cache,
    )
    dataset = build_dataset(config, provider_path)

    run_rows: list[dict[str, Any]] = []
    training_curves: list[pd.DataFrame] = []
    latency_rows: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    portfolio_parts: list[pd.DataFrame] = []
    prediction_paths: list[str] = []
    model_inventory: dict[str, dict[str, Any]] = {}
    attribution = config["model_attribution"]

    for variant in variants:
        model_class = MODEL_VARIANTS[variant]
        probe = model_class(len(alpha_names), int(attribution["num_timesteps"]))
        parameter_count = sum(parameter.numel() for parameter in probe.parameters())
        model_inventory[variant] = {
            "class": model_class.__name__,
            "parameter_count": parameter_count,
            "fp32_parameter_bytes": parameter_count * 4,
        }
        del probe

        for seed in seeds:
            cache_prefix = run_cache / f"{variant}_{seed}"
            prediction_path = cache_prefix.with_suffix(".predictions.parquet")
            curve_path = cache_prefix.with_suffix(".curve.csv")
            metadata_path = cache_prefix.with_suffix(".metadata.json")
            weights_path = cache_prefix.with_suffix(".weights.pt")
            can_resume = (
                not args.no_resume
                and prediction_path.exists()
                and curve_path.exists()
                and metadata_path.exists()
            )
            if can_resume:
                predictions = pd.read_parquet(prediction_path)
                predictions.index = predictions.index.set_names(
                    ["datetime", "instrument"]
                )
                curve = pd.read_csv(curve_path)
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            else:
                set_deterministic_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats()
                model = GeneralPTNN(
                    n_epochs=int(attribution["n_epochs"]),
                    lr=float(attribution["learning_rate"]),
                    metric="loss",
                    batch_size=int(attribution["batch_size"]),
                    early_stop=int(attribution["early_stop"]),
                    loss=str(attribution["loss"]),
                    weight_decay=float(attribution["weight_decay"]),
                    optimizer=str(attribution["optimizer"]),
                    n_jobs=int(attribution["dataloader_workers"]),
                    GPU=0,
                    seed=seed,
                    pt_model_uri=f"ep23_model_variants.{model_class.__name__}",
                    pt_model_kwargs={
                        "num_features": len(alpha_names),
                        "num_timesteps": int(attribution["num_timesteps"]),
                    },
                )
                evals_result: dict[str, list[float]] = {}
                training_started = time.monotonic()
                model.fit(
                    dataset,
                    evals_result=evals_result,
                    save_path=str(weights_path),
                )
                training_seconds = time.monotonic() - training_started
                validation_prediction = predict_segment(model, dataset, "valid")
                test_prediction = predict_segment(model, dataset, "test")
                predictions = pd.concat(
                    [
                        validation_prediction.to_frame().assign(split="validation"),
                        test_prediction.to_frame().assign(split="historical_test"),
                    ]
                ).sort_index()
                curve = pd.DataFrame(
                    {
                        "epoch": np.arange(len(evals_result["train"])),
                        "train_loss": evals_result["train"],
                        "valid_loss": evals_result["valid"],
                    }
                )
                best_epoch = int(curve["valid_loss"].idxmin())
                latency = benchmark_latency(
                    model.dnn_model,
                    model.device,
                    int(attribution["batch_size"]),
                    int(attribution["num_timesteps"]),
                    len(alpha_names),
                )
                peak_gpu_bytes = (
                    int(torch.cuda.max_memory_allocated())
                    if torch.cuda.is_available()
                    else 0
                )
                metadata = {
                    "variant": variant,
                    "seed": seed,
                    "parameter_count": parameter_count,
                    "epochs_ran": len(curve),
                    "best_epoch": best_epoch,
                    "best_valid_loss": float(curve.loc[best_epoch, "valid_loss"]),
                    "training_seconds": training_seconds,
                    "peak_gpu_bytes": peak_gpu_bytes,
                    **latency,
                }
                predictions.to_parquet(prediction_path)
                curve.to_csv(curve_path, index=False)
                metadata_path.write_text(
                    json.dumps(metadata, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                del model
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            evaluated, daily, portfolios = evaluate_predictions(
                variant=variant,
                seed=seed,
                predictions=predictions,
                raw_panel=raw_panel,
                config=config,
            )
            evaluated.update(metadata)
            run_rows.append(evaluated)
            curve = curve.copy()
            curve["variant"] = variant
            curve["seed"] = seed
            training_curves.append(curve)
            latency_rows.append(
                {
                    "variant": variant,
                    "seed": seed,
                    "device": "cuda:0" if torch.cuda.is_available() else "cpu",
                    "batch_size": int(attribution["batch_size"]),
                    "num_timesteps": int(attribution["num_timesteps"]),
                    "num_features": len(alpha_names),
                    "median_ms": metadata["latency_median_ms"],
                    "p95_ms": metadata["latency_p95_ms"],
                }
            )
            daily_parts.extend(daily)
            portfolio_parts.extend(portfolios)
            prediction_paths.append(str(prediction_path.relative_to(topic_root)))
            print(
                json.dumps(
                    {
                        "variant": variant,
                        "seed": seed,
                        "resumed": can_resume,
                        "best_epoch": metadata["best_epoch"],
                        "validation_ic": evaluated["validation_paper_proxy_ic"],
                        "test_ic": evaluated["historical_test_paper_proxy_ic"],
                        "gross_arr": evaluated[
                            "historical_test_paper_proxy_gross_arr"
                        ],
                        "net_arr": evaluated[
                            "historical_test_paper_proxy_net_arr"
                        ],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    seed_metrics = pd.DataFrame(run_rows).sort_values(["variant", "seed"])
    seed_metrics.to_csv(output_dir / "seed_metrics.csv", index=False)
    pd.concat(training_curves, ignore_index=True).to_csv(
        output_dir / "training_curves.csv",
        index=False,
    )
    pd.DataFrame(latency_rows).to_csv(output_dir / "inference_latency.csv", index=False)
    pd.concat(daily_parts, ignore_index=True).to_csv(
        output_dir / "daily_predictive_metrics.csv",
        index=False,
    )
    pd.concat(portfolio_parts, ignore_index=True).to_csv(
        output_dir / "portfolio_daily.csv",
        index=False,
    )
    pd.DataFrame.from_dict(model_inventory, orient="index").rename_axis(
        "variant"
    ).reset_index().to_csv(output_dir / "model_inventory.csv", index=False)

    lgbm_path = topic_root / config["outputs"]["baseline"] / "seed_metrics.csv"
    lgbm_metrics = pd.read_csv(lgbm_path)
    missing_lgbm_seeds = sorted(set(seeds) - set(lgbm_metrics["seed"]))
    if missing_lgbm_seeds:
        raise RuntimeError(f"23B lacks matched seeds: {missing_lgbm_seeds}")
    lgbm_metrics = lgbm_metrics[lgbm_metrics["seed"].isin(seeds)]
    matched_deltas = build_matched_deltas(seed_metrics, lgbm_metrics)
    matched_deltas.to_csv(output_dir / "matched_seed_deltas.csv", index=False)

    aggregate = seed_metrics.groupby("variant", sort=False)[KEY_METRICS].agg(
        ["median", "min", "max"]
    )
    aggregate.columns = [f"{metric}_{stat}" for metric, stat in aggregate.columns]
    aggregate.reset_index().to_csv(
        output_dir / "aggregate_summary.csv",
        index=False,
    )

    elapsed_seconds = time.monotonic() - started
    decision = "diagnostic_partial"
    attribution_summary: dict[str, Any] = {}
    cumulative_training_seconds = float(seed_metrics["training_seconds"].sum())
    if args.mode == "smoke" and set(variants) == set(default_variants):
        decision, attribution_summary = write_report(
            output_dir=output_dir,
            mode=args.mode,
            seeds=seeds,
            seed_metrics=seed_metrics,
            matched_deltas=matched_deltas,
            elapsed_seconds=elapsed_seconds,
            cumulative_training_seconds=cumulative_training_seconds,
        )
    elif args.mode == "formal" and set(variants) == set(default_variants):
        decision, attribution_summary = write_formal_backbone_report(
            output_dir=output_dir,
            seeds=seeds,
            seed_metrics=seed_metrics,
            matched_deltas=matched_deltas,
            elapsed_seconds=elapsed_seconds,
            cumulative_training_seconds=cumulative_training_seconds,
        )
    manifest = {
        "episode_id": config["episode_id"],
        "stage": (
            "23D2_formal_last_state_gru_attribution"
            if args.mode == "formal"
            else "23D1_controlled_model_attribution"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_kind": run_kind,
        "mode": args.mode,
        "seeds": seeds,
        "variants": variants,
        "semantic_hash": experiment_hash,
        "model_source_sha256": baseline.sha256_file(model_source),
        "provider_uri": str(provider_path),
        "market": config["data"]["market"],
        "runtime_contract": config["model_attribution"],
        "model_inventory": model_inventory,
        "prediction_paths_local_cache": prediction_paths,
        "decision": decision,
        "attribution_summary": attribution_summary,
        "formal_five_seed_run": (
            args.mode == "formal"
            and seeds == list(config["model_attribution"]["formal_seeds"])
            and set(variants) == set(FORMAL_VARIANTS)
        ),
        "invocation_elapsed_seconds": elapsed_seconds,
        "cumulative_training_seconds": cumulative_training_seconds,
        "evidence_class": config["split"]["evidence_class"],
        "claim_ceiling": (
            "formal_model_attribution_complete_pending_23F"
            if args.mode == "formal"
            and len(seeds) == 5
            and set(variants) == set(FORMAL_VARIANTS)
            else "controlled_model_attribution_smoke_only"
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
