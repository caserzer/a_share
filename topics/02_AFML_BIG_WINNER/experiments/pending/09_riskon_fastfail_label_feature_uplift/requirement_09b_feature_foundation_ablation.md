# 需求：09B Feature Foundation / Stationary / Importance

## 1. 目标

09B 构建 t0 可见、稳定、可审计的 feature set v1。它不是最终模型实验，不能因为某个 feature family 在 validation 好看就直接升级为 entry signal。

09B 必须回答：

1. 哪些 feature family 可在 t0 PIT 构造。
2. 哪些 feature 需要 rolling z / percentile / ATR / sigma normalization。
3. 哪些 memory-bearing continuous series 适合 selected fracdiff。
4. 哪些 feature family 对 selected label 有稳定 OOS importance。
5. 哪些 feature 与 label mechanism 重叠，需要单独解释。
6. 样本 uniqueness / concurrency 权重如何冻结并供 09C 复用。
7. 哪一份冻结 feature matrix、transform contract 与 sample key 可以被 09C 原样消费。

只有 09B 输出 `09B_feature_foundation_complete`，09C 才允许输出 research-entry supported。

## 2. 输入与依赖

09B 必须读取 09A 输出：

```text
outputs/manifests/09A_fast_fail_label_frontier_manifest.json
outputs/publishable/reports/09A_fast_fail_label_frontier/fast_fail_label_contract.md
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_contract.csv
outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_event_binding_summary.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/cost_target_bridge.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/label_mechanism_contract.csv
```

如果 09A 没有输出 `09A_label_frontier_candidate_selected` 或 `09A_label_frontier_candidate_source_caveated_selected`，09B 仍可运行 feature foundation，但必须标记：

```text
selected_label_status = diagnostic_only_no_candidate
```

此时 09B 不得声称为 09C supported gate 提供完整 target contract。

09B 必须从 `selected_label_event_bindings.parquet` 读取 selected label、`label_t1_date`、censoring status 与 denominator view。禁止从 `fast_fail_label_frontier.csv`、`cost_target_bridge.csv` 或其他 aggregate 表反推事件级 label。

09B 的事件级主键冻结为：

```text
sample_key = (sample_id, selected_target_id, denominator_id)
```

`sample_id` 单列不得假设唯一。所有 09B feature matrix、sample weights、importance readout 与 09C downstream join 都必须使用 `sample_key`。

09B 必须审计 `selected_label_contract.csv` 与 `selected_label_event_bindings.parquet` 的 target 覆盖：

1. `selection_status = selected` 且 `usable_for_09C_supported_gate = true` 的 target 必须有事件级 binding。
2. 如果任一 selected target 缺少 binding，必须输出 `selected_target_binding_coverage_status = partial`，该 target 不得进入 09C supported gate。
3. 若 09B 只覆盖 primary binding target，必须在 report 和 manifest 中写明 `supported_selected_target_ids` 与 `missing_selected_target_ids`。
4. 只有所有 selected target 都有完整 binding，09B 才能输出 `09B_feature_foundation_complete`。
5. 如果 `usable_for_09C_supported_gate = true` 的 target 缺少 binding，这不是 feature diagnostic 问题，而是上游 09A target contract 冲突；09B 必须 fail closed：

```text
decision = 09B_feature_foundation_upstream_contract_conflict
```

要解除该冲突，上游 09A 必须二选一：

1. 将缺 binding 的 target 改为 `usable_for_09C_supported_gate = false`，保留为 sensitivity / 对照 target。
2. 为该 target 补发完整事件级 binding，使其可被 09B/09C 通过 `sample_key` 消费。

必须输出 target 覆盖审计：

```text
outputs/publishable/tables/09B_feature_foundation/selected_target_binding_coverage_audit.csv
```

必须读取并记录 hash：

```text
topics/02_AFML_BIG_WINNER/README.md
topics/02_AFML_BIG_WINNER/research_direction_discussion_20260614.md
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/08_all_experiments_final_report.md
```

