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
decision = 09B_feature_foundation_blocked
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

## 7. Stationary Hygiene

必须做：

1. rolling z-score。
2. rolling percentile。
3. ATR normalization。
4. sigma normalization。
5. selected fracdiff only。

Fracdiff 只允许用于 selected memory-bearing continuous series，例如：

```text
log(close / industry_index)
log(close / market_index)
log(industry / market)
log(amount)
VWAP-related series
```

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

权重计算必须使用 `t0` / `t1`、event active interval、concurrency、average uniqueness。至少输出：

1. `sample_id`
2. `canonical_event_id`
3. `instrument`
4. `event_t0_date`
5. `label_t1_date`
6. `active_interval_start`
7. `active_interval_end`
8. `average_uniqueness`
9. `time_decay_weight`
10. `final_sample_weight`

09B 的 feature importance 和 09C 的模型训练必须引用同一份权重文件。禁止各自重算。

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

只有 `allowed_for_09C_flag = true` 的 feature 可以进入 09C model matrix。

## 13. 输出

09B 必须输出：

```text
outputs/manifests/09B_feature_foundation_ablation_manifest.json
outputs/publishable/reports/09B_feature_foundation_ablation_report.md
outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
outputs/publishable/tables/09B_feature_foundation/feature_stationarity_audit.csv
outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv
outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
outputs/publishable/tables/09B_feature_foundation/feature_family_ablation.csv
outputs/publishable/tables/09B_feature_foundation/group_mda_importance.csv
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
selected_target_label
selected_target_contract_hash
selected_label_event_bindings_hash
selected_feature_contract_hash
sample_uniqueness_weights_hash
feature_leakage_status
forbidden_feature_count
stationarity_audit_status
mechanism_overlap_status
```

## 14. 09B 决策

允许的 09B 决策：

```text
09B_feature_foundation_complete
09B_feature_foundation_diagnostic_only
09B_feature_foundation_blocked
```

只有 `09B_feature_foundation_complete` 允许 09C 输出 research-entry supported。其他状态下 09C 只能 diagnostic。
