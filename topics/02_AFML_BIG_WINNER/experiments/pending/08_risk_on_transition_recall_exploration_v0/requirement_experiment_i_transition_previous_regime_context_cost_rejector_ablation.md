# 需求：Experiment I - Transition Previous-Regime Context Cost Rejector Ablation

## 1. 背景

Experiment G 证明，`transition` 与其前一个非 transition regime 有明显关系：

1. `transition_from_risk_on` / `transition_from_risk_off` 是 t0 可知的 PIT context。
2. `transition_continuation` / `transition_conversion` 依赖未来 next regime，只能作为 ex-post readout。
3. G 的 supported evidence 不足：robustness conversion segment 只有 3 段，per-direction conversion 在 OOS 只有 1-2 段。
4. 但 G 的 readout 有解释力：同样是 `transition_from_risk_on`，robustness continuation 很干净，而 conversion 很脏；R-core fast-fail 约 10 倍、false-repair 约 5.5 倍。

Experiment H 进一步证明，当前 risk_on cost rejector 有稳定 OOS 排序信号，但 research-entry 未过：

1. H 已补齐 E 的工程/契约缺口。
2. H robustness ROC-AUC = `0.6858`，top-decile lift = `2.0307`。
3. H 失败点不是 label / as-of / denominator / feature coverage，而是 train-only 同阈值 frontier：
   - `keep_0800`：train any recall `90.0452%`，但 train cost reduction `14.1389%`，差 `0.8611pp`。
   - `keep_0775`：train cost reduction `15.3452%`，但 train any recall `89.1403%`，差 `0.8597pp`。

因此，本实验不再继续做 H 的 threshold hardening，也不把 G 的 context 并入 H 的 risk_on-only gate。

Experiment I 的目标是一个更窄的 diagnostic ablation：

```text
在 transition universe 内，只用 t0 可见 previous-regime context，
检验它是否改善 cost_bad sorting / post-filter cost quality。
```

本实验允许训练 supervised `cost_bad_10_20` rejector 的诊断模型；但严禁训练
`transition_conversion` / `transition_continuation` classifier。conversion 只能作为 readout label。

方法学风险：transition events 不是独立样本。当前 primary universe 的 train event_n 可能超过
一万，但这些事件只来自几十个 transition segments，且少数长段会贡献大量事件。同一 segment
内的 events 共享 previous-regime context 与高度相关的 market state。I 的所有模型读数必须同时报告
event-level 与 segment-level power；任何 uplift claim 必须通过 segment-grouped / purged stability
readout，不能只看 event-level ROC-AUC。

## 2. Primary Question

Experiment I 必须回答：

```text
Does PIT previous-regime context improve transition-side cost_bad sorting
relative to the same t0 feature set without previous-regime context?
```

中文等价问题：

```text
在 transition universe 内，加入 t0 可见的 previous non-transition regime context，
是否能稳定改善 cost_bad_10_20 排序、降低 fast-fail / false-repair 成本，
同时不牺牲过多 replay recall？
```

本实验的结论层级只能是 diagnostic / ablation，不得输出 research-entry support。

## 3. 范围

Experiment I 覆盖：

1. transition universe 内的 event-level cost_bad rejector diagnostic。
2. G 产出的 PIT `pit_transition_context` 作为可选 feature / stratification。
3. 与同一 t0 feature set 的 no-context baseline 对照。
4. train-only fit、train-only threshold selection、validation / robustness readout。
5. cost quality、recall retention、density / overlap、segment contribution concentration。
6. ex-post `transition_outcome_label` / `transition_outcome_direction` readout。

Experiment I 不覆盖：

1. 当前 E/H risk_on-only research-entry gate。
2. production entry gate。
3. direct-entry support。
4. transition family rediscovery。
5. conversion / continuation classifier。
6. 使用 `next_regime`、future return、future high / low、future label 作为 t0 feature。
7. trading strategy、portfolio simulation、position sizing。