必须读取的 08 feature / event / membership 源：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_capture.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/cross_section_feature_panel.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
```

`cross_section_feature_panel.parquet` 必须存在；若缺失，09B 必须 fail closed：

```text
decision = 09B_feature_foundation_input_blocked
```

## 3. 非目标

09B 明确不做：

1. 不训练最终 risk_on cost rejector。
2. 不选择 09C threshold。
3. 不输出 research-entry supported。
4. 不做 full-sample feature selection、full-sample PCA、full-sample scaling。
5. 不发明新 event family 或新 source。
6. 不做 transition model 或 transition feature uplift。

## 4. PIT 与 Forbidden Feature 规则

所有 feature as-of join 必须满足：

```text
feature_as_of_date <= event_t0_date
```

09B 禁止构造或选择：

1. `failure_10_label`
2. `event_false_repair_20d_label`
3. `winner_120`
4. post-replay membership flag
5. future MFE / MAE
6. future high / low
7. transition outcome / conversion label
8. `next_regime`
9. post-event volume or return
10. any label-derived variable

09A binding 中以下字段只能作为 label / meta / audit / weight 输入，不得进入 feature matrix 或 feature selection：

```text
selected_fast_fail_10_label
selected_cost_bad_10_20_target
frozen_false_repair_20d_label
selected_fast_fail_touch_date
selected_fast_fail_touch_pos
selected_fast_fail_touch_offset_sessions
selected_fast_fail_barrier_id
event_big_winner_120d_label
event_super_winner_120d_label
event_near_winner_120d_label
winner_censoring_status
label_t1_date
censoring_status
horizon_complete_10d
horizon_complete_20d
horizon_complete_120d
candidate_outcome_120d_status
```

`selected_fast_fail_touch_offset_sessions` 只能用于 label audit / horizon sanity check，不得作为 t0 feature。`label_t1_date` 只能用于 uniqueness / embargo / sample weight，不得作为 predictive feature。

如果任何 forbidden field 进入 feature matrix，必须输出：

```text
decision = 09B_feature_foundation_blocked
```

## 5. Source Pool 与 Regime Scope

09B 的 feature foundation scope 必须来自可重建 source pool：

```text
event_regime_bucket = risk_on
source_pool in {08_R_core_event_regime_gated, 08_R6_event_regime_gated}
```

主训练分母冻结为：

```text
denominator_id = risk_on_r_core_horizon_complete
```

`risk_on_r6_horizon_complete` 只能作为 R6 slice / readout，不能与 R-core 并列堆叠成训练分母。若同时输出 R-core 与 R6 feature matrix，必须以 `denominator_id` 区分，禁止重复计数同一 `sample_id`。

R6 readout 规则：

1. `risk_on_r_core_horizon_complete` 是唯一 `supported_training_scope_flag = true` 的 denominator。
2. `risk_on_r6_horizon_complete` 若产出 feature matrix / weights / importance，只能标记 `supported_training_scope_flag = false` 与 `scope_usage = readout_only`。
3. R6 rows 不得参与 feature selection、diagnostic model fit、scaler fit、PCA fit、threshold selection 或 09C supported gate。
4. 如果实现选择不为 R6 产出权重 / importance，必须在 manifest 中标记 `r6_readout_materialization_status = not_materialized`，并在 report 中说明 R6 只保留为 09A label readout。

必须复用 09A / 09 总览中定义的 source pool reconstruction audit：

```text
outputs/publishable/tables/input_audit/source_pool_reconstruction_audit.csv
```

如果 `08_R_core_event_regime_gated` 或 `08_R6_event_regime_gated` 不能重建，09B 只能 diagnostic 或 blocked，不得向 09C 提供 supported feature contract。

## 6. Feature Family

至少包含：

```text
FS0_baseline_h_features:
    H 中已经允许的 t0 feature

FS1_event_intrinsic:
    family_id, channel_count, family_count, event score, source scope, same-day overlap

FS2_basis_path_quality:
    stock_vs_market / stock_vs_board / stock_vs_industry basis,
    close_to_high, distance-to-event-low, path slope, relative CUSUM

FS3_vol_range_stop_distance:
    ATR, realized volatility, range width, drawdown depth,
    ATR-normalized stop distance, sigma-normalized stop distance

FS4_amount_volume_vwap_dib:
    amount ratio, turnover ratio, VWAP deviation, DIB / signed amount proxy,
    volume expansion quality

FS5_market_industry_riskon_quality:
    market trend, breadth, universe_up_share, board relative strength,
    industry / board context when PIT-available

FS6_recurrence_local_density:
    prior event count up to t0, rolling 10d / 20d local density before t0,
    same instrument recurrence, family recurrence, de-overlap context
```

任何 industry feature 必须先证明 PIT membership；否则降级为 blocked 或 board-level fallback，不得静默冒充 industry。

PIT membership 审计必须读取并输出：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/industry_style_input_contract_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_run_capability_summary.csv
outputs/publishable/tables/09B_feature_foundation/industry_board_pit_membership_audit.csv
```

如果上述两个 08 PIT / capability audit artifact 任一缺失，09B 必须输出：

```text
decision = 09B_feature_foundation_input_blocked
```

