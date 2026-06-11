# Requirement Patch: Risk-on / Transition Regime-specific Selected Unions

## 1. 背景

当前 08 full run 已经生成 joint `selected_candidate_union`，并分别在 `risk_on` 与 `transition` 上报告表现。

这个路径可以作为 diagnostic baseline 保留，但它不等价于：

```text
为 risk_on 单独选择 event family union；
为 transition 单独选择 event family union。
```

08 的研究目标本身是修复 `risk_on` 与 `transition` 两类不同 regime 的漏召回。两者可能对应不同市场结构、不同事件机制、不同 bridge quality 与不同 density / overlap trade-off。因此，本 patch 要求在不破坏原有 08 执行路径的前提下，新增 regime-specific selected union 路径。

本 patch 的定位必须收窄为 diagnostic / ablation：

1. 它回答的问题是：把 `risk_on` 与 `transition` 分开 selection，是否会选出与 joint selected union 显著不同的 family / variant 集合，并改变 gate 结论。
2. 它不是 08 报告推荐主线的替代品。若现有 evidence 已显示失败主因是 bridge-positive quality，而非 joint-vs-regime-specific selection 方式，则主修复路径仍应优先是 bridge-positive ranker / rejector。
3. 如果 preflight 发现两组 regime-specific top-ranked variants 大概率仍收敛到相同低 density 但低 bridge-quality 的 family，本 patch 只产出诊断结论，不应继续消耗 full rerun 成本去重复已知 bridge-blocked 结论。
4. 如果进一步 evidence 证明 risk_on 的 R 系列是 high-recall / high-bridge 但 density-binding，则 risk_on 主线应转向 `requirement_patch_risk_on_r_series_density_compression.md`，而不是继续扩展本 regime-split diagnostic。

## 2. 本 patch 的目标

新增一个独立的 post-run / extension experiment：

```text
08 regime-specific selected union patch
```

它必须分别构建：

1. `selected_risk_on_candidate_union`
2. `selected_transition_candidate_union`
3. 可选保留 `selected_joint_candidate_union` 作为原 08 joint path 的对照别名，但不得替代上述两个 regime-specific union。

核心要求：

1. `risk_on` union 只能使用 `risk_on` 的 train evidence 做 selection。
2. `transition` union 只能使用 `transition` 的 train evidence 做 selection。
3. 两个 union 可以选择到相同 family，也可以不同；相同不是问题，但必须由各自 selection path 独立得出。
4. 两个 union 的 density、bridge、stability、overlap、cluster ablation、timing/basis 必须分开评估。
5. 原有 08 full run 的 `selected_candidate_union`、report、manifest、tables 不得被覆盖或改变。

### 2.1 Cheap feasibility preflight

在 full patch run 之前，必须先执行 cheap feasibility preflight。preflight 只使用现成 publishable tables，不重算 events / labels / capture：

1. `candidate_family_incremental_recall_over_e1.csv`
2. `candidate_family_bridge_positive_recall.csv`
3. `candidate_family_bridge_exclusion_audit.csv`
4. `candidate_family_density_summary.csv`
5. `candidate_family_label_quality_readout.csv`
6. `candidate_family_run_capability_summary.csv`

preflight 必须分别构建：

```text
risk_on_only_preflight_rank
transition_only_preflight_rank
```

ranking 口径必须与 §5.0.2 selection config 一致，并且只允许使用：

1. `episode_split == train`
2. `market_regime_bucket == selection_regime`
3. `window == before_first_50pct`
4. eligible family / variant status
5. density / bridge / label quality 的 train same-regime evidence

preflight 必须输出：

```text
outputs/publishable/tables/regime_specific_unions/regime_specific_union_preflight_frontier.csv
outputs/publishable/tables/regime_specific_unions/regime_specific_union_preflight_summary.csv
```

`regime_specific_union_preflight_frontier.csv` 至少包含：

1. `selection_regime`
2. `candidate_scope_id`
3. `family_id`
4. `variant_id`
5. `preflight_rank`
6. `would_select_flag`
7. `train_incremental_recall_over_e1`
8. `train_incremental_captures_over_e1`
9. `train_bridge_recall_delta_vs_e1`
10. `density_vs_e1_full_denominator`
11. `label_completeness_rate`
12. `next_open_executable_rate`
13. `density_prefilter_pass`
14. `bridge_threshold_pass`
15. `filter_reason`

`regime_specific_union_preflight_summary.csv` 至少包含：

1. `same_family_set_flag`
2. `same_variant_set_flag`
3. `risk_on_would_select_family_ids`
4. `transition_would_select_family_ids`
5. `risk_on_would_select_candidate_scope_ids`
6. `transition_would_select_candidate_scope_ids`
7. `family_set_jaccard`
8. `variant_set_jaccard`
9. `max_preflight_bridge_delta_improvement_vs_joint`
10. `low_density_bridge_tension_flag`
11. `preflight_decision`

preflight decision 规则：

1. 如果 `same_variant_set_flag == true` 且 `same_family_set_flag == true`，并且 `max_preflight_bridge_delta_improvement_vs_joint < 0.03`，则停止 full patch run，并返回：