若实现中把 `transition_outcome_label`、`transition_outcome_direction`、`next_non_transition_regime`
或任何 future segment 字段作为训练特征、threshold selection 字段或 final gate 字段，必须停止并输出：

```text
transition_previous_regime_context_future_outcome_leakage_blocked
```

若实现试图修改、重训或覆盖 E/H 的 risk_on-only selected threshold / manifest / research-entry gate，必须停止并输出：

```text
transition_previous_regime_context_eh_scope_pollution_blocked
```

## 4. Required Inputs

### 4.1 上游 manifests

必须读取：

```text
outputs/manifests/transition_previous_regime_outcome_audit/transition_previous_regime_outcome_audit_manifest.json
outputs/manifests/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_manifest.json
outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
outputs/manifests/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_manifest.json
```

要求：

| manifest | required decision / role |
| --- | --- |
| G manifest | `transition_previous_regime_conditioning_diagnostic_only` |
| H manifest | `risk_on_cost_rejector_diagnostic_only_or_no_candidate` |
| D manifest | post-replay membership source 可读 |
| E manifest | E 原 cost rejector source 可读，用于 lineage 对照 |

G / H 本身是 diagnostic，不得因为其 decision 非 supported 而阻塞 I；但必须在 manifest 中记录：

```text
upstream_g_decision
upstream_h_decision
upstream_e_decision
upstream_source_caveat_status
g_selected_grid_rule_id
```

若 required manifest 缺失、JSON 不可读或 hash 字段无法解析，停止：

```text
transition_previous_regime_context_input_blocked
```

### 4.2 G 产物

必须读取 G 的 materialized previous-regime artifacts：

```text
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_event_assignment.csv.gz
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_segment_catalog.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_universe_binding_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_leakage_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_label_join_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_segment_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_cost_quality_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_recall_retention_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_e1_missed_capture.csv
```

这些文件必须与 G manifest 的 `output_hashes` 一致。任一 hash mismatch，停止：

```text
transition_previous_regime_context_g_artifact_hash_blocked
```

I 必须绑定 G manifest 中的：

```text
selected_grid_rule_id
```

并只使用 `transition_previous_regime_event_assignment.csv.gz` 中同一 `grid_rule_id` 的 rows。
若 event assignment 中出现多个 `grid_rule_id`，但实现未按 `selected_grid_rule_id` 过滤，必须停止：

```text
transition_previous_regime_context_grid_binding_blocked
```

### 4.3 Raw event / label / feature source

必须重新读取 raw event 与 label source：

```text
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/local_cache/candidate_family_event_labels.parquet
outputs/local_cache/cross_section_feature_panel.parquet
outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_scope_retention_by_split_regime.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
```

要求：

1. D label leakage audit 必须 pass。
2. event-level label join 必须按 event key 对齐。
3. 若 membership 与 label source 同时携带 `failure_10_label` / `event_false_repair_20d_label`，必须做布尔语义对账。
4. `cost_bad_10_20 = failure_10_label OR event_false_repair_20d_label`，且只在两个 horizon complete 时可用于 supervised train/eval。
5. `horizon_complete = failure_10_complete AND event_false_repair_20d_complete`。

任一 label 对账失败，停止：

```text
transition_previous_regime_context_label_binding_blocked
```

### 4.4 H feature lineage artifacts

必须读取 H 的 feature lineage 产物：

```text
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_feature_contract.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_feature_delta_from_e.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_asof_join_audit.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_model_registry.csv
```

这些文件必须与 H manifest 的 `output_hashes` 一致。任一 hash mismatch，停止：

```text
transition_previous_regime_context_h_artifact_hash_blocked
```

## 5. Universe 与 Grain

### 5.1 Primary universe

primary universe 固定为：

```text
G transition_previous_regime_event_assignment 中
grid_rule_id == G manifest selected_grid_rule_id
且 rule_event_included = true
且
universe_binding_status in {
  published_and_reconstructed_transition,
  reconstructed_transition_not_published_transition
}
且 pit_transition_context in {
  transition_from_risk_on,
  transition_from_risk_off
}
```

