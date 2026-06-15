# 需求骨架：10C False-Repair Rejector

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. manifest 必须记录 resolved absolute path 与 hash。

## 1. 目标

10C 是 Layer 2 false-repair / exposure-efficiency rejector。它回答：

```text
在 10A 冻结后的 post-dedup population 上，
false_repair_20d_component 是否能作为中容量 exposure-efficiency filter。
```

10C 不是 fast-fail safety gate，也不能把 false-repair signal 写成 fast-fail uplift。

## 2. 输入与依赖

10C supported gate 必须读取 10A 输出：

```text
outputs/manifests/10A_density_rule_system_manifest.json
outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_false_repair_power_audit.csv
outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet
```

10C 必须读取 09B / 09C 的可审计 feature 与 diagnostic 产物：

```text
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09B_feature_foundation_ablation_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
```

09C pre-dedup false-repair readout 只能作为 diagnostic prior。supported gate 必须在 post-dedup population 上重新训练、重新校准或重新冻结 threshold policy。

## 3. 非目标

10C 明确不做：

1. 不做 fast-fail structural safety gate。
2. 不训练 hybrid cost target。
3. 不调 density / cooldown 规则。
4. 不在 validation / robustness 上选择 threshold。
5. 不把 E1 baseline 当作主 uplift comparator。
6. 不声称 production-ready 或 entry-candidate。

## 4. Scope 纪律

supported training / threshold / gate scope：

```text
population_id = 10A__same_instrument_cooldown_10d
denominator_id = post_dedup_risk_on_r_core
readout_only_flag = false
target_component = false_repair_20d_component
```

`population_id` 必须在 run config 中预声明，并且默认只能使用上面这个 10A frozen population。若要改用其他 10A arm，必须先修改本 requirement / config；不得根据 validation / robustness readout 回选。

R6 只能 readout：

```text
no fit
no feature selection
no threshold selection
no supported gate
```

E1 baseline 只能作为外部 repair baseline、E1-missed retention 或 fallback 参照，不作为 rejector uplift 的主比较对象。

## 5. Frozen Source Handling

R2 source 处理必须作为 10C frozen input 定死，不得留作 10C 内部可调项。

10C 默认 frozen policy 固定为：

```text
r2_source_policy = separate_family_budget_cooldown
```

该策略表示 10C 不在本阶段补齐 amount / volume 字段，不重建 09B feature matrix，也不根据 10C 模型读数回改 10A population。R2 相关事件只允许继承 10A frozen population 中已经 materialized 的 family / cooldown 处理；`r2_source_policy`、10A population hash、09B feature matrix hash 必须写入 10C manifest。

`backfill_amount_volume` 明确不是本 requirement 的支持路径。若未来要改用该路径，必须先更新本 requirement 与上游 frozen artifacts，再重新运行；不得在 10C 内部作为可调项切换。

如果 R2 处理会同时改变 feature set 与样本总体，10C 必须 input-blocked 或降级 diagnostic。

## 6. Threshold Grid

false-repair threshold grid：

```text
keep_8000
keep_8250
keep_8500
keep_8750
keep_9000
```

selected operating point 必须由 train-only threshold policy 冻结。validation / robustness 只能 readout。

10C 必须先消费 10A 的 `post_dedup_false_repair_power_audit.csv`。如果出现以下情况，10C 只能输出 diagnostic：

```text
false_repair_ml_supported_gate_allowed != true
post_dedup_false_repair_positive_n < 300
post_dedup_winner_n < 100
winner_retention_power_status != pass
e1_missed_proxy_status = episode_membership_proxy_input_blocked
```

这里的 `e1_missed_proxy_status` 指 10A `post_dedup_false_repair_power_audit.csv` 中的 aggregate rollup status。`mixed_non_blocking`、`all_episode_level_proxy_from_08_membership`、`all_no_episode_membership_for_event` 都不因 E1 proxy 本身阻塞 10C；只有 `episode_membership_proxy_input_blocked` 会强制 10C diagnostic-only。

## 7. Binding Metrics

10C 必须报告：

```text
false-repair reduction
winner retention
exposure-days reduction
E1-missed retention
bridge retention
MFE / confirm_20 relation
OOS rejected-fraction spread
train-only threshold instability proxy
```

`train-only threshold instability proxy` 定义为：

```text
purged-CV 下 selected threshold / reject-fraction 的方差
```

该 proxy 只能来自 train-only purged folds，不得读取 validation / robustness。

winner retention floor 可以低于 10B fast-fail layer，但必须满足：

```text
winner_retention >= 0.8500
```

如果 winner retention 接近 09C 的 67% 到 70%，或低于 0.8500，只能输出有 cost signal 但不可用的 rejector diagnostic。

`OOS rejected-fraction spread` cap 冻结为：

```text
max(validation_rejected_fraction, robustness_rejected_fraction)
    - min(validation_rejected_fraction, robustness_rejected_fraction)
    <= 0.1500
```

## 8. Cascade Readout

10C 必须预留 cascade-level 联合 readout。若 10B 有 frozen gate，10C 必须输出 overlap-deduplicated cost attribution：

```text
fast_fail_only_rejected
false_repair_only_rejected
both_rejected
accepted_by_cascade
```

primary comparison：

```text
cascade vs same R-core pre-cascade population
winner recall net change
false-positive exposure-days net change
density after Layer 0 = 10A frozen value
```

最终判据是同一 R-core population 上 cascade 前后的净改善，不是 10B / 10C 分数相加。

## 9. 必须输出

10C 必须输出：

```text
outputs/publishable/tables/10C_false_repair_rejector/false_repair_power_gate_readout.csv
outputs/publishable/tables/10C_false_repair_rejector/false_repair_threshold_frontier.csv
outputs/publishable/tables/10C_false_repair_rejector/exposure_efficiency_readout.csv
outputs/publishable/tables/10C_false_repair_rejector/winner_retention_audit.csv
outputs/publishable/tables/10C_false_repair_rejector/train_only_threshold_instability.csv
outputs/publishable/tables/10C_false_repair_rejector/cascade_overlap_attribution.csv
outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet
outputs/manifests/10C_false_repair_rejector_manifest.json
outputs/publishable/reports/10C_false_repair_rejector_report.md
```

## 10. 决策状态

10C 决策必须使用以下之一：

```text
10C_false_repair_rejector_supported
10C_false_repair_rejector_source_caveated_supported
10C_false_repair_feature_source_supported
10C_false_repair_diagnostic_only
10C_false_repair_input_blocked
```

只要 source caveat 未修复，正向结论只能使用 `source_caveated` variant。