```text
regime_specific_union_preflight_no_material_split_benefit
```

2. 如果 family set 或 variant set 分叉，或 bridge delta 预计改善达到 `+3 pct` 以上，才允许进入 full patch run。
3. 如果实现者通过 config 强制 full run，manifest 必须记录 `preflight_override_full_run = true` 和 override reason。

### 2.2 已知结构张力

当前 08 报告中的 evidence 已提示：joint selected union 失败的核心否决证据更可能来自 bridge gate，而不是 joint selection 本身。实现与报告必须显式承认以下结构张力：

1. `train_selection_max_density_vs_e1 = 0.50` 会优先保留低 density family。
2. 现有高 bridge-positive recall 的大族可能同时具有 `density_vs_e1 > 1.50`，会被 density prefilter 提前淘汰。
3. 因此 regime-specific selection 很可能仍选择 T4 / T7 这类低 density、低 bridge-quality family，并在 bridge gate 失败。
4. 这不是实现 bug，而是本 patch 要诊断的机制：recall / density prefilter 与 bridge quality gate 是否结构性互斥。

所有 report 与 gate summary 必须输出：

```text
low_density_bridge_tension_flag
```

并解释该 flag 是否导致 full patch 被 preflight 停止，或是否导致 full patch 最终 `regime_specific_union_bridge_blocked`。

## 3. 允许复用的内容

实现允许复用当前 08 的代码和 full-run artifacts，包括：

1. `candidate_family_event_instances.csv`
2. `candidate_family_canonical_events.csv`
3. `candidate_family_incremental_recall_over_e1.csv`
4. `candidate_family_density_summary.csv`
5. `candidate_family_bridge_positive_recall.csv`
6. `candidate_family_bridge_exclusion_audit.csv`
7. `candidate_family_label_quality_readout.csv`
8. `candidate_family_false_repair_diagnostic.csv`
9. `candidate_family_overlap_matrix.csv`
10. `candidate_family_cluster_ablation.csv`
11. local cache 中的 candidate labels / capture / feature panel，只要 hash 可审计。

允许从当前 pipeline 中复用以下函数或逻辑：

1. event canonicalization
2. capture linking
3. E1-only baseline rebuild
4. incremental recall calculation
5. density calculation
6. label quality readout
7. bridge exclusion audit
8. timing / basis comparison
9. mechanism cluster summary / ablation
10. manifest writer

但新增路径必须以独立入口、独立 output key、独立 report 和独立 manifest metadata 闭合。

### 3.1 必需输入 artifact

本 patch 是 08 full run 的只读 extension。实现必须显式读取并校验以下输入：

1. `source_08_run_manifest_json`
   - 默认路径：`outputs/manifests/run_manifest.json`
   - 必须存在。
   - 必须记录 `run_scope == full`。
   - 必须包含原 08 output artifact 的 path / hash / row count / column schema。
2. `candidate_family_event_instances.csv`
3. `candidate_family_canonical_events.csv`
4. `candidate_family_incremental_recall_over_e1.csv`
5. `candidate_family_density_summary.csv`
6. `candidate_family_bridge_positive_recall.csv`
7. `candidate_family_bridge_exclusion_audit.csv`
8. `candidate_family_label_quality_readout.csv`
9. `candidate_family_false_repair_diagnostic.csv`
10. `candidate_family_overlap_matrix.csv`
11. `candidate_family_cluster_ablation.csv`
12. `candidate_vs_e1_timing_basis_comparison.csv`
13. `candidate_family_run_capability_summary.csv`
14. `regime_recall_baseline_07_e1_only.csv`
15. 当前 patch requirement 文件自身。

如果实现需要重新构建 canonical union、capture、label 或 timing/basis，而不是只从 existing tables 派生，则还必须读取并校验：

1. `candidate_family_event_labels.parquet`
2. `candidate_family_capture.parquet`
3. `cross_section_feature_panel.parquet`
4. 原 08 config
5. 原 08 source git revision

如果 local cache 不存在，实现可以选择在 patch 独立 output/cache 目录中重算，但必须满足：

1. 不覆盖原 08 `outputs/local_cache/`。
2. 不覆盖原 08 publishable tables。
3. 在 patch manifest 中记录 `recomputed_from_source_artifacts = true`。
4. 记录重算所用 input paths / hashes / row counts / column schema。

如果必需输入缺失、hash 不匹配、schema 不满足本 patch 要求，必须返回：

```text
regime_specific_union_input_blocked
```

不得用部分可用 artifact 继续产出 headline decision。

### 3.2 原 08 只读边界

以下路径在 patch 执行中必须视为 read-only：

```text
outputs/publishable/tables/
outputs/publishable/reports/risk_on_transition_recall_exploration_report.md
outputs/manifests/run_manifest.json
outputs/local_cache/
```

patch manifest 只能记录这些 source artifact 的 hash，不能改写 source artifact。

## 4. 禁止事项

实现不得：