`transition_from_unknown_or_censored` 只能进入 coverage audit，不得进入 primary supervised train/eval。

### 5.2 Grain contract

必须同时维护三种 grain：

| grain | key | 用途 |
| --- | --- | --- |
| event | `event_id` / `canonical_event_id` | feature、score、selected/rejected event |
| segment | `transition_segment_id` | previous-regime context、segment concentration |
| episode | `target_episode_id` | recall retention、E1-missed capture |

禁止在 raw membership row grain 上直接计算 recall / retention。所有 recall 必须先去重到：

```text
model_id, threshold_id, split, window, replay_policy_id, target_episode_id
```

pre-filter event set 定义为 primary universe 内的全部 eligible events。post-filter event set
定义为某个 model arm / threshold selected events。episode denominator 固定为同一 split / window /
replay_policy 下 pre-filter event set 在 D membership 中能触达的 unique `target_episode_id`。
post-filter recall retention 只比较 post-filter captured episodes 相对该 pre-filter denominator 的保留率。

D membership join 规则：

1. 用 `event_id` 优先 join；若缺失则用 `canonical_event_id`。
2. join 后按 `(model_id, threshold_id, split, window, replay_policy_id, target_episode_id)` 去重。
3. `source_id` / `candidate_scope_id` 只作为 lineage readout，不得作为 denominator grain。
4. 若同一 `target_episode_id` 被多个 transition segment 的 selected events 捕获，segment concentration 另行记录，不得在 recall denominator 中重复计数。

### 5.3 Split policy

supervised fit 与 threshold selection 必须使用 `event_split = train`。

validation：

```text
diagnostic_only_no_threshold_tuning
```

robustness：

```text
out_of_time_readout_only
```

若 transition segment 跨 split，event-level train/eval 按 event_split 归属；segment-level power 与 concentration 必须按 `(split, unique transition_segment_id)` 去重，并单列：

```text
cross_split_segment_n
```

## 6. Feature Contract

### 6.1 Baseline t0 features

baseline feature set 必须沿用 H 的 allowed t0 feature contract：

```text
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_feature_contract.csv
```

要求：

1. 只允许 `allowed_as_t0_feature = true` 的字段进入 baseline。
2. 继续剔除 `momentum_percentile_20d_lag20`。
3. I 额外强制剔除以下 regime / binding proxy 字段，即使它们在 H 中 allowed：

```text
event_regime_bucket
market_regime_bucket
published_market_regime_bucket
reconstructed_market_regime_bucket
universe_binding_status
grid_rule_id
rule_event_included
online_confirmation_status
```

原因：H 的 risk_on scope 中 `event_regime_bucket` 基本是常量；但 I 的 transition universe
同时包含 published / reconstructed 口径差异，这些字段会代理 legacy regime mismatch，污染
previous-regime context uplift。

4. daily panel features 必须使用 as-of join：

```text
instrument + latest panel.date <= event_t0_date
```

5. 每个 feature 必须输出 train / validation / robustness missing rate。
6. 任一 allowed feature 在 train 或 robustness missing rate > 5%，该 feature 必须剔除或 fail closed；不得未来填充。

### 6.2 Previous-regime context features

只允许以下 PIT context model features：

```text
pit_transition_context
previous_non_transition_trading_day_n
previous_non_transition_duration_bucket
segment_age_at_event_t0
observed_segment_trading_day_n_asof_t0
days_since_previous_regime_end_asof_event
```

`previous_non_transition_regime` 必须保留在 feature contract / audit output 中，但默认
`model_role = audit_only_collinear_with_pit_transition_context`，不得进入模型矩阵。原因是过滤
unknown 后：

```text
pit_transition_context in {transition_from_risk_on, transition_from_risk_off}
```

与：

