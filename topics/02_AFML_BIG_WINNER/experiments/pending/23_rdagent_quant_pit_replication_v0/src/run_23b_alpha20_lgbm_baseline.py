#!/usr/bin/env python3
"""Deterministic Alpha20/LightGBM PIT baseline for EP23."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.data import D


def find_topic_root(config_path: Path) -> Path:
    for parent in [config_path.parent, *config_path.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "data").is_dir():
            return parent
    raise RuntimeError(f"cannot resolve topic root from {config_path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.index.names) == ["instrument", "datetime"]:
        frame = frame.swaplevel()
    frame.index = frame.index.set_names(["datetime", "instrument"])
    return frame.sort_index()


def cross_sectional_zscore(series: pd.Series) -> pd.Series:
    def scale(group: pd.Series) -> pd.Series:
        std = group.std(ddof=0)
        if not np.isfinite(std) or std <= 1e-12:
            return pd.Series(np.nan, index=group.index)
        return (group - group.mean()) / std

    return series.groupby(level="datetime", group_keys=False).apply(scale)


def fit_robust_transform(
    train: pd.DataFrame, clip: float
) -> tuple[pd.Series, pd.Series]:
    median = train.median(axis=0, skipna=True)
    mad = (train - median).abs().median(axis=0, skipna=True)
    scale = 1.4826 * mad
    fallback = train.std(axis=0, ddof=0)
    scale = scale.where((scale > 1e-12) & np.isfinite(scale), fallback)
    scale = scale.where((scale > 1e-12) & np.isfinite(scale), 1.0)
    return median, scale


def apply_robust_transform(
    frame: pd.DataFrame, median: pd.Series, scale: pd.Series, clip: float
) -> pd.DataFrame:
    transformed = (frame - median) / scale
    transformed = transformed.clip(lower=-clip, upper=clip).fillna(0.0)
    return transformed.astype("float32")


def daily_correlations(
    frame: pd.DataFrame,
    prediction_column: str,
    label_column: str,
    minimum_cross_section: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, group in frame[[prediction_column, label_column]].groupby(
        level="datetime"
    ):
        clean = group.dropna()
        if len(clean) < minimum_cross_section:
            continue
        rows.append(
            {
                "datetime": pd.Timestamp(date),
                "n": len(clean),
                "ic": clean[prediction_column].corr(
                    clean[label_column], method="pearson"
                ),
                "rank_ic": clean[prediction_column].corr(
                    clean[label_column], method="spearman"
                ),
            }
        )
    return pd.DataFrame(rows).set_index("datetime").sort_index()


def correlation_summary(daily: pd.DataFrame) -> dict[str, float]:
    result: dict[str, float] = {}
    for column in ["ic", "rank_ic"]:
        values = daily[column].dropna()
        mean = float(values.mean())
        std = float(values.std(ddof=1))
        result[column] = mean
        result[f"{column}ir"] = mean / std if std > 0 else math.nan
    result["metric_days"] = int(len(daily))
    return result


def topk_dropout_returns(
    frame: pd.DataFrame,
    *,
    prediction_column: str,
    label_column: str,
    topk: int,
    n_drop: int,
    buy_cost: float,
    sell_cost: float,
) -> pd.DataFrame:
    holdings: set[str] = set()
    rows: list[dict[str, Any]] = []
    for date, group in frame[[prediction_column, label_column]].groupby(
        level="datetime"
    ):
        clean = group.dropna().reset_index("datetime", drop=True)
        clean = clean[~clean.index.duplicated(keep="last")]
        if len(clean) < topk:
            continue
        ranked = clean.sort_values(
            prediction_column, ascending=False, kind="mergesort"
        )
        available = set(ranked.index.astype(str))
        prior = holdings & available
        forced_sells = holdings - available
        prior_ranked = [instrument for instrument in ranked.index if instrument in prior]
        optional_drop = set(prior_ranked[-min(n_drop, len(prior_ranked)) :])
        retained = prior - optional_drop
        slots = topk - len(retained)
        additions = [
            str(instrument)
            for instrument in ranked.index
            if str(instrument) not in retained
        ][:slots]
        new_holdings = set(retained) | set(additions)
        sold = (holdings - new_holdings) | forced_sells
        bought = new_holdings - holdings
        gross_return = float(clean.loc[list(new_holdings), label_column].mean())
        universe_return = float(clean[label_column].mean())
        buy_fraction = len(bought) / topk
        sell_fraction = len(sold) / topk
        cost = buy_fraction * buy_cost + sell_fraction * sell_cost
        rows.append(
            {
                "datetime": pd.Timestamp(date),
                "gross_return": gross_return,
                "net_return": gross_return - cost,
                "universe_equal_weight_return": universe_return,
                "buy_fraction": buy_fraction,
                "sell_fraction": sell_fraction,
                "one_way_turnover": 0.5 * (buy_fraction + sell_fraction),
                "cost": cost,
                "holdings": len(new_holdings),
            }
        )
        holdings = new_holdings
    return pd.DataFrame(rows).set_index("datetime").sort_index()


def portfolio_summary(daily: pd.DataFrame, annualization: int) -> dict[str, float]:
    returns = daily["net_return"].dropna()
    gross = daily["gross_return"].dropna()
    universe = daily["universe_equal_weight_return"].dropna()
    if returns.empty:
        return {}
    net_nav = (1.0 + returns).cumprod()
    gross_nav = (1.0 + gross).cumprod()
    universe_nav = (1.0 + universe).cumprod()
    years = len(returns) / annualization
    arr = float(net_nav.iloc[-1] ** (1.0 / years) - 1.0)
    gross_arr = float(gross_nav.iloc[-1] ** (1.0 / years) - 1.0)
    universe_arr = float(universe_nav.iloc[-1] ** (1.0 / years) - 1.0)
    std = float(returns.std(ddof=1))
    ir = float(returns.mean() / std * math.sqrt(annualization)) if std > 0 else math.nan
    active = returns - universe.reindex(returns.index)
    active_std = float(active.std(ddof=1))
    active_ir = (
        float(active.mean() / active_std * math.sqrt(annualization))
        if active_std > 0
        else math.nan
    )
    drawdown = net_nav / net_nav.cummax() - 1.0
    mdd = float(drawdown.min())
    return {
        "gross_arr": gross_arr,
        "net_arr": arr,
        "universe_equal_weight_arr": universe_arr,
        "net_arr_minus_universe_arr": arr - universe_arr,
        "ir": ir,
        "active_ir_vs_universe_equal_weight": active_ir,
        "mdd": mdd,
        "calmar": arr / abs(mdd) if mdd < 0 else math.nan,
        "mean_one_way_turnover": float(daily["one_way_turnover"].mean()),
        "total_cost": float(daily["cost"].sum()),
        "portfolio_days": int(len(daily)),
    }


def load_or_materialize(
    *,
    provider_path: Path,
    market: str,
    expressions: list[str],
    columns: list[str],
    start_time: str,
    end_time: str,
    cache_path: Path,
) -> pd.DataFrame:
    if cache_path.exists():
        frame = pd.read_parquet(cache_path)
        frame.index = frame.index.set_names(["datetime", "instrument"])
        if list(frame.columns) == columns:
            return frame.sort_index()
    qlib.init(provider_uri=str(provider_path), region="cn")
    frame = D.features(
        D.instruments(market),
        expressions,
        start_time=start_time,
        end_time=end_time,
        freq="day",
    )
    frame = normalize_feature_frame(frame)
    frame.columns = columns
    frame = frame.replace([np.inf, -np.inf], np.nan)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(cache_path)
    return frame


def parse_seed_override(value: str | None, default: list[int]) -> list[int]:
    if value is None:
        return default
    seeds = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not seeds:
        raise ValueError("--seeds did not contain an integer")
    return seeds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--seeds",
        help="comma-separated seed override; omit for the frozen five-seed run",
    )
    args = parser.parse_args()

    started = time.monotonic()
    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    topic_root = find_topic_root(config_path)
    output_dir = topic_root / config["outputs"]["baseline"]
    local_cache = topic_root / config["outputs"]["local_cache"]
    output_dir.mkdir(parents=True, exist_ok=True)
    local_cache.mkdir(parents=True, exist_ok=True)

    preflight_path = (
        topic_root / config["outputs"]["preflight"] / "preflight_decision.json"
    )
    if not preflight_path.exists():
        raise RuntimeError("23A preflight must be run before 23B")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if not preflight.get("ready_for_deterministic_baseline"):
        raise RuntimeError("23A did not authorize the deterministic baseline")

    alpha_names = list(config["alpha20"])
    expressions = [config["alpha20"][name] for name in alpha_names]
    label_names = ["paper_proxy", "executable_bridge"]
    expressions.extend(
        config["labels"][name]["expression"] for name in label_names
    )
    columns = [*alpha_names, *label_names]
    config_sha = sha256_file(config_path)
    cache_path = local_cache / f"alpha20_dual_label_panel_{config_sha[:12]}.parquet"
    provider_path = topic_root / config["data"]["provider_uri"]
    frame = load_or_materialize(
        provider_path=provider_path,
        market=config["data"]["market"],
        expressions=expressions,
        columns=columns,
        start_time=config["data"]["expected_calendar_start"],
        end_time=config["data"]["expected_calendar_end"],
        cache_path=cache_path,
    )

    split_frames: dict[str, pd.DataFrame] = {}
    for split_name in ["train", "validation", "historical_test"]:
        start, end = config["split"][split_name]
        split_frame = frame.loc[
            (slice(pd.Timestamp(start), pd.Timestamp(end)), slice(None)), :
        ].copy()
        split_frame = split_frame[split_frame["paper_proxy"].notna()]
        split_frames[split_name] = split_frame

    clip = float(config["baseline"]["robust_zscore_clip"])
    median, scale = fit_robust_transform(
        split_frames["train"][alpha_names], clip=clip
    )
    transformed = {
        name: apply_robust_transform(part[alpha_names], median, scale, clip)
        for name, part in split_frames.items()
    }
    targets = {
        name: cross_sectional_zscore(part["paper_proxy"])
        for name, part in split_frames.items()
    }
    valid_target_mask = targets["validation"].notna()
    train_target_mask = targets["train"].notna()
    X_train = transformed["train"].loc[train_target_mask]
    y_train = targets["train"].loc[train_target_mask].astype("float32")
    X_valid = transformed["validation"].loc[valid_target_mask]
    y_valid = targets["validation"].loc[valid_target_mask].astype("float32")

    seeds = parse_seed_override(args.seeds, list(config["baseline"]["seeds"]))
    seed_rows: list[dict[str, Any]] = []
    daily_metric_parts: list[pd.DataFrame] = []
    portfolio_parts: list[pd.DataFrame] = []
    importance_parts: list[pd.DataFrame] = []
    prediction_paths: list[str] = []
    lgb_params = dict(config["baseline"]["lightgbm"])
    early_stopping_rounds = int(config["baseline"]["early_stopping_rounds"])
    minimum_cross_section = int(
        config["baseline"]["minimum_daily_cross_section"]
    )

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

        split_predictions: list[pd.DataFrame] = []
        seed_summary: dict[str, Any] = {
            "seed": seed,
            "best_iteration": int(model.best_iteration_ or model.n_estimators),
        }
        for split_name in ["validation", "historical_test"]:
            prediction = model.predict(
                transformed[split_name],
                num_iteration=model.best_iteration_,
            )
            scored = split_frames[split_name][
                ["paper_proxy", "executable_bridge"]
            ].copy()
            scored["prediction"] = prediction
            scored["split"] = split_name
            scored["seed"] = seed
            split_predictions.append(scored)

            for label_name in label_names:
                daily = daily_correlations(
                    scored,
                    prediction_column="prediction",
                    label_column=label_name,
                    minimum_cross_section=minimum_cross_section,
                )
                summary = correlation_summary(daily)
                prefix = f"{split_name}_{label_name}"
                seed_summary.update(
                    {f"{prefix}_{key}": value for key, value in summary.items()}
                )
                daily = daily.reset_index()
                daily["split"] = split_name
                daily["label_lane"] = label_name
                daily["seed"] = seed
                daily_metric_parts.append(daily)

            if split_name == "historical_test":
                for label_name in label_names:
                    portfolio = topk_dropout_returns(
                        scored,
                        prediction_column="prediction",
                        label_column=label_name,
                        topk=int(config["portfolio"]["topk"]),
                        n_drop=int(config["portfolio"]["n_drop"]),
                        buy_cost=float(config["portfolio"]["buy_cost"]),
                        sell_cost=float(config["portfolio"]["sell_cost"]),
                    )
                    portfolio_metrics = portfolio_summary(
                        portfolio, int(config["portfolio"]["annualization"])
                    )
                    seed_summary.update(
                        {
                            f"historical_test_{label_name}_{key}": value
                            for key, value in portfolio_metrics.items()
                        }
                    )
                    portfolio = portfolio.reset_index()
                    portfolio["label_lane"] = label_name
                    portfolio["seed"] = seed
                    portfolio_parts.append(portfolio)

        predictions = pd.concat(split_predictions).sort_index()
        prediction_path = (
            local_cache / f"alpha20_lgbm_seed_{seed}_predictions.parquet"
        )
        predictions.to_parquet(prediction_path)
        prediction_paths.append(str(prediction_path.relative_to(topic_root)))
        seed_rows.append(seed_summary)
        importance_parts.append(
            pd.DataFrame(
                {
                    "feature": alpha_names,
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

    seed_metrics = pd.DataFrame(seed_rows).sort_values("seed")
    selection_column = "validation_paper_proxy_ic"
    selected_row = seed_metrics.sort_values(
        [selection_column, "seed"], ascending=[False, True]
    ).iloc[0]
    selected_seed = int(selected_row["seed"])
    seed_metrics["selected_by_validation_ic"] = (
        seed_metrics["seed"] == selected_seed
    )
    seed_metrics.to_csv(output_dir / "seed_metrics.csv", index=False)
    pd.concat(daily_metric_parts, ignore_index=True).to_csv(
        output_dir / "daily_predictive_metrics.csv", index=False
    )
    pd.concat(portfolio_parts, ignore_index=True).to_csv(
        output_dir / "portfolio_daily.csv", index=False
    )
    pd.concat(importance_parts, ignore_index=True).to_csv(
        output_dir / "feature_importance.csv", index=False
    )
    pd.DataFrame(
        {
            "feature": alpha_names,
            "train_median": median.reindex(alpha_names).values,
            "train_scale": scale.reindex(alpha_names).values,
        }
    ).to_csv(output_dir / "train_only_normalization.csv", index=False)

    split_inventory = []
    for split_name, part in split_frames.items():
        dates = part.index.get_level_values("datetime")
        split_inventory.append(
            {
                "split": split_name,
                "rows": len(part),
                "dates": dates.nunique(),
                "instruments": part.index.get_level_values(
                    "instrument"
                ).nunique(),
                "date_start": dates.min().date().isoformat(),
                "date_end": dates.max().date().isoformat(),
                "paper_proxy_finite_ratio": float(
                    np.isfinite(part["paper_proxy"]).mean()
                ),
                "executable_bridge_finite_ratio": float(
                    np.isfinite(part["executable_bridge"]).mean()
                ),
            }
        )
    pd.DataFrame(split_inventory).to_csv(
        output_dir / "split_inventory.csv", index=False
    )

    median_metrics = (
        seed_metrics.select_dtypes(include=[np.number]).median().to_dict()
    )
    stability_summary = {
        "historical_test_paper_proxy_ic_positive_seeds": int(
            (seed_metrics["historical_test_paper_proxy_ic"] > 0).sum()
        ),
        "historical_test_paper_proxy_ic_min": float(
            seed_metrics["historical_test_paper_proxy_ic"].min()
        ),
        "historical_test_paper_proxy_ic_max": float(
            seed_metrics["historical_test_paper_proxy_ic"].max()
        ),
        "historical_test_paper_proxy_active_ir_negative_seeds": int(
            (
                seed_metrics[
                    "historical_test_paper_proxy_active_ir_vs_universe_equal_weight"
                ]
                < 0
            ).sum()
        ),
        "historical_test_executable_bridge_active_ir_negative_seeds": int(
            (
                seed_metrics[
                    "historical_test_executable_bridge_active_ir_vs_universe_equal_weight"
                ]
                < 0
            ).sum()
        ),
    }
    manifest = {
        "episode_id": config["episode_id"],
        "stage": "23B_alpha20_lgbm_pit_baseline",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": config_sha,
        "provider_uri": str(provider_path),
        "market": config["data"]["market"],
        "features": alpha_names,
        "feature_count": len(alpha_names),
        "seeds": seeds,
        "formal_five_seed_run": seeds == list(config["baseline"]["seeds"]),
        "selected_seed": selected_seed,
        "selection_rule": "maximum validation PAPER_PROXY daily Pearson IC; lower seed tie-break",
        "median_seed_metrics": median_metrics,
        "stability_summary": stability_summary,
        "prediction_paths_local_cache": prediction_paths,
        "evidence_class": config["split"]["evidence_class"],
        "elapsed_seconds": time.monotonic() - started,
        "claim_ceiling": (
            "deterministic_baseline_complete"
            if seeds == list(config["baseline"]["seeds"])
            else "deterministic_baseline_smoke_only"
        ),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def metric(name: str) -> str:
        value = float(selected_row[name])
        return f"{value:.6f}"

    report = f"""# EP23 23B Alpha20 / LightGBM PIT Baseline