1. 修改原有 `selected_candidate_union` 的语义。
2. 覆盖 `outputs/publishable/reports/risk_on_transition_recall_exploration_report.md`。
3. 覆盖原有 `outputs/manifests/run_manifest.json` 的 full-run decision。
4. 改变已有 publishable tables 的 schema，除非原路径同时保持 backward-compatible。
5. 把 risk_on 和 transition 的 train evidence 合并后再 selection。
6. 用 validation 或 robustness 调参。
7. 因为某 family 在两个 regime 都入选，就把两个 union 合并成一个 headline union。
8. 为了让某 regime 的结果更好而在 selection 后按 target episode 过滤事件。
9. 使用 target episode membership 反向决定 event generation 或 canonicalization。

## 5. Regime-specific selection contract

### 5.0 术语与 inclusion policy

本 patch 必须显式区分以下字段：

1. `selection_regime`
   - 取值：`risk_on` 或 `transition`。
   - 只表示该 union 的 train-only family / variant selection 使用哪个 episode regime evidence。
2. `episode_regime_bucket`
   - target episode 的 regime。
   - 对应原表中的 `market_regime_bucket` when grouped by target episode。
   - 用于 recall / bridge / stability denominator。
3. `event_regime_bucket`
   - event `t0` 当天的 market regime。
   - 只能作为 event-regime-gated variant 或 diagnostic 维度。
   - 不得替代 `episode_regime_bucket` 做 headline denominator。
4. `union_id`
   - 必须至少包含：
     - `selected_risk_on_candidate_union`
     - `selected_transition_candidate_union`

Regime-specific union 的事件 inclusion policy 必须固定为：

```text
先按 selection_regime 独立选择 candidate_family_variant；
再取这些 selected variants 在完整 evaluated universe 上已经生成的所有 event instances；
按 instrument + event_t0_date canonicalize；
最后 link 到所有 06 target episodes，并按 episode_regime_bucket 切片评估。
```

换言之：

1. selection 使用对应 regime 的 train episode evidence。
2. event inclusion 不得按 target episodes 过滤。
3. event inclusion 不得在 selection 后额外按 `episode_regime_bucket` 过滤。
4. event inclusion 不得在 selection 后额外按 `event_regime_bucket` 过滤，除非该 variant 本身就是 `event_regime_gated`。
5. 如果实现额外输出 `event_regime_filtered` diagnostic scope，必须使用不同 `union_id`，不得作为 headline union。

### 5.0.1 Selection universe

默认 selection unit 必须是：

```text
candidate_scope_type == candidate_family_variant
```

不得把以下 scope 作为 selection unit：

1. `candidate_family__all_variants`
2. `all_new_candidate_union`
3. `07_e1_only`
4. `07_full_union`
5. 原 `selected_candidate_union`

默认 eligible statuses：

```text
runnable_existing_data
fallback_variant
```

`diagnostic_only` family 默认不得进入 regime-specific selected union。若某实现希望允许 diagnostic-only，必须在 patch config 中显式打开，并在报告中降级为 diagnostic-only conclusion，不得直接给 `candidate_supported_for_meta_label`。

每个 `selection_regime` 内，同一 `family_id` 默认最多选择一个 `variant_id`。若同一 family 有多个 variant 通过筛选，必须按 selection score 选择排名最高的 variant，并在 frontier 中保留被淘汰 variant 的 `filter_reason = same_family_lower_ranked_variant`。

### 5.0.2 Selection config

必须在 patch config 或 manifest 中冻结以下参数：

| parameter | default |
|---|---:|
| `selection_unit` | `candidate_family_variant` |
| `eligible_statuses` | `runnable_existing_data,fallback_variant` |
| `focus_window` | `before_first_50pct` |
| `train_selection_min_incremental_recall` | `0.005` |
| `train_selection_max_density_vs_e1` | `0.50` |
| `max_selected_variants_per_regime` | `6` |
| `same_family_variant_policy` | `keep_best_per_family_per_regime` |
| `bridge_recall_delta_materiality_threshold` | `-0.03` |
| `bridge_exclusion_rate_excess_threshold` | `0.02` |
| `forward_big_winner_rate_delta_threshold` | `-0.03` |
| `sample_small_denominator_threshold` | `30` |
| `preflight_required` | `true` |
| `run_full_patch_when_preflight_no_material_split_benefit` | `false` |
| `validation_usage` | `read_only` |
| `robustness_usage` | `read_only` |

如果实现覆盖默认值，必须在 `regime_specific_union_selection_frontier.csv` 和报告中明确记录。

`max_selected_variants_per_regime = 6` 是安全上限，不是预期会 binding 的核心约束。在 single-regime selection 且 `train_selection_max_density_vs_e1 = 0.50` 的默认配置下，大多数候选会先被 density prefilter 或 label / execution 检查排除；bridge threshold 必须作为 audit / gate 字段保留。报告必须说明最终 selected count 是否触达该上限。

`train_selection_max_density_vs_e1` 与 density drag 是两个不同口径：

1. density prefilter 使用 `density_vs_e1_full_denominator <= 0.50`，发生在 selection 之前。
2. density drag 使用 `incremental_recall_over_e1 < +2 pct` 且 `family_density_share_full_union_events > 20%`，发生在 union 形成之后。