```text
previous_non_transition_regime in {risk_on, risk_off}
```

是同一信息的两种编码。为避免 context_only arm 的 coefficient / importance 解读混乱，模型中只保留
`pit_transition_context` 作为 categorical context。

字段来源与派生规则：

| feature | source / derivation |
| --- | --- |
| `pit_transition_context` | G event assignment |
| `previous_non_transition_regime` | G event assignment，audit-only，不进模型矩阵 |
| `previous_non_transition_trading_day_n` | G event assignment |
| `previous_non_transition_duration_bucket` | 从 `previous_non_transition_trading_day_n` 派生，bins 固定为 `1_5`, `6_20`, `21_60`, `61_plus` |
| `segment_age_at_event_t0` | G event assignment，必须是 as-of event_t0 age |
| `observed_segment_trading_day_n_asof_t0` | G event assignment，必须是 as-of event_t0 observed length |
| `days_since_previous_regime_end_asof_event` | 用 G segment catalog 的 `previous_non_transition_end_date` 与 `event_t0_date` 派生；若无法 join，字段必须剔除并记录原因 |

这些字段必须满足：

```text
feature_available_date <= event_t0_date
```

`segment_age_at_event_t0` 与 `observed_segment_trading_day_n_asof_t0` 必须按 event_t0_date
截断计算，不得使用完整 transition segment 终点。禁止使用 `final_segment_trading_day_n`、
`final_segment_calendar_day_n`、`segment_end_date` 或 `segment_remaining_days_ex_post` 作为 model feature。

禁止使用：

```text
segment_end_date
final_segment_trading_day_n
final_segment_calendar_day_n
segment_remaining_days_ex_post
next_non_transition_regime
next_non_transition_start_date
days_to_next_regime_start
transition_outcome_label
transition_outcome_direction
conversion / continuation flags
future_return_*
future_low_*
future_high_*
```

### 6.3 Leakage audit

必须输出 feature-level leakage audit：

| column | required |
| --- | --- |
| `feature_name` | yes |
| `source_artifact` | yes |
| `feature_as_of_policy` | yes |
| `max_feature_as_of_date_minus_event_t0_date` | yes |
| `uses_future_information` | yes |
| `allowed_for_model` | yes |
| `blocked_reason` | yes |

任一 model feature `uses_future_information = true`，停止：

```text
transition_previous_regime_context_feature_leakage_blocked
```

## 7. Model Arms

Experiment I 必须训练并比较以下 diagnostic arms：

| model_id | feature set | 目标 |
| --- | --- | --- |
| `transition_cost_rejector_no_context` | H allowed t0 features only | baseline |
| `transition_cost_rejector_prev_context` | H allowed t0 features + §6.2 model context features | primary ablation |
| `transition_cost_rejector_context_only` | §6.2 model context features only | context standalone diagnostic |

所有 model arms：

1. target 固定为 `cost_bad_10_20`。
2. model type 固定为 `logistic_regression_balanced_l2`，除非 requirement 后续显式修改。
3. preprocessing 必须 train-only：

```text
train_median_impute
nonnegative_log1p_selected_numeric
train_winsorize_1_99
train_zscore
categorical_train_vocab_one_hot
```

4. 不允许在 validation / robustness 上重新 fit scaler、imputer、winsor bounds、category vocabulary。
5. class_weight 固定为 `balanced`。
6. 若 train horizon-complete label < 300 或 positive label < 50，输出 low-power diagnostic，不得训练模型并声明 uplift。
7. 若 train unique `transition_segment_id` < 20，或 train effective segment n < 8，输出 low-power diagnostic；
   可以训练 exploratory model 用于 report，但 final decision 不得为 uplift_observed。

train effective segment n 计算：

```text
1 / sum(train_segment_event_share^2)
```

其中 `train_segment_event_share` 以 horizon-complete train events 计算。

### 7.1 Segment-grouped / purged stability