## 裁决

```text
run_kind = {"formal_5_seed" if manifest["formal_five_seed_run"] else "smoke"}
selected_seed = {selected_seed}
selection = validation PAPER_PROXY Pearson IC only
evidence = {config["split"]["evidence_class"]}
claim_ceiling = {manifest["claim_ceiling"]}
```

本阶段建立了 RD-Agent factor/model/joint loop 的共同 deterministic comparator。
它不是 R&D-Agent(Q) 主实验结果，也不是 true OOS 证据。

## Selected-seed predictive readout

| split / lane | IC | ICIR | RankIC | RankICIR |
|---|---:|---:|---:|---:|
| validation / PAPER_PROXY | {metric("validation_paper_proxy_ic")} | {metric("validation_paper_proxy_icir")} | {metric("validation_paper_proxy_rank_ic")} | {metric("validation_paper_proxy_rank_icir")} |
| validation / EXECUTABLE_BRIDGE | {metric("validation_executable_bridge_ic")} | {metric("validation_executable_bridge_icir")} | {metric("validation_executable_bridge_rank_ic")} | {metric("validation_executable_bridge_rank_icir")} |
| historical test / PAPER_PROXY | {metric("historical_test_paper_proxy_ic")} | {metric("historical_test_paper_proxy_icir")} | {metric("historical_test_paper_proxy_rank_ic")} | {metric("historical_test_paper_proxy_rank_icir")} |
| historical test / EXECUTABLE_BRIDGE | {metric("historical_test_executable_bridge_ic")} | {metric("historical_test_executable_bridge_icir")} | {metric("historical_test_executable_bridge_rank_ic")} | {metric("historical_test_executable_bridge_rank_icir")} |