frontier、density summary 与报告必须同时列出两套字段，避免 prefilter pass 与 density drag flag 被混读。

### 5.1 Risk-on selection

`selected_risk_on_candidate_union` 的 family / variant 选择必须满足：

```text
episode_split == train
market_regime_bucket == risk_on
window == before_first_50pct
family_input_status in eligible_statuses
```

selection score 至少包含：

1. `train_risk_on_incremental_recall_over_e1`
2. `train_risk_on_incremental_captures_over_e1`
3. `density_vs_e1_full_denominator`
4. `family_density_full_denominator`
5. `bridge_positive_recall_delta_vs_e1_train_risk_on`
6. optional: `better_basis_first_event_count_train_risk_on`
7. optional: `false_repair_10d_rate` / `false_repair_20d_rate`

默认排序建议：

```text
1. pass density prefilter
2. pass label / execution completeness
3. higher train_risk_on_incremental_recall
4. higher train_risk_on_incremental_captures
5. lower density_vs_e1_full_denominator
6. lower overlap with already selected family
```

### 5.2 Transition selection

`selected_transition_candidate_union` 的 family / variant 选择必须满足：

```text
episode_split == train
market_regime_bucket == transition
window == before_first_50pct
family_input_status in eligible_statuses
```

selection score 至少包含：

1. `train_transition_incremental_recall_over_e1`
2. `train_transition_incremental_captures_over_e1`
3. `density_vs_e1_full_denominator`
4. `family_density_full_denominator`
5. `bridge_positive_recall_delta_vs_e1_train_transition`
6. optional: `better_basis_first_event_count_train_transition`
7. optional: `false_repair_10d_rate` / `false_repair_20d_rate`

默认排序建议同 risk_on，但不得引用 risk_on train evidence。

### 5.3 Shared family rule

同一个 `family_id` 可以同时进入两个 regime-specific unions，但必须在输出中明确标注：

1. `selected_for_risk_on_union`
2. `selected_for_transition_union`
3. `selected_for_both_regime_unions`
4. `risk_on_selection_rank`
5. `transition_selection_rank`
6. `selection_reason_by_regime`

如果两个 union 最终选择完全相同，也必须报告：

```text
same_family_set_flag = true
same_variant_set_flag = true / false
```

并解释这是独立 selection 后的结果，而不是 joint selection 的复用。

### 5.4 Selection audit

必须输出完整 selection audit，证明 selection 只使用 train evidence。

`regime_specific_union_selection_frontier.csv` 至少包含：

1. `selection_regime`
2. `candidate_scope_id`
3. `candidate_scope_type`
4. `family_id`
5. `variant_id`
6. `family_input_status`
7. `selection_unit`
8. `eligible_status_flag`
9. `train_selection_denominator_episodes`
10. `train_selection_incremental_captures_over_e1`
11. `train_selection_incremental_recall_over_e1`
12. `train_selection_unique_captures_not_in_e1_e2_e3_e6`
13. `train_selection_bridge_recall_delta_vs_e1`
14. `train_selection_bridge_exclusion_delta_vs_e1`
15. `density_full_denominator`
16. `density_vs_e1_full_denominator`
17. `events_per_instrument_year_p95`
18. `label_completeness_rate`
19. `next_open_executable_rate`
20. `false_repair_10d_rate`
21. `false_repair_20d_rate`
22. `same_family_candidate_rank`
23. `selection_rank`
24. `selected_for_regime_union`
25. `filter_reason`
26. `density_prefilter_pass`
27. `density_prefilter_threshold`
28. `density_drag_flag`
29. `density_drag_incremental_recall_threshold`
30. `density_drag_density_share_threshold`
31. `bridge_threshold_pass`
32. `bridge_recall_delta_materiality_threshold`
33. `bridge_exclusion_rate_excess_threshold`
34. `low_density_bridge_tension_flag`
35. `max_selected_variants_per_regime_binding_flag`
36. `selection_config_hash`

`filter_reason` 至少支持：

```text
selected
not_eligible_status
below_min_train_incremental_recall
density_prefilter_failed
label_execution_prefilter_failed
same_family_lower_ranked_variant
max_selected_variants_exceeded
diagnostic_only_excluded
input_missing
```

Validation / robustness metrics 可以出现在 frontier 中，但必须在 selection 完成后 join，并标记：

```text
post_selection_read_only_metric = true
```

不得把 validation / robustness 排名、过滤或调参写入 selection score。

## 6. Evaluation contract

每个 regime-specific union 必须在所有 split / all regime 上评估，但 headline gate 只对对应 regime 解释：

### 6.1 Risk-on union headline

headline metrics：

1. `train risk_on`
2. `validation risk_on`，但 denominator 小于 `sample_small_denominator_threshold` 时只作为 diagnostic。
3. `robustness risk_on`
4. `all risk_on`

同时必须报告 spillover：

1. `transition` 表现
2. `risk_off` 表现
3. all-regime aggregate

### 6.2 Transition union headline

headline metrics：

1. `train transition`
2. `validation transition`
3. `robustness transition`
4. `all transition`

同时必须报告 spillover：