由于 transition events 在 segment 内高度相关，所有 model arms 必须输出 train 内部 segment-aware
stability readout。

必须至少实现两种稳定性读数：

1. `segment_grouped_cv`：
   - group key = `transition_segment_id`
   - 同一 transition segment 不得同时出现在 train fold 与 holdout fold。
   - `n_splits = min(5, train_unique_segment_n)`，若 `train_unique_segment_n < 5`，输出 low-power。
2. `chronological_purged_segment_cv`：
   - 按 `segment_start_date` 对 train transition segments 排序后做 contiguous block folds。
   - 每个 holdout block 两侧至少 purge 1 个相邻 transition segment。
   - purge 后若 fold train positive_n < 30 或 holdout positive_n < 10，该 fold 标记为 `fold_low_power`。

每个 arm 必须输出：

```text
cv_scheme
fold_id
train_segment_n
holdout_segment_n
purged_segment_n
train_event_n
holdout_event_n
holdout_positive_n
roc_auc
pr_auc
top_decile_lift
fold_status
```

primary uplift comparison 必须额外输出 grouped / purged fold-level uplift：

```text
roc_auc_uplift
pr_auc_uplift
top_decile_lift_uplift
positive_uplift_fold_share
median_roc_auc_uplift
median_pr_auc_uplift
median_top_decile_lift_uplift
stability_status
```

若 prev_context 的 OOS uplift 存在，但 segment-grouped 或 purged stability 的 median uplift < 0，
final decision 不得超过 `transition_previous_regime_context_cost_rejector_diagnostic_no_uplift`
或 `transition_previous_regime_context_diagnostic_low_power`。

## 8. Threshold 与 Grid Search

### 8.1 Threshold grid

每个 model arm 使用同一 keep_fraction grid：

```text
[0.90, 0.875, 0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]
```

threshold 只在 train split 的 `cost_bad_score` 分布上计算：

```text
selected if cost_bad_score <= train_quantile(keep_fraction)
```

### 8.2 Diagnostic selected threshold

因为 I 不是 research-entry gate，selected threshold 只用于同阈值 readout。

train selection rule：

1. 在 train 上 `cost_reduction_relative >= 10%`。
2. train any recall retention >= 80%。
3. train E1-missed capture retention >= 70%。
4. fast-fail rate after <= before。
5. false-repair rate after <= before。
6. 在满足以上条件的阈值里选择最低 keep_fraction；若并列，选择 train cost reduction 更高者。

若某 model arm 找不到 threshold，输出：

```text
selection_status = no_train_diagnostic_threshold
```

不得从 robustness-best 或 validation-best 反向选择 threshold。

### 8.3 Context uplift comparison

primary uplift 必须比较：

```text
transition_cost_rejector_prev_context
vs
transition_cost_rejector_no_context
```

比较必须在同一 split、同一 selected-threshold policy、同一 denominator 下进行。

不得用 prev_context 的 best robustness threshold 与 no_context 的 train selected threshold 比较。

## 9. Metrics

### 9.1 OOS separability

每个 arm / split 输出：

```text
sample_n
positive_n
label_prevalence
roc_auc
pr_auc
top_decile_lift
bottom_decile_cost_bad_rate
brier_score
score_monotonicity_by_decile
feature_missing_coverage
train_unique_segment_n
train_effective_segment_n
```

### 9.2 Cost quality

按 arm / threshold / split 输出：

```text
before_horizon_complete_event_n
after_horizon_complete_event_n
reject_rate
cost_bad_rate_before
cost_bad_rate_after
cost_reduction_relative
fast_fail_rate_before
fast_fail_rate_after
false_repair_rate_before
false_repair_rate_after
```

cost denominator 必须固定为：

```text
same_universe_split_context_horizon_complete_before_after
```

必须同时输出：

1. headline aggregate row：`pit_transition_context = all_primary_contexts`，denominator 为同一 split 的全部 primary universe horizon-complete events。
2. context-sliced rows：分别按 `transition_from_risk_on` / `transition_from_risk_off` 输出，denominator 为同一 split/context 的 horizon-complete events。