默认规则：

1. 08 已声明 `industry` PIT artifact 不可用时，09B 不得构造 stock-vs-industry、industry-vs-market、industry breadth 或 industry rank feature。
2. `style_proxy_board` / board bucket 只能作为 board-level fallback 或 context feature，不能命名或解释为 industry alpha。
3. 若未来提供新的 PIT industry membership artifact，必须满足 `membership_as_of_date <= event_t0_date`、coverage >= 95%、split 内 consistency >= 95%，否则该 feature family 只能 diagnostic 或 blocked。
4. 对任何 board/style fallback，`feature_contract.csv` 必须写明 `industry_pit_status = board_fallback_not_industry`。

## 7. Stationary Hygiene

必须做：

1. rolling z-score。
2. rolling percentile。
3. ATR normalization。
4. sigma normalization。
5. selected fracdiff only。

rolling z-score、rolling percentile、ATR normalization、sigma normalization 的 estimator 只能使用 `feature_as_of_date <= event_t0_date` 的 trailing window。任何 scaler、imputer、winsorizer、PCA、feature selector 都必须在 train fold 内 fit，再 transform validation / robustness；不得用全样本统计量。

Fracdiff 只允许用于 selected memory-bearing continuous series，例如：

```text
log(close / industry_index)
log(close / market_index)
log(industry / market)
log(amount)
VWAP-related series
```

含 `industry` 的 fracdiff 候选只有在 §6 的 PIT industry membership audit 通过后才允许；在当前 08 artifact 声明 industry PIT unavailable 的情况下，必须降级为 blocked 或改用 market / board fallback series，且不得命名为 industry feature。

不得对以下字段做 fracdiff：

```text
returns
ranks
event dummies
labels
future-derived fields
```

必须输出：

```text
outputs/publishable/tables/09B_feature_foundation/feature_stationarity_audit.csv
```

## 8. Sample Uniqueness / Sample Weights

09B 必须输出冻结权重：

```text
outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv
```

权重计算必须使用 `t0` / `t1`、event active interval、concurrency、average uniqueness。由于 09C 必须同时评估 fast-fail-only target 与 hybrid cost target，09B 必须冻结多 horizon 权重：

```text
weight_horizon_id in {
    fast_fail_10d,
    cost_bad_10_20_20d
}
```

`fast_fail_10d` 使用 fast-fail component 的 10D active interval；`cost_bad_10_20_20d` 使用 hybrid target 的 20D `label_t1_date` / active interval。禁止用 20D hybrid 权重覆盖 10D fast-fail-only 评估。

`fast_fail_10d` 的 active interval 不能复用 binding 中 hybrid target 的 `label_t1_date`。它必须由事件级 binding 重建：

```text
active_interval_start = trade_time
if selected_fast_fail_10_label = true:
    active_interval_end = selected_fast_fail_touch_date
else:
    active_interval_end = 10th trading session after trade_time
```

必须用 `selected_fast_fail_touch_offset_sessions` 做 sanity check：触发样本的 offset 必须在 `[0, 9]`；未触发 / 不可评估样本不得用 touch date 推断 t1。若 10D 路径不可评估，`fast_fail_10d` 权重行必须标为 `weight_status = not_evaluable_10d`，不得静默复用 20D t1。

权重必须按 `selected_target_id` 输出。缺 binding 的 target 不产出权重行，必须在 `sample_uniqueness_audit.csv` 中标为 `target_binding_missing`，并触发 `09B_feature_foundation_upstream_contract_conflict`。

`sample_uniqueness_audit.csv` 必须按 `weight_horizon_id` 与 `denominator_id` 分组报告 uniqueness / concurrency 分布，至少包含：

```text
weight_horizon_id
denominator_id
scope_usage
sample_n
average_uniqueness_mean
average_uniqueness_median
average_uniqueness_p10
average_uniqueness_p90
concurrency_count_mean
concurrency_count_p90
```

报告必须明确说明 `fast_fail_10d` 与 `cost_bad_10_20_20d` 的 active interval 不同，因此 average uniqueness 不可横向直接比较为 feature 质量；它只是 09C 选择正确权重 horizon 的审计读数。通常 10D fast-fail-only 权重的 average uniqueness 应高于 20D hybrid 权重，若方向相反必须给出原因。

至少输出：

1. `sample_id`
2. `selected_target_id`
3. `denominator_id`
4. `weight_horizon_id`
5. `scope_usage`
6. `supported_training_scope_flag`
7. `canonical_event_id`
8. `instrument`
9. `event_t0_date`
10. `label_t1_date`
11. `active_interval_start`
12. `active_interval_end`
13. `concurrency_count_mean`
14. `average_uniqueness`
15. `time_decay_weight`
16. `final_sample_weight`
17. `weight_status`