1. `risk_on` 表现
2. `risk_off` 表现
3. all-regime aggregate

### 6.3 Metrics

每个 union 至少输出：

1. denominator episodes
2. E1-only captured episodes
3. candidate-only captured episodes
4. E1 + candidate captured episodes
5. incremental captures over E1
6. incremental recall over E1，单位为 percentage points
7. unique captures not in E1 / E2 / E3 / E6
8. earlier first-event captures vs E1
9. better-basis first-event captures vs E1
10. missed episodes remaining
11. bridge-positive recall
12. bridge recall delta vs E1
13. bridge exclusion rate delta vs E1
14. density full denominator
15. density eligible gated denominator
16. density vs E1 full denominator
17. density vs same gated denominator
18. family density share inside the regime-specific union
19. density drag flag
20. event label completeness
21. next-open executable rate
22. false-repair 10d / 20d rate
23. mechanism cluster share
24. cluster ablation result
25. overlap with E1 / E2 / E3 / E6 and with other selected union

所有 recall / bridge 指标必须同时保留以下字段：

1. `union_id`
2. `selection_regime`
3. `evaluation_split`
4. `episode_regime_bucket`
5. `event_regime_bucket`，若该 metric 非 event-regime slice，则填 `all`
6. `window`
7. `denominator_policy`
8. `percentage_point_convention`

`incremental_recall_over_e1` 必须按：

```text
incremental_captures_over_e1 / same evaluation_split + same episode_regime_bucket + same window denominator
```

不得用 all-regime denominator 解释 single-regime incremental recall。

## 7. Gate contract

必须先给出一个 patch-level decision：

```text
regime_specific_union_patch_decision
```

取值至少包含：

```text
regime_specific_union_input_blocked
regime_specific_union_preflight_no_material_split_benefit
regime_specific_union_full_patch_evaluated
```

只有当 `regime_specific_union_patch_decision == regime_specific_union_full_patch_evaluated` 时，才必须分别给出两个 full-run regime decision：

```text
risk_on_regime_specific_union_decision
transition_regime_specific_union_decision
```

每个 decision 取值：

```text
regime_specific_union_input_blocked
regime_specific_union_no_incremental_recall
regime_specific_union_density_blocked
regime_specific_union_bridge_blocked
regime_specific_union_sample_blocked
regime_specific_union_diagnostic_only
regime_specific_union_candidate_supported_for_meta_label
```

### 7.1 Recall gate

对应 regime 的 union 至少满足其一：

1. robustness incremental recall over E1 >= `+8 pct`
2. train + robustness missed capture count >= `30`
3. earlier first-event count vs E1 >= `30` 且 bridge-positive 不劣于 E1
4. better-basis first-event count vs E1 >= `30` 且 forward label quality 不劣于 E1

以上 gate 只使用对应 `selection_regime` 的 same split / same `episode_regime_bucket` / same window denominator。

例如：

```text
risk_on_regime_specific_union_decision:
  robustness gate denominator = robustness + episode_regime_bucket == risk_on + before_first_50pct

transition_regime_specific_union_decision:
  robustness gate denominator = robustness + episode_regime_bucket == transition + before_first_50pct
```

gate 3 的 "bridge-positive 不劣于 E1" 必须量化为：

```text
bridge_recall_delta_vs_e1 >= bridge_recall_delta_materiality_threshold
bridge_exclusion_rate_delta_vs_e1 <= bridge_exclusion_rate_excess_threshold
```

默认阈值为：

```text
bridge_recall_delta_materiality_threshold = -0.03
bridge_exclusion_rate_excess_threshold = 0.02
```

gate 4 的 "forward label quality 不劣于 E1" 必须量化为：

```text
label_completeness_rate >= 0.70
next_open_executable_rate >= 0.95
event_big_winner_120d_rate_delta_vs_e1 >= forward_big_winner_rate_delta_threshold
```

默认 `forward_big_winner_rate_delta_threshold = -0.03`。如果 source table 不包含 E1 的 event-level forward winner rate baseline，gate 4 不得直接 pass，必须返回 `forward_label_quality_baseline_missing` diagnostic reason。

### 7.2 Density gate

对应 regime union 必须：

1. headline 使用 full evaluated denominator density。
2. union canonical density 不超过 config 上限。
3. family density 不超过 config 上限。
4. 单一 family density share 不超过 `35%`。
5. 若某 family incremental recall < `+2 pct` 且 density share > `20%`，标记 density drag。

Density 必须同时报告两套 share：

1. `family_density_share_full_union_events`
   - 分母为该 regime-specific union 的 full evaluated event count。
   - 用于 headline density gate。
2. `family_density_share_headline_episode_regime_captures`
   - 分母为该 union 在对应 headline episode regime 中捕捉到的 candidate events / episodes。
   - 只作为 diagnostic，不能替代 full denominator density gate。

如果两者结论冲突，headline gate 以 `family_density_share_full_union_events` 为准。

### 7.3 Bridge / label gate

对应 regime union 必须：