final decision 的 uplift gate 默认使用 headline aggregate row；context-sliced rows 只能解释异质性。

### 9.3 Replay recall

按 arm / threshold / split / replay policy 输出：

```text
target_episode_denominator_n
pre_filter_captured_episode_n
post_filter_captured_episode_n
post_filter_any_recall_retention
post_filter_bridge_recall_retention
post_filter_e1_missed_capture_retention
post_filter_e1_missed_captured_episode_n
```

### 9.4 Segment concentration

必须输出每个 arm / threshold / split 的 segment contribution concentration：

```text
selected_transition_segment_n
effective_selected_transition_segment_n
top1_segment_selected_event_share
top1_segment_target_episode_share
top3_segment_target_episode_share
multi_segment_episode_overlap_n
cross_split_segment_n
segment_concentration_status
```

若 robustness 的 selected target episodes 中 top1 segment share > 50%，则该 split 的 uplift 只能是 low-power caveat。

segment episode attribution 规则：

1. 先构造 `(transition_segment_id, target_episode_id)` unique pairs。
2. top share 分母为该 arm/threshold/split/window/replay_policy 的 unique `target_episode_id`。
3. 若一个 `target_episode_id` 被多个 segment 捕获，允许出现在多个 segment numerator 中，但必须计入 `multi_segment_episode_overlap_n`。
4. effective segment n 使用 inverse Herfindahl：`1 / sum(segment_episode_share^2)`。

### 9.5 Ex-post outcome readout

必须输出但不得用于 training / threshold selection：

```text
transition_outcome_label
transition_outcome_direction
```

readout 包括：

1. continuation vs conversion 的 selected / rejected cost quality。
2. per-direction conversion 的 diagnostic-only matrix。
3. from_risk_on vs from_risk_off 的 cost quality。
4. context feature 是否主要只是代理未来 conversion。

如果 prev_context arm 的 uplift 只出现在 ex-post conversion 子样本，而 continuation / aggregate 不稳定，final decision 不得超过：

```text
transition_previous_regime_context_diagnostic_low_power
```

### 9.6 Segment-grouped stability

必须输出 train 内部 grouped / purged stability readout，并在 report 中独立解释。

headline fields：

```text
model_id
cv_scheme
fold_n
valid_fold_n
median_roc_auc
median_pr_auc
median_top_decile_lift
median_roc_auc_uplift_vs_no_context
median_pr_auc_uplift_vs_no_context
positive_uplift_fold_share
fold_low_power_n
stability_status
```

`transition_cost_rejector_context_only` 必须特别报告 grouped stability，因为其特征多为
segment-level 常量。若 context_only 在 event-level 表现好，但 grouped / purged fold 表现不稳，
报告必须明确指出这是 segment-level proxy 风险，而不是可独立泛化的 event-level signal。

## 10. Decision Rules

Experiment I 的 final decision 只能取以下之一：

```text
transition_previous_regime_context_cost_rejector_diagnostic_uplift_observed
transition_previous_regime_context_cost_rejector_diagnostic_no_uplift
transition_previous_regime_context_diagnostic_low_power
transition_previous_regime_context_input_blocked
transition_previous_regime_context_feature_leakage_blocked
transition_previous_regime_context_label_binding_blocked
transition_previous_regime_context_g_artifact_hash_blocked
transition_previous_regime_context_h_artifact_hash_blocked
transition_previous_regime_context_grid_binding_blocked
transition_previous_regime_context_future_outcome_leakage_blocked
transition_previous_regime_context_eh_scope_pollution_blocked
```

### 10.1 Uplift observed 条件

只有同时满足以下条件，才能输出：

```text
transition_previous_regime_context_cost_rejector_diagnostic_uplift_observed
```