09B 的 feature importance 和 09C 的模型训练 / fast-fail-only readout 必须引用同一份权重文件。禁止各自重算。

## 9. Feature Importance

必须输出：

```text
outputs/publishable/tables/09B_feature_foundation/feature_family_ablation.csv
outputs/publishable/tables/09B_feature_foundation/group_mda_importance.csv
outputs/publishable/reports/09B_feature_foundation/clustered_importance_report.md
```

规则：

1. SFI、MDA、group MDA 是主证据。
2. MDI 只能辅助解释，不得单独驱动 feature selection。
3. Feature selection、scaling、PCA、calibration、threshold tuning 必须在 train fold 内 fit。
4. 不得做 full-sample feature ranking before CV。
5. 所有 importance 必须使用 09B 冻结 sample weights。

09B 的 importance 只能使用诊断模型，不得升级为 09C 最终模型。诊断模型必须在 config 中冻结，默认只允许：

```text
balanced logistic / elastic net
shallow random forest or bagging shallow trees
```

importance 必须按以下 target/component 分开报告：

```text
fast_fail_only_10d
false_repair_20d_component
hybrid_cost_bad_10_20
```

importance 必须按 split 报告：

```text
train
validation
robustness
```

并输出 train vs robustness 的稳定性读数，例如 group rank Spearman、top-k overlap、sign consistency。validation 因 winner/cost bad 单元格 power 可能不足，只能作为 low-power readout，不得驱动 feature selection 或 family graduation。

如果 selected target binding 只覆盖 primary target，必须输出 `target_binding_missing` 并触发 `09B_feature_foundation_upstream_contract_conflict`；不得把缺 binding target 的 importance 当作 09B feature 问题。

R6 importance 只能作为 readout-only slice：

1. 诊断模型、transform 与 feature selection 必须在 R-core training scope 内完成。
2. R6 只能复用 R-core fitted diagnostic model / transform 做 separability 与 group importance readout。
3. R6 importance 不得参与 feature graduation 或 09C supported feature contract。
4. 如果 R6 未产出 importance，`target_component_importance_summary.csv` 必须标记 `r6_importance_status = not_materialized`。

必须新增输出：

```text
outputs/publishable/tables/09B_feature_foundation/diagnostic_model_registry.csv
outputs/publishable/tables/09B_feature_foundation/target_component_importance_summary.csv
outputs/publishable/tables/09B_feature_foundation/importance_split_stability.csv
```

## 10. PCA 纪律

PCA 不作为主力 selector。若使用 PCA，只允许：

1. family 内 PCA。
2. train-fold fit。
3. validation / robustness transform。
4. 与 raw / representative feature 对照。

禁止：

```text
global PCA
full-sample PCA
先 PCA 再解释模型
```

## 11. Feature-label Mechanism Overlap

09B 必须输出：

```text
outputs/publishable/tables/09B_feature_foundation/label_mechanism_overlap_audit.csv
```

至少报告：

| column | meaning |
| --- | --- |
| `feature_id` | feature |
| `feature_family` | feature family |
| `label_id` | selected label |
| `shared_series` | EMA60 / swing low / ATR / sigma / etc. |
| `overlap_type` | direct / related / none |
| `interpretation_caveat` | 解读约束 |

Feature 与 label 同机制不自动 forbidden，但 09C 必须在 ablation 中单独报告去掉 overlap features 后的结果。

## 12. Feature Contract

09B 必须输出：

```text
outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
outputs/publishable/tables/09B_feature_foundation/feature_matrix_schema.csv
outputs/publishable/tables/09B_feature_foundation/feature_transform_contract.json
outputs/publishable/tables/09B_feature_foundation/selected_target_binding_coverage_audit.csv
```

至少包含：

1. `feature_id`
2. `feature_family`
3. `raw_source_artifact`
4. `as_of_rule`
5. `t0_visible_flag`
6. `normalization_method`
7. `stationarity_status`
8. `fracdiff_status`
9. `industry_pit_status`
10. `allowed_for_09C_flag`
11. `forbidden_reason`
12. `label_mechanism_overlap_type`
13. `feature_dtype`
14. `feature_as_of_date_rule`
15. `transform_fit_scope`
16. `missing_value_policy`

只有 `allowed_for_09C_flag = true` 的 feature 可以进入 09C model matrix。