1. label completeness >= `70%`
2. next-open executable rate >= `95%`
3. bridge-positive recall 不得低于 E1-only 同 split / regime baseline 超过 `3 pct`，即 `bridge_recall_delta_vs_e1 >= -0.03`。
4. bridge exclusion rate 不得高于 E1-only 同 split / regime baseline 超过 `2 pct`，即 `bridge_exclusion_rate_delta_vs_e1 <= 0.02`。
5. false-repair 10d / 20d 必须报告。

§7.1 的 earlier / better-basis recall gate 与本节 bridge / label gate 必须引用同一组阈值，不得在两处各自定义不同的 "not worse" 标准。

### 7.4 Stability gate

必须报告：

1. train / validation / robustness 是否方向一致。
2. validation denominator 是否 sample-small：`denominator_episodes < sample_small_denominator_threshold`，默认阈值为 `30`。
3. robustness 是否仍有正增量。
4. 是否集中在单一 board / 少数年份 / 少数 instrument。
5. cluster ablation 后是否仍有实质增量。

## 8. Required outputs

不得覆盖原 08 outputs。新增 outputs 必须使用独立命名。

建议输出目录：

```text
outputs/publishable/tables/regime_specific_unions/
outputs/publishable/reports/regime_specific_unions/
outputs/manifests/regime_specific_unions/
```

preflight 必须总是输出：

1. `regime_specific_union_preflight_frontier.csv`
2. `regime_specific_union_preflight_summary.csv`

如果 preflight decision 为 `regime_specific_union_preflight_no_material_split_benefit`，可以不生成 full patch tables，但仍必须生成独立 report 与 manifest。manifest 必须为未生成的 full tables 写明：

```text
not_generated_reason = preflight_no_material_split_benefit
```

若 preflight 允许进入 full patch run，MVP headline-required tables 必须输出：

1. `regime_specific_union_selection_frontier.csv`
2. `regime_specific_union_selected_variants.csv`
3. `regime_specific_union_incremental_recall_over_e1.csv`
4. `regime_specific_union_bridge_positive_recall.csv`
5. `regime_specific_union_density_summary.csv`
6. `regime_specific_union_gate_summary.csv`

full diagnostic-optional tables 建议输出，但不得作为 MVP 完成的硬前置：

1. `regime_specific_union_canonical_events.csv`
2. `regime_specific_union_recall_by_split_regime.csv`
3. `regime_specific_union_bridge_exclusion_audit.csv`
4. `regime_specific_union_density_denominator_comparison.csv`
5. `regime_specific_union_label_quality_readout.csv`
6. `regime_specific_union_false_repair_diagnostic.csv`
7. `regime_specific_union_timing_basis_comparison.csv`
8. `regime_specific_union_overlap_matrix.csv`
9. `regime_specific_union_cluster_ablation.csv`
10. `regime_specific_union_spillover_diagnostic.csv`

### 8.1 Required output schema

除 manifest 和 report 外，所有 patch publishable tables 必须包含：

1. `source_08_manifest_hash`
2. `patch_requirement_hash`

除 preflight tables 外，所有 full patch publishable tables 还必须包含：

1. `union_id`
2. `selection_regime`

如果表的粒度是 split / regime / window，还必须包含：

1. `evaluation_split`
2. `episode_regime_bucket`
3. `event_regime_bucket`
4. `window`

关键表 schema 要求：

`regime_specific_union_preflight_frontier.csv` 至少包含：

1. `selection_regime`
2. `candidate_scope_id`
3. `candidate_scope_type`
4. `family_id`
5. `variant_id`
6. `family_input_status`
7. `preflight_rank`
8. `would_select_flag`
9. `train_selection_denominator_episodes`
10. `train_incremental_captures_over_e1`
11. `train_incremental_recall_over_e1`
12. `train_bridge_recall_delta_vs_e1`
13. `train_bridge_exclusion_delta_vs_e1`
14. `density_vs_e1_full_denominator`
15. `label_completeness_rate`
16. `next_open_executable_rate`
17. `density_prefilter_pass`
18. `bridge_threshold_pass`
19. `low_density_bridge_tension_flag`
20. `filter_reason`
21. `source_08_manifest_hash`
22. `patch_requirement_hash`

`regime_specific_union_preflight_summary.csv` 至少包含：

1. `preflight_decision`
2. `same_family_set_flag`
3. `same_variant_set_flag`
4. `risk_on_would_select_family_ids`
5. `transition_would_select_family_ids`
6. `risk_on_would_select_candidate_scope_ids`
7. `transition_would_select_candidate_scope_ids`
8. `family_set_jaccard`
9. `variant_set_jaccard`
10. `max_preflight_bridge_delta_improvement_vs_joint`
11. `preflight_override_full_run`
12. `low_density_bridge_tension_flag`
13. `source_08_manifest_hash`
14. `patch_requirement_hash`

`regime_specific_union_selected_variants.csv` 至少包含：

1. `union_id`
2. `selection_regime`
3. `candidate_scope_id`
4. `family_id`
5. `variant_id`
6. `family_input_status`
7. `mechanism_cluster`
8. `selection_rank`
9. `selected_for_risk_on_union`
10. `selected_for_transition_union`
11. `selected_for_both_regime_unions`
12. `selection_reason_by_regime`
13. `train_selection_incremental_recall_over_e1`
14. `density_vs_e1_full_denominator`
15. `bridge_recall_delta_vs_e1_train_selection_regime`
16. `bridge_recall_delta_materiality_threshold`
17. `bridge_threshold_pass`
18. `low_density_bridge_tension_flag`