## Selected-seed Top50/drop5 proxy

| lane | gross ARR | net ARR | universe EW ARR | net ARR - universe | active IR | MDD | turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| PAPER_PROXY | {metric("historical_test_paper_proxy_gross_arr")} | {metric("historical_test_paper_proxy_net_arr")} | {metric("historical_test_paper_proxy_universe_equal_weight_arr")} | {metric("historical_test_paper_proxy_net_arr_minus_universe_arr")} | {metric("historical_test_paper_proxy_active_ir_vs_universe_equal_weight")} | {metric("historical_test_paper_proxy_mdd")} | {metric("historical_test_paper_proxy_mean_one_way_turnover")} |
| EXECUTABLE_BRIDGE | {metric("historical_test_executable_bridge_gross_arr")} | {metric("historical_test_executable_bridge_net_arr")} | {metric("historical_test_executable_bridge_universe_equal_weight_arr")} | {metric("historical_test_executable_bridge_net_arr_minus_universe_arr")} | {metric("historical_test_executable_bridge_active_ir_vs_universe_equal_weight")} | {metric("historical_test_executable_bridge_mdd")} | {metric("historical_test_executable_bridge_mean_one_way_turnover")} |

这里的 portfolio 是可复现的 equal-weight Top50/drop5 代理，不含 EP19 的停牌、
blocked fill、现金和逐笔最小费用状态机；完整可执行裁决留给 23F。