1. prev_context arm 与 no_context arm 都有 train selected diagnostic threshold。
2. robustness ROC-AUC uplift >= 0.02，或 robustness PR-AUC uplift >= 0.02。
3. robustness top-decile lift uplift >= 0.15。
4. robustness selected-threshold cost reduction uplift >= 5pp。
5. robustness any recall retention drop vs no_context >= `-0.05`。
6. robustness E1-missed capture retention drop vs no_context >= `-0.05`。
7. robustness segment concentration 未触发 top1 > 50% caveat。
8. `segment_grouped_cv` 的 median ROC-AUC uplift 或 median PR-AUC uplift >= 0，且 positive uplift fold share >= 60%。
9. `chronological_purged_segment_cv` 的 median ROC-AUC uplift 或 median PR-AUC uplift >= 0。
10. validation 与 robustness uplift 同向；validation 不用于调参，只用于 sanity readout。

若只在 train 上 uplift，或 robustness uplift 依赖单个长 transition segment，必须输出 low-power 或 no-uplift。

### 10.2 No uplift 条件

若 inputs / leakage / labels 都通过，但不满足 §10.1，且样本 power 足够，输出：

```text
transition_previous_regime_context_cost_rejector_diagnostic_no_uplift
```

### 10.3 Low power 条件

任一以下条件触发 low-power：

0. train unique transition_segment_id < 20，或 train effective segment n < 8。
1. robustness horizon-complete event_n < 500。
2. robustness positive_n < 100。
3. robustness unique transition_segment_n < 10。
4. robustness selected effective segment_n < 5。
5. robustness top1 segment target episode share > 50%。
6. continuation / conversion 聚合层任一 cell segment_n < 3。这里的聚合层指 across
   `transition_from_risk_on` / `transition_from_risk_off` 后的 `transition_outcome_label`
   cell，不包括 per-direction conversion cell。
7. segment-grouped CV valid_fold_n < 3，或 purged CV valid_fold_n < 3。

输出：

```text
transition_previous_regime_context_diagnostic_low_power
```

## 11. Required Outputs

### 11.1 Tables

必须输出到：

```text
outputs/publishable/tables/transition_previous_regime_context_cost_rejector_ablation/
```

Required tables：

```text
transition_context_ablation_input_audit.csv
transition_context_ablation_upstream_binding_audit.csv
transition_context_ablation_feature_contract.csv
transition_context_ablation_leakage_audit.csv
transition_context_ablation_label_join_audit.csv
transition_context_ablation_training_universe_audit.csv
transition_context_ablation_model_registry.csv
transition_context_ablation_segment_grouped_stability.csv
transition_context_ablation_segment_grouped_uplift.csv
transition_context_ablation_oos_separability.csv
transition_context_ablation_threshold_frontier.csv
transition_context_ablation_selected_threshold_readout.csv
transition_context_ablation_cost_quality_readout.csv
transition_context_ablation_recall_retention_readout.csv
transition_context_ablation_density_overlap_readout.csv
transition_context_ablation_segment_concentration_audit.csv
transition_context_ablation_outcome_readout.csv
transition_context_ablation_uplift_comparison.csv
transition_context_ablation_decision_tiers.csv
```

Allowed event-level outputs：

```text
transition_context_ablation_event_scores.csv.gz
transition_context_ablation_selected_events.csv.gz
transition_context_ablation_rejected_events.csv.gz
```

### 11.2 Reports

必须输出：

```text
outputs/publishable/reports/transition_previous_regime_context_cost_rejector_ablation/transition_previous_regime_context_cost_rejector_ablation_report.md
outputs/publishable/reports/transition_previous_regime_context_cost_rejector_ablation/transition_previous_regime_context_cost_rejector_ablation_contract.md
```

Report 必须包含：