`regime_specific_union_canonical_events.csv` 至少包含：

1. `union_id`
2. `selection_regime`
3. `event_id`
4. `canonical_event_id`
5. `instrument`
6. `event_t0_date`
7. `event_regime_bucket`
8. `event_split`
9. `primary_family_id`
10. `primary_variant_id`
11. `triggered_family_ids`
12. `triggered_family_variants`
13. `raw_source_event_ids`
14. `source_candidate_scope_ids`

`regime_specific_union_incremental_recall_over_e1.csv` 至少包含：

1. `union_id`
2. `selection_regime`
3. `evaluation_split`
4. `episode_regime_bucket`
5. `window`
6. `denominator_episodes`
7. `e1_only_captured_episodes`
8. `candidate_captured_episodes`
9. `e1_plus_candidate_captured_episodes`
10. `incremental_captures_over_e1`
11. `incremental_recall_over_e1`
12. `unique_captures_not_in_e1_e2_e3_e6`
13. `earlier_first_event_captures_vs_e1`
14. `better_basis_first_event_captures_vs_e1`
15. `percentage_point_convention`

`regime_specific_union_density_summary.csv` 至少包含：

1. `union_id`
2. `selection_regime`
3. `candidate_scope_id`
4. `family_id`
5. `variant_id`
6. `event_count`
7. `canonical_event_count`
8. `density_full_denominator`
9. `density_eligible_gated_denominator`
10. `density_vs_e1_full_denominator`
11. `density_vs_same_gated_denominator`
12. `events_per_instrument_year_mean`
13. `events_per_instrument_year_p50`
14. `events_per_instrument_year_p95`
15. `family_density_share_full_union_events`
16. `family_density_share_headline_episode_regime_captures`
17. `density_drag_flag`
18. `density_prefilter_pass`
19. `density_prefilter_threshold`
20. `density_drag_incremental_recall_threshold`
21. `density_drag_density_share_threshold`
22. `headline_density_gate_pass`

`regime_specific_union_gate_summary.csv` 至少包含：

1. `union_id`
2. `selection_regime`
3. `regime_specific_union_patch_decision`
4. `decision`
5. `recall_gate_pass`
6. `density_gate_pass`
7. `bridge_gate_pass`
8. `label_execution_gate_pass`
9. `stability_gate_pass`
10. `gate_failures`
11. `headline_robustness_incremental_recall_over_e1`
12. `headline_train_robustness_missed_capture_count`
13. `headline_bridge_recall_delta_vs_e1_min`
14. `headline_density_full_denominator`
15. `headline_family_density_share_max`
16. `sample_small_caveat`
17. `sample_small_denominator_threshold`
18. `bridge_recall_delta_materiality_threshold`
19. `bridge_exclusion_rate_excess_threshold`
20. `forward_big_winner_rate_delta_threshold`
21. `preflight_decision`
22. `low_density_bridge_tension_flag`

`regime_specific_union_spillover_diagnostic.csv` 至少包含：

1. `union_id`
2. `selection_regime`
3. `spillover_regime_bucket`
4. `evaluation_split`
5. `incremental_recall_over_e1`
6. `bridge_recall_delta_vs_e1`
7. `density_note`
8. `interpretation`

必须输出独立报告：

```text
outputs/publishable/reports/regime_specific_unions/risk_on_transition_regime_specific_union_report.md
```

必须输出独立 manifest：

```text
outputs/manifests/regime_specific_unions/regime_specific_union_manifest.json
```

manifest 必须记录：

1. input artifact paths
2. input hashes
3. output artifact paths
4. output hashes
5. row counts
6. column schema
7. source 08 run manifest hash
8. source 08 code git revision
9. patch requirement hash
10. patch selection config path / hash
11. source 08 artifacts read-only verification result
12. preflight decision
13. preflight override flag / reason
14. full table `not_generated_reason`，若 preflight 停止 full patch
15. threshold config values used by bridge / density / sample-small gates

## 9. Report requirements

独立报告必须用中文撰写，并至少包含：

1. patch 背景：为什么 joint selected union 不够，以及本 patch 为什么只是 diagnostic / ablation，不替代 P0 bridge-positive ranker / rejector 主线。
2. 原 08 joint selected union 的简短对照。
3. preflight 方法、preflight decision，以及是否有证据表明 regime-specific selection 会显著分叉。
4. `low_density_bridge_tension_flag` 的数据解释：低 density prefilter 与 bridge gate 是否结构性互斥。
5. risk_on-specific selection 方法。
6. transition-specific selection 方法。
7. 两个 union 的 selected variants 对照。
8. risk_on headline recall / density / bridge / label / stability。
9. transition headline recall / density / bridge / label / stability。
10. spillover diagnostic：risk_on union 在 transition/risk_off 的表现，transition union 在 risk_on/risk_off 的表现。
11. shared family / different family 分析。
12. high-recall high-density family 为什么被排除。
13. R 系列、T 系列、fallback / diagnostic-only family 的角色说明。
14. overlap 与 cluster ablation。
15. timing / better-basis 结果。
16. false-repair 与 rejector 建议，且必须说明这些建议与 P0 bridge-positive ranker / rejector 的关系。
17. 最终两个 decision；若 preflight 停止 full patch，则报告 `regime_specific_union_preflight_no_material_split_benefit`，不伪造两个 full-run decision。
18. 明确说明本 patch 不是交易信号、不是模型、不是回测。