## Findings

- 5 个 seed 的 historical-test PAPER_PROXY IC 全部为正，但范围仅为
  `{stability_summary["historical_test_paper_proxy_ic_min"]:.6f}` 至
  `{stability_summary["historical_test_paper_proxy_ic_max"]:.6f}`，属于弱排序信息。
- selected seed 的 PAPER_PROXY 净 ARR 为
  `{metric("historical_test_paper_proxy_net_arr")}`，同期动态 universe 等权 ARR 为
  `{metric("historical_test_paper_proxy_universe_equal_weight_arr")}`；active IR 为
  `{metric("historical_test_paper_proxy_active_ir_vs_universe_equal_weight")}`。
- next-open bridge 没有发生 IC 符号翻转，但 selected seed 的净 ARR 仍低于动态
  universe 等权，active IR 为
  `{metric("historical_test_executable_bridge_active_ir_vs_universe_equal_weight")}`。
- 两条 lane 的 5 个 seed active IR 全部为负。因此当前正的绝对 ARR 主要不能解释为
  Alpha20 排序已经战胜本地大盘股 beta；它只是 agent loop 必须超过的弱基线。
- frozen 官方 LightGBM 强正则参数下 best iteration 仅为
  `{int(selected_row["best_iteration"])}`，后续 agent comparison 必须保留这一事实，
  并另列参数预算匹配 sensitivity，不能把一个欠拟合 comparator 当作成功证据。

## 解释边界

- `PAPER_PROXY` 与官方标签一致，但不是论文文字所说的 t+1 open execution。
- `EXECUTABLE_BRIDGE` 使用 next-open-to-next-open return，用来检测时点桥接是否翻转。
- historical test 已被本项目多次观察，只能用于本地诊断。
- agent-generated candidate 必须在完全相同的 split、label 和成本代理上比较。
- 5-seed 中位数摘要已写入 manifest 生成上下文；逐 seed 数值见 `seed_metrics.csv`。

运行耗时：`{manifest["elapsed_seconds"]:.2f}` 秒。
"""
    (output_dir / "23B_alpha20_lgbm_pit_baseline_report.md").write_text(
        report, encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(
        json.dumps(
            {
                "selected_seed": selected_seed,
                "median_numeric_metrics": median_metrics,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