`feature_matrix.parquet` 是 09C 唯一允许消费的 frozen feature matrix。至少包含：

1. `sample_id`
2. `selected_target_id`
3. `denominator_id`
4. `canonical_event_id`
5. `instrument`
6. `event_t0_date`
7. `event_split`
8. `feature_as_of_date`
9. 所有 `allowed_for_09C_flag = true` 的 feature columns

`feature_matrix.parquet` 禁止包含任何 label、future outcome、touch result、horizon completeness、winner label、`label_t1_date` 或 sample weight column。09C 如需 target / weight / censoring，只能通过 `sample_key` 从 09A binding 与 09B weights join。

`feature_transform_contract.json` 必须冻结：

```text
imputer policy
winsorization policy
scaler / normalizer policy
rolling window definitions
fracdiff selected series and d value
PCA usage if any
train-fold fit / OOS transform rule
feature ordering
missing feature behavior
```

## 13. 输出

09B 必须输出：

```text
outputs/manifests/09B_feature_foundation_ablation_manifest.json
outputs/publishable/reports/09B_feature_foundation_ablation_report.md
outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
outputs/publishable/tables/09B_feature_foundation/feature_stationarity_audit.csv
outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv
outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
outputs/publishable/tables/09B_feature_foundation/feature_matrix_schema.csv
outputs/publishable/tables/09B_feature_foundation/feature_transform_contract.json
outputs/publishable/tables/09B_feature_foundation/selected_target_binding_coverage_audit.csv
outputs/publishable/tables/09B_feature_foundation/industry_board_pit_membership_audit.csv
outputs/publishable/tables/09B_feature_foundation/feature_family_ablation.csv
outputs/publishable/tables/09B_feature_foundation/group_mda_importance.csv
outputs/publishable/tables/09B_feature_foundation/diagnostic_model_registry.csv
outputs/publishable/tables/09B_feature_foundation/target_component_importance_summary.csv
outputs/publishable/tables/09B_feature_foundation/importance_split_stability.csv
outputs/publishable/tables/09B_feature_foundation/label_mechanism_overlap_audit.csv
outputs/publishable/reports/09B_feature_foundation/clustered_importance_report.md
```

manifest 至少包含：

```text
experiment_id
run_timestamp
git_commit
decision
source_caveated
input_hashes
output_hashes
config_hash
selected_target_ids
supported_selected_target_ids
missing_selected_target_ids
selected_target_contract_hash
selected_label_event_bindings_hash
selected_feature_contract_hash
feature_matrix_hash
feature_transform_contract_hash
sample_uniqueness_weights_hash
feature_leakage_status
forbidden_feature_count
stationarity_audit_status
mechanism_overlap_status
selected_target_binding_coverage_status
sample_key_uniqueness_status
weight_horizon_ids
r6_readout_materialization_status
upstream_contract_status
industry_pit_status
importance_split_stability_status
```

## 14. 09B 决策

允许的 09B 决策：

```text
09B_feature_foundation_complete
09B_feature_foundation_diagnostic_only
09B_feature_foundation_input_blocked
09B_feature_foundation_upstream_contract_conflict
09B_feature_foundation_blocked
```

只有 `09B_feature_foundation_complete` 允许 09C 输出 research-entry supported。其他状态下 09C 只能 diagnostic。

`09B_feature_foundation_complete` 必须同时满足：

1. 09A decision 为 selected 或 source-caveated selected。
2. 所有 `usable_for_09C_supported_gate = true` 的 selected target 都有事件级 binding。
3. `sample_key = (sample_id, selected_target_id, denominator_id)` 唯一。
4. `feature_matrix.parquet`、`feature_contract.csv`、`feature_transform_contract.json`、`sample_uniqueness_weights.parquet` 都已生成并写入 manifest hash。
5. forbidden feature count = 0。
6. source pool reconstruction audit 没有 unsupported training scope。
7. multi-horizon sample weights 至少覆盖 `fast_fail_10d` 与 `cost_bad_10_20_20d`。

如果 09A input artifact 文件整体缺失、hash mismatch、或 `cross_section_feature_panel.parquet` 缺失，输出：

```text
decision = 09B_feature_foundation_input_blocked
```

如果 09A 的 `selected_label_contract.csv` 声明某个 target `usable_for_09C_supported_gate = true`，但 `selected_label_event_bindings.parquet` 中没有该 `selected_target_id` 的事件级 binding，输出：

```text
decision = 09B_feature_foundation_upstream_contract_conflict
```

该状态必须在 report 中明确写成 09A artifact contract 冲突，不得解释成 09B feature foundation 失败。
