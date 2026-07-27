# Requirement 23H：静态多因子库 Matched Benchmark

> 状态：`implementation_authorized`
>
> 上游：23G `ready_for_primary_static_benchmark`

## 1. Estimand

在相同 PIT universe、split、双标签、train-only normalization、LightGBM、
五个 seed 和 Top50/drop5 成本代理下，仅改变 factor library：

```text
A20_RDAGENT_PINNED
A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION
A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION
```

完整 Alpha158/Alpha360、Alpha101 和 AutoAlpha 维持 23G 的 blocked 状态。

## 2. 公平性

- 五个 library/seed 配对完全一致；
- frozen LightGBM 参数完全一致；
- preprocessing 只在 train fit；
- 每个 library 以相同 validation lane early stop；
- historical test 不参与模型、seed 或 library 选择；
- headline 使用五 seed 中位数，不使用挑选 seed；
- selected seed 只为后续可执行桥生成预测，规则为 validation IC 最大。

## 3. 必须输出

```text
outputs/23H_static_factor_library_benchmark/
    config.resolved.yaml
    library_materialization_inventory.csv
    library_quality_metrics.csv
    seed_metrics.csv
    matched_seed_deltas_vs_a20.csv
    library_summary.csv
    annual_predictive_metrics.csv
    daily_predictive_metrics.csv
    portfolio_daily.csv
    feature_importance.csv
    train_only_normalization.csv
    manifest.json
    verdict.json
    23H_static_factor_library_benchmark_report.md
```

预测文件只写入 `outputs/local_cache/phase2/`。

## 4. Gate

```text
23G authorization == true
all three registered libraries materialized
all three libraries have five completed seeds
no all-empty retained feature
train-only normalization complete
Alpha20 reconciliation with 23B within rtol=1e-6, atol=5e-7
headline library selection uses validation median IC only
```

本阶段无论其他库是否超过 Alpha20都可以“实验完成”；弱结果必须保留。