1. final decision。
2. 为什么本实验不并入 E/H gate。
3. model arms 与 feature 差异。
4. train unique / effective segment n，说明 event_n 不等于独立样本数。
5. segment-grouped / purged stability 对照。
6. OOS separability 对照。
7. selected threshold frontier。
8. cost / recall / density readout。
9. segment concentration 与 low-power caveat。
10. ex-post continuation / conversion readout。
11. findings / insight。
12. explicit non-claims。

### 11.3 Manifest

必须输出：

```text
outputs/manifests/transition_previous_regime_context_cost_rejector_ablation/transition_previous_regime_context_cost_rejector_ablation_manifest.json
```

Manifest 必须记录：

1. experiment id。
2. created_at。
3. requirement hash。
4. input paths / hashes / schema fingerprints。
5. upstream G/H/E/D decisions。
6. upstream artifact hashes。
7. feature columns hash。
8. preprocessing hash。
9. previous-regime context feature list。
10. context collinearity policy：`previous_non_transition_regime = audit_only`。
11. train unique / effective segment n。
12. grouped / purged stability summary。
13. forbidden future outcome feature check result。
14. selected model arm / threshold id / keep fraction。
15. final decision。
16. blocked reasons 与 non-pass reasons。
17. output paths / hashes / row counts。
18. event-level gzip compressed hash、uncompressed row count、schema fingerprint。

## 12. Report Non-Claims

报告必须显式声明：

1. 本实验不是 E/H research-entry gate。
2. 本实验不是 direct-entry support。
3. 本实验不是 production-ready model。
4. 本实验不是 transition family rediscovery。
5. 本实验没有训练 conversion / continuation classifier。
6. `transition_outcome_label` / `transition_outcome_direction` 只用于 ex-post readout。
7. 若 uplift observed，也只能说明 previous-regime context 值得进入 future multi-regime rejector 研究，不代表当前可上线。

## 13. Expected Outcome / Interpretation

I 的默认预期不是产生 supported candidate，而是回答 previous-regime context 是否值得进入下一轮
multi-regime cost rejector 研究。

基于 G/H 的既有证据，最可能的合理结果是：

```text
transition_previous_regime_context_cost_rejector_diagnostic_no_uplift
```

或：

```text
transition_previous_regime_context_diagnostic_low_power
```

这两种结果都不表示实现失败。只有在 event-level OOS uplift、segment-grouped stability、
chronological purged stability、recall retention 与 segment concentration 同时过关时，才允许输出
`transition_previous_regime_context_cost_rejector_diagnostic_uplift_observed`。

报告必须避免把以下情况误读成 positive result：

1. 只有 train uplift，validation / robustness 不同向。
2. 只有 event-level ROC-AUC uplift，但 segment-grouped / purged stability 不稳。
3. context_only arm 表现好，但 uplift 主要来自 segment-level 常量或少数长 segment。
4. uplift 只出现在 ex-post conversion 子样本，aggregate 或 continuation 不稳。

## 14. Implementation Command

建议实现脚本：

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/src/run_transition_previous_regime_context_cost_rejector_ablation.py --mode full
```

支持：

```bash
--mode check-inputs
--mode full
```

## 15. Acceptance Criteria

完成标准：

1. 所有 required inputs 均被 input audit 覆盖。
2. G artifact hash binding 通过。
3. E/H manifests 未被修改。
4. feature leakage audit 证明 model features 全部 t0 可见。
5. no_context / prev_context / context_only 三个 arms 均有 model registry；若样本不足，必须有 fail-closed reason。
6. threshold selection 只使用 train。
7. validation / robustness 只读数，不调参。
8. outcome labels 只出现在 readout，不出现在 model feature contract 的 allowed list。
9. `previous_non_transition_regime` 只作为 audit-only collinear field，不进入模型矩阵。
10. training universe audit 输出 train unique / effective segment n。
11. segment-grouped / purged stability audit 可解释 uplift 是否由 segment 内相关虚高。
12. segment concentration audit 可解释 robustness uplift 是否由少数长 segment 主导。
13. final decision 只能取 §10 定义的 diagnostic / blocked 状态。
