# 需求骨架：10B Fast-Fail Structural Gate

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. manifest 必须记录 resolved absolute path 与 hash。

## 1. 目标

10B 是 Layer 1 fast-fail structural safety gate。它回答一个窄问题：

```text
在 10A 冻结后的 post-dedup population 上，
fast-fail-only score 是否相对规则化 swing-low structural stop
有 capacity-matched incremental capture lift。
```

10B 不是 cost optimizer，不是 medium-capacity rejector，也不能把 false-repair uplift 写成 fast-fail uplift。

## 2. 输入与依赖

10B supported gate 必须读取 10A 输出：

```text
outputs/manifests/10A_density_rule_system_manifest.json
outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_fast_fail_power_audit.csv
outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet
```

10B 可以读取 09C fast-fail-only score 作为 pre-dedup diagnostic replay 参照，但不能复用 pre-dedup score 或 threshold claim supported：

```text
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
```

supported gate 下，10B 必须在 post-dedup population 上重新训练、重新校准或至少重新冻结 threshold policy。

## 3. 非目标

10B 明确不做：

1. 不训练 hybrid cost target。
2. 不混入 false-repair component。
3. 不做 medium-capacity cost rejector。
4. 不在 validation / robustness 上选择 threshold。
5. 不把 no-overlap ablation collapse 当作 kill 判据。
6. 不声称 production-ready 或 entry-candidate。

## 4. Scope 纪律

supported training / threshold / gate scope：

```text
denominator_id = post_dedup_risk_on_r_core
```

R6 只能 readout：

```text
no fit
no feature selection
no threshold selection
no supported gate
```

任何 pre-dedup replay 只能输出 diagnostic。

## 5. Threshold Grid

fast-fail-only threshold grid：

```text
keep_9000
keep_9250
keep_9300
keep_9400
keep_9500
keep_9600
keep_9700
```

`keep_9000` 只作为 lower-bound sensitivity。selected operating point 应落在：

```text
keep_9250 到 keep_9700
```

并由 winner-retention floor 与 power gate 约束，不得因为 grid 包含 `keep_9000` 就允许 10% reject capacity。

## 6. Power Gate

10B 必须先消费 10A 的 `post_dedup_fast_fail_power_audit.csv`。

如果出现以下情况，10B 只能输出 rule-based structural stop diagnostic：

```text
post_dedup_fast_fail_positive_n < predeclared_min_positive_count
post_dedup_fast_fail_winner_n < predeclared_min_winner_count
rule_baseline_rejected_fast_fail_positive_n < predeclared_min_rule_positive_count
rule_baseline_rejected_fast_fail_winner_n < predeclared_min_rule_winner_count
```

低功效 split 的 low wrong-kill 读数不得写成稳定支持证据。

## 7. Binding Metrics

决定 pass / fail 的 binding objectives：

```text
capacity_matched_capture_lift_over_rule_baseline > predeclared_margin
capacity_matched_capture_lift_over_random > predeclared_margin
accepted_MAE_10_improves
```

必要 side constraints：

```text
winner_retention >= predeclared_floor
wrong_kill_rate <= predeclared_cap
density_after_Layer_0 == 10A frozen density
OOS readout no severe reversal
```

winner retention 是 floor，不是主优化目标。

## 8. Ablation 与解释

10B 必须报告：

```text
full model
rule baseline
random baseline
drop FS2 / FS3 mechanism-overlap subset
```

no-overlap ablation 只作解释，不作 kill。如果 full 有效但去掉 related-overlap 后完全坍塌，结论应降级为：

```text
rule-based structural stop diagnostic
```

不得 claim 泛化 fast-fail alpha。

## 9. 必须输出

10B 必须输出：

```text
outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_power_gate_readout.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_threshold_frontier.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/capacity_matched_rule_lift.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/winner_injury_audit.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_ablation_readout.csv
outputs/local_cache/10B_fast_fail_structural_gate/post_dedup_fast_fail_scores.parquet
outputs/manifests/10B_fast_fail_structural_gate_manifest.json
outputs/publishable/reports/10B_fast_fail_structural_gate_report.md
```

## 10. 决策状态

10B 决策必须使用以下之一：

```text
10B_fast_fail_structural_gate_supported
10B_fast_fail_structural_gate_source_caveated_supported
10B_fast_fail_rule_based_structural_stop_diagnostic
10B_fast_fail_pre_dedup_diagnostic_only
10B_fast_fail_input_blocked
```

只要 source caveat 未修复，正向结论只能使用 `source_caveated` variant。