## 10. Tests

必须新增或复用测试覆盖：

1. 原 `selected_candidate_union` 输出路径不被覆盖。
2. preflight 使用 existing publishable tables，不触发 event / label / capture 重算。
3. preflight 若发现 `same_variant_set_flag == true`、`same_family_set_flag == true` 且 `max_preflight_bridge_delta_improvement_vs_joint < 0.03`，必须停止 full patch run 并返回 `regime_specific_union_preflight_no_material_split_benefit`。
4. preflight override full run 时，manifest 必须记录 `preflight_override_full_run = true` 与 override reason。
5. risk_on selection 不读取 transition train evidence。
6. transition selection 不读取 risk_on train evidence。
7. 两个 regime-specific union 可以选择同一 family，但必须有独立 selection rank。
8. density gate 使用 full denominator。
9. density prefilter 与 density drag 两套字段同时存在，且各自阈值不同。
10. bridge delta 使用同 split / same regime E1 baseline。
11. bridge gate 使用数值阈值：`bridge_recall_delta_vs_e1 >= -0.03` 且 `bridge_exclusion_rate_delta_vs_e1 <= 0.02`。
12. earlier / better-basis gate 引用与 bridge / label gate 相同的阈值，不得另设 "not worse" 标准。
13. `denominator_episodes < 30` 时，sample-small validation risk_on 只 diagnostic。
14. manifest 记录 row count / column schema。
15. 独立 report path 和 manifest path 存在。
16. source 08 manifest hash 不匹配时返回 `regime_specific_union_input_blocked`。
17. 缺失必需 source table 时 fail closed，不生成 supported decision。
18. `selection_regime` 只影响 selection，不在 event inclusion 阶段按 target episode 过滤 events。
19. event-regime-gated variant 只因自身 variant 定义过滤 `event_regime_bucket`，不得在 union 构建后额外过滤。
20. `candidate_family__all_variants`、`all_new_candidate_union`、原 `selected_candidate_union` 不能作为 selection unit。
21. 同一 family 多 variant 通过筛选时，只保留最高 rank variant，并给其他 variant 写入 `same_family_lower_ranked_variant`。
22. `regime_specific_union_selection_frontier.csv` 中 validation / robustness 字段必须标记为 post-selection read-only。
23. `family_density_share_full_union_events` 与 `family_density_share_headline_episode_regime_captures` 同时存在，headline gate 使用前者。
24. preflight summary、selection frontier、gate summary 均包含 `low_density_bridge_tension_flag`。
25. patch runner 不修改原 `outputs/manifests/run_manifest.json` 的 hash、mtime 或 content。

## 11. 推荐执行方式

推荐实现为独立入口，而不是修改原 full-run 默认路径：

```text
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python experiments/pending/08_risk_on_transition_recall_exploration_v0/src/run_risk_on_transition_recall_exploration.py --mode full
uv run python experiments/pending/08_risk_on_transition_recall_exploration_v0/src/run_regime_specific_union_patch.py --source-manifest experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/manifests/run_manifest.json
```

canonical CLI 只有 `run_regime_specific_union_patch.py`。不得要求实现者同时支持 `run_risk_on_transition_recall_exploration.py --mode regime-specific-unions`。默认 `--mode full` 必须保持原 08 行为。

## 12. 验收标准

验收时必须满足：

1. 原 08 report / manifest 仍可读取且 hash 未被 patch 自动覆盖。
2. 新 report 存在，并明确说明本 patch 是 regime-split diagnostic / ablation，不替代 P0 bridge-positive ranker / rejector 主线。
3. 新 manifest 中所有输出 artifact 都有 hash、row count、column schema。
4. preflight 两张表必须存在；若 preflight 返回 `regime_specific_union_preflight_no_material_split_benefit`，report 必须解释为什么 full patch 未继续。
5. 若 preflight 允许 full patch run，新 report 必须包含 risk_on / transition 两个独立 decision。
6. 如果两个 selected union 最终相同，报告必须说明这是独立 selection 的结果。
7. 如果任一 union 失败，必须明确失败 gate，而不是把 joint union 的 gate 结论复制过来。
8. `regime_specific_union_selected_variants.csv` 能证明每个 selected variant 的 `selection_regime`、rank、filter reason 和 source candidate scope。
9. `regime_specific_union_gate_summary.csv` 中 risk_on / transition 两行 decision 彼此独立，并包含 bridge / sample-small / density threshold 字段。
10. 原 08 source report / source manifest 的 content hash 在 patch 前后不变。
