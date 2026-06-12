# Experiment B：Regime x Event-Family Performance Matrix 报告

Final decision: `regime_family_matrix_source_caveated_complete`

## 一页结论

Experiment B 的结论不是“直接选择一个 entry union”，而是给 Experiment C / 后续 ranker 设计提供分 regime 的证据矩阵。当前顶层决策为 `regime_family_matrix_source_caveated_complete`，原因是 Experiment A 的最终状态为 `density_fast_fail_audit_partial_source_complete`，且 retention 只来自 `pre_replay_capture_only`。因此本报告所有 recall / bridge 结论只能解释为“pre-replay candidate generation 的覆盖能力”，不能解释为“经过 fast-fail / 质量过滤后仍能保留的交易信号”。

核心发现如下：

1. E1 不是 10d density 失败。`07_E1_only` 全样本事件数 6,820，mean density 1.88，p95 density 4.70，rolling 10d duplicate 只有 0.19%，10d fast-fail 14.52%。E1 的问题是覆盖不足，而不是事件过密。
2. 07 full union 不是更好的答案。相对 E1，它 all/all pre-replay any recall 只从 71.12% 增到 72.04%，bridge recall 从 32.56% 增到 34.75%，但事件数从 6,820 增到 15,161，rolling 10d duplicate 升到 29.60%，uniqueness p10 降到 0.727。收益很小，拥挤成本明显。
3. T4 / T7 不能作为 transition 默认假设。`08_selected_T4_T7_union` all/all recall 17.61%，bridge 5.09%，fast-fail 35.19%。transition train 也只有 23.03% / 8.55%，10d fast-fail 28.74%。它是 challenged incumbent / quality-filter candidate，不是 primary recall family。
4. R-family 的单族表现强，但 R-core union 有严重 cross-family collision。单个 R1/R2/R6/R7/R8 的 rolling 10d duplicate 都是 0.00%，但 `08_R_core_event_regime_gated` 事件数 47,914，rolling 10d duplicate 57.83%，uniqueness p10 0.364，p95 density 38.12。问题不是单个 R family 重复，而是 union 后同一 instrument 短周期内多 family 撞车。
5. Transition 方向上，R6 是当前最强的 primary candidate。train transition 中 R6 recall / bridge / fast-fail 为 96.05% / 49.34% / 20.86%；robustness transition 为 43.00% / 27.00% / 14.42%。相对 E1，R6 在 train transition 增加 33.88pp any recall 和 17.33pp bridge recall，但 fast-fail 也增加 3.71pp；在 robustness transition 增加 3.00pp any recall 和 3.00pp bridge recall，fast-fail 增加 6.78pp。因此 R6 应进入 Experiment C 的正向 ranker / de-overlap / quality-filter 设计，而不是直接变成 raw entry。

## 数据边界

本报告来自以下 publishable tables：

| artifact | row_count | 用途 |
|:--|--:|:--|
| `regime_family_performance_matrix.csv` | 186 | 主 cell 矩阵，包含 split x regime x scope 的 recall、fast-fail、density、sample status 和 role |
| `transition_event_family_reselection_matrix.csv` | 50 | transition 专用 reselection 结果 |
| `regime_family_density_fast_fail_matrix.csv` | 186 | density / uniqueness / fast-fail 诊断 |
| `regime_family_fast_fail_diagnostic_matrix.csv` | 186 | 聚合 fast-fail label 诊断，使用 `event_split` / `event_count` 命名 |
| `regime_family_cross_family_collision_matrix.csv` | 75 | R-family 与 R-core collision 对照 |
| `regime_family_compression_arm_hypothesis.csv` | 24 | R-series compression arm 假设，只能作为 aggregate hypothesis |

需要特别注意三个边界：

1. `events_per_instrument_year_mean`、`events_per_instrument_year_p95`、`rolling_10d_duplicate_rate` 全部来自 Experiment A 的 scope-level density summary。B 只按 scope id join 到 cell，`density_granularity = scope_level_only`，`density_cell_recomputed_flag = False`，没有做 split/regime density 重算。
2. `fast_fail_10d_*` 和 `false_repair_20d_*` 是诊断标签，不是 t0 entry feature。当前 186 个 fast-fail cell 中，137 个有 `failure_10_label / failure_10_path / direct_event_level_label / event_level_label_available`，49 个没有 event-level label source。
3. `post_replay_any_recall` 和 `post_replay_bridge_recall` 全为空。报告不能声称任何 family 经过 post-fast-fail replay 后仍然有效。

## Experiment A 对齐总览

| candidate_scope_id | event_n | pre_replay_any_recall | pre_replay_bridge_recall | mean_density | p95_density | rolling_10d_duplicate | uniqueness_p10 | fast_fail_10d | false_repair_20d |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `07_E1_only` | 6,820 | 71.12% | 32.56% | 1.88 | 4.70 | 0.19% | 1.000 | 14.52% | 20.62% |
| `07_full_union` | 15,161 | 72.04% | 34.75% | 4.19 | 10.85 | 29.60% | 0.727 | 16.33% | 23.13% |
| `08_selected_T4_T7_union` | 2,063 | 17.61% | 5.09% | 0.57 | 1.53 | 3.73% | 1.000 | 35.19% | 39.07% |
| `08_R_core_event_regime_gated` | 47,914 | NA | NA | 13.23 | 38.12 | 57.83% | 0.364 | 24.20% | 31.11% |
| `08_R1_event_regime_gated` | 14,363 | 85.28% | 33.84% | 3.97 | 10.87 | 0.00% | 1.000 | 26.61% | 33.49% |
| `08_R2_event_regime_gated` | 9,537 | 76.25% | 27.13% | 2.63 | 7.00 | 0.00% | 1.000 | 23.75% | 29.16% |
| `08_R6_event_regime_gated` | 16,204 | 88.25% | 38.99% | 4.47 | 12.23 | 0.00% | 1.000 | 23.19% | 30.30% |
| `08_R7_event_regime_gated` | 9,786 | 78.86% | 33.29% | 2.70 | 7.00 | 0.00% | 1.000 | 23.30% | 29.62% |
| `08_R8_event_regime_gated` | 12,896 | 74.85% | 28.04% | 3.56 | 9.88 | 0.00% | 1.000 | 26.33% | 33.70% |

解读：

1. E1 是低拥挤 baseline。它的 p95 density 为 4.70，rolling duplicate 仅 0.19%，fast-fail 14.52%。后续设计应把它作为 repair baseline，而不是因为它 recall 不够就认为它 density 失败。
2. 07 full union 相对 E1 的 recall 增量很小，但 density 和重复度代价很大。all/all any recall 只多 0.92pp，bridge 多 2.19pp，但事件数是 E1 的 2.22 倍，rolling duplicate 从 0.19% 升到 29.60%。
3. 单个 R family 的 recall 明显高于 E1，但 fast-fail 也明显更高。R6 all/all any recall 88.25%、bridge 38.99%，是最强单族之一；但 fast-fail 23.19%，比 E1 高 8.67pp。
4. R-core union 不能做 direct-entry support。它没有 capture scope，recall/bridge 为 NA，同时 rolling duplicate 57.83%，说明 raw union 会把单族优点转化为同 instrument 短期碰撞。

## Regime 结论

### Risk-off：E1 仍是最干净 baseline，R/T 的 fast-fail source 不完整

risk_off 下部分 R/T family 的 pre-replay recall 看起来很高，但对应 fast-fail cell 缺失，因此被标为 `source_blocked`，不能作为支持结论。可用的 E1 和 07 full union 数据显示，07 full union 的增益仍然不足以抵消额外复杂度。

| split | candidate_scope_id | any_recall | bridge_recall | fast_fail_10d | cell_status | role |
|:--|:--|--:|--:|--:|:--|:--|
| train | `07_E1_only` | 75.82% | 38.08% | 16.45% | sufficient | backbone_candidate |
| train | `07_full_union` | 76.74% | 40.92% | 17.89% | sufficient | density_or_fast_fail_blocked |
| train | `08_R6_event_regime_gated` | 90.93% | 41.63% | NA | sufficient | source_blocked |
| train | `08_R1_event_regime_gated` | 88.57% | 36.63% | NA | sufficient | source_blocked |
| robustness | `07_E1_only` | 80.92% | 33.61% | 10.73% | sufficient | backbone_candidate |
| robustness | `07_full_union` | 82.18% | 35.71% | 12.00% | sufficient | density_or_fast_fail_blocked |
| robustness | `08_R6_event_regime_gated` | 87.00% | 37.61% | NA | sufficient | source_blocked |

Insight：

1. risk_off 的设计应该先保留 E1，暂时不要用 R/T family 做 entry support。
2. 如果要研究 risk_off 的 R/T family，下一步不是直接 rank，而是补齐同口径 fast-fail source，否则 recall 高值无法评估代价。
3. 07 full union 的 bridge 增益在 train 为 +2.84pp，在 robustness 为 +2.10pp，但 fast-fail 同时增加约 1.3pp 到 1.4pp；这不是一个足够干净的替代方案。

### Risk-on：R-family 有强 recall，但必须先做 de-overlap / ranker

risk_on 下，R-family 明显强于 E1，尤其 R6。robustness split 中，R6 any recall 90.06%，bridge recall 56.91%，明显高于 E1 的 49.17% / 34.81%。但 R-family fast-fail 也高，且 R-core union collision 很严重，所以不能把 raw R union 当 entry。

| split | candidate_scope_id | any_recall | bridge_recall | fast_fail_10d | rolling_duplicate | role |
|:--|:--|--:|--:|--:|--:|:--|
| train | `08_R6_event_regime_gated` | 96.44% | 43.30% | 30.52% | 0.00% | collision_deoverlap_required |
| train | `08_R1_event_regime_gated` | 96.00% | 42.86% | 33.12% | 0.00% | collision_deoverlap_required |
| train | `08_R7_event_regime_gated` | 89.33% | 35.56% | 31.18% | 0.00% | collision_deoverlap_required |
| train | `07_E1_only` | 63.11% | 28.89% | 13.90% | 0.19% | backbone_candidate |
| train | `08_selected_T4_T7_union` | 21.78% | 6.22% | 40.31% | 3.73% | quality_filter_required |
| robustness | `08_R6_event_regime_gated` | 90.06% | 56.91% | 22.70% | 0.00% | collision_deoverlap_required |
| robustness | `08_R1_event_regime_gated` | 85.64% | 49.17% | 27.32% | 0.00% | collision_deoverlap_required |
| robustness | `08_R7_event_regime_gated` | 80.66% | 46.37% | 22.05% | 0.00% | collision_deoverlap_required |
| robustness | `07_E1_only` | 49.17% | 34.81% | 13.47% | 0.19% | backbone_candidate |

Insight：

1. risk_on 中 R6 是最稳定的正向候选。它在 train / robustness 都排在前列，且 bridge recall 很强。
2. 代价也很清楚。train 中 R6 相对 E1 提升 33.33pp any recall 和 14.41pp bridge recall，但 fast-fail 多 16.62pp。robustness 中 R6 提升 40.89pp any recall 和 22.10pp bridge recall，fast-fail 多 9.23pp。
3. 单族 R 的 rolling duplicate 是 0.00%，说明单族内部不是重复问题。问题出在 union。`08_R_core_event_regime_gated` all/all rolling duplicate 57.83%，risk_on r_core 也维持高碰撞，因此 Experiment C 应优先做 de-overlap、cooldown、top-k 或 positive ranker，而不是扩大 raw union。
4. T4/T7 在 risk_on 中不具备 recall 支撑。robustness union 只有 19.89% / 7.18%，fast-fail 36.12%；train union 21.78% / 6.22%，fast-fail 40.31%。它更像 rejector / quality-filter 研究对象，不是 recall backbone。

### Transition：R6 是当前 primary candidate，T4/T7 退为 challenged incumbent

transition 是本实验最重要的部分。结果显示，T4/T7 并不是 transition 的主 recall 来源。R6 在 train 和 robustness 都被选为 `transition_primary_candidate`。

| split | candidate_scope_id | transition_role | any_recall | bridge_recall | fast_fail_10d | false_repair_20d | cell_status |
|:--|:--|:--|--:|--:|--:|--:|:--|
| train | `08_R6_event_regime_gated` | transition_primary_candidate | 96.05% | 49.34% | 20.86% | 25.55% | sufficient |
| train | `08_R1_event_regime_gated` | transition_support_feature | 97.04% | 46.71% | 25.21% | 29.25% | sufficient |
| train | `08_R7_event_regime_gated` | transition_support_feature | 93.75% | 46.05% | 22.18% | 26.17% | sufficient |
| train | `07_E1_only` | transition_context_only | 62.17% | 32.01% | 17.15% | 21.00% | sufficient |
| train | `08_selected_T4_T7_union` | transition_quality_filter_candidate | 23.03% | 8.55% | 28.74% | 30.52% | sufficient |
| robustness | `08_R6_event_regime_gated` | transition_primary_candidate | 43.00% | 27.00% | 14.42% | 20.89% | sufficient |
| robustness | `08_R2_event_regime_gated` | transition_support_feature | 45.00% | 21.00% | 11.64% | 17.10% | sufficient |
| robustness | `08_R1_event_regime_gated` | transition_support_feature | 42.00% | 22.22% | 16.35% | 25.62% | sufficient |
| robustness | `07_E1_only` | transition_context_only | 40.00% | 24.00% | 7.63% | 13.49% | sufficient |
| robustness | `08_selected_T4_T7_union` | transition_quality_filter_candidate | 12.00% | 2.00% | 16.67% | 24.59% | sufficient |
| validation | `08_R6_event_regime_gated` | transition_support_feature | 95.06% | 37.04% | 20.17% | 28.79% | low_power_caution |
| validation | `07_E1_only` | transition_context_only | 70.37% | 30.86% | 14.03% | 21.39% | low_power_caution |
| validation | `08_selected_T4_T7_union` | transition_quality_filter_candidate | 8.64% | 3.70% | 25.48% | 29.94% | low_power_caution |

Insight：

1. R6 的优势来自 bridge，而不只是 any recall。train 中 R6 bridge 49.34%，比 E1 高 17.33pp；robustness 中 R6 bridge 27.00%，比 E1 高 3.00pp。
2. R6 的 fast-fail 成本不能忽略。train 中 R6 fast-fail 20.86%，比 E1 高 3.71pp；robustness 中 R6 14.42%，比 E1 高 6.78pp。因此它适合作为 positive ranker 的 candidate family，而不是原样 entry。
3. validation transition 全部是 `low_power_caution`，只能做方向验证，不能单独支持结论。它仍支持“R6 明显强于 T4/T7”的方向，但不应作为阈值设定依据。
4. T4/T7 的问题不是“太稀疏导致看不到”，而是 recall 和 bridge 都弱。它低 density，但没有换来更高质量。

## T4 / T7 个体与 union 诊断

T4/T7 的 individual readout 必须来自 Experiment A retention 表，不从 08 family recall 表 join。当前 individual scope 的 incremental recall 来源为 `not_available_publishable_source`，这不会 source-block cell，但要求我们不要把 incremental 当作支持证据。

| split | candidate_scope_id | any_recall | bridge_recall | incremental_source | fast_fail_10d | false_repair_20d | cell_status |
|:--|:--|--:|--:|:--|--:|--:|:--|
| train | `08_T4_gated` | 15.79% | 5.92% | not_available_publishable_source | 29.35% | 31.18% | sufficient |
| train | `08_T7_gated` | 8.22% | 2.63% | not_available_publishable_source | 27.69% | 29.23% | sufficient |
| train | `08_selected_T4_T7_union` | 23.03% | 8.55% | candidate_family_incremental_recall_over_e1 | 28.74% | 30.52% | sufficient |
| robustness | `08_T4_gated` | 3.00% | 1.00% | not_available_publishable_source | 16.36% | 23.21% | sufficient |
| robustness | `08_T7_gated` | 10.00% | 1.00% | not_available_publishable_source | 16.67% | 50.00% | sufficient |
| robustness | `08_selected_T4_T7_union` | 12.00% | 2.00% | candidate_family_incremental_recall_over_e1 | 16.67% | 24.59% | sufficient |
| validation | `08_T4_gated` | 8.64% | 3.70% | not_available_publishable_source | 25.48% | 29.94% | low_power_caution |
| validation | `08_T7_gated` | 1.23% | 1.23% | not_available_publishable_source | NA | NA | low_power_caution |
| validation | `08_selected_T4_T7_union` | 8.64% | 3.70% | candidate_family_incremental_recall_over_e1 | 25.48% | 29.94% | low_power_caution |

结论：T4/T7 最多保留为 transition quality filter 或 negative control。它不能继续作为 transition recall 的默认 event family。

## Density、fast-fail 与 uniqueness

| candidate_scope_id | mean_density | p95_density | rolling_duplicate | uniqueness_p10 | fast_fail_10d | false_repair_20d | 解释 |
|:--|--:|--:|--:|--:|--:|--:|:--|
| `07_E1_only` | 1.88 | 4.70 | 0.19% | 1.000 | 14.52% | 20.62% | 低拥挤 baseline |
| `07_full_union` | 4.19 | 10.85 | 29.60% | 0.727 | 16.33% | 23.13% | union 后重复明显 |
| `08_selected_T4_T7_union` | 0.57 | 1.53 | 3.73% | 1.000 | 35.19% | 39.07% | 低 density 但质量差 |
| `08_R_core_event_regime_gated` | 13.23 | 38.12 | 57.83% | 0.364 | 24.20% | 31.11% | cross-family collision stress scope |
| `08_R6_event_regime_gated` | 4.47 | 12.23 | 0.00% | 1.000 | 23.19% | 30.30% | 单族强 recall，但需要质量过滤 |

这里最重要的 insight 是：density 问题不在“每个 R family 自己太密”，而在“多个 R family 同时触发后形成同 instrument collision”。这直接决定 Experiment C 不应该只是简单调低 R-core 阈值，而应该在 family 之间做 de-overlap / top-k / cooldown / ranker。

## Sample 与 source guardrail

| split | regime | sufficient | low_power | diagnostic |
|:--|:--|--:|--:|--:|
| train | risk_off | 10 | 0 | 3 |
| train | risk_on | 10 | 0 | 4 |
| train | transition | 10 | 0 | 3 |
| robustness | risk_off | 10 | 0 | 2 |
| robustness | risk_on | 10 | 0 | 4 |
| robustness | transition | 10 | 0 | 3 |
| validation | risk_off | 10 | 0 | 3 |
| validation | risk_on | 0 | 0 | 14 |
| validation | transition | 0 | 10 | 3 |

解读：

1. train 和 robustness 是主要支持 split。多数核心 family 在这两个 split 有 sufficient readout。
2. validation risk_on 全部 diagnostic，不能作为支持或阈值来源。
3. validation transition 的核心 family 多为 low_power_caution，只能验证方向，不能单独驱动选择。
4. risk_off 中 R/T fast-fail source 不完整，因此即使 recall 高，也必须 source-block。

## R-core collision 分解

R1/R2/R6/R7/R8 单族都有 0.00% rolling duplicate，但 R-core union 的 all/all duplicate 达到 57.83%，uniqueness p10 只有 0.364。这说明 collision 是跨 family 的组合问题。

| scope | event_n | rolling_duplicate | uniqueness_p10 | fast_fail_10d |
|:--|--:|--:|--:|--:|
| `08_R1_event_regime_gated` | 14,363 | 0.00% | 1.000 | 26.61% |
| `08_R2_event_regime_gated` | 9,537 | 0.00% | 1.000 | 23.75% |
| `08_R6_event_regime_gated` | 16,204 | 0.00% | 1.000 | 23.19% |
| `08_R7_event_regime_gated` | 9,786 | 0.00% | 1.000 | 23.30% |
| `08_R8_event_regime_gated` | 12,896 | 0.00% | 1.000 | 26.33% |
| `08_R_core_event_regime_gated` | 47,914 | 57.83% | 0.364 | 24.20% |

设计含义：

1. 如果 Experiment C 做 direct union，会重现 R-core collision。
2. 如果 Experiment C 做 per-instrument day top-k 或 cooldown，可能保留 R6/R1/R7 的高 recall，同时降低 duplicate。
3. R2 在 transition robustness 的 fast-fail 较低，但 bridge 不如 R6；它更像 support feature 或备选 score component。

## Compression arms 只能作为 hypothesis

R-series compression frontier 当前没有可发布的 selected-event membership，因此只能作为 aggregate hypothesis。不能把这些 arms 直接放进 family role classification。

| compression_arm_id | canonical_events | density_vs_e1 | density_full | p95_density | train_risk_on_incremental | robustness_risk_on_incremental | gate_status | failure_reason |
|:--|--:|--:|--:|--:|--:|--:|:--|:--|
| `consensus_family_count__min3` | 3,094 | 0.45 | 0.85 | 2.00 | 12.89% | 12.15% | train_blocked | train_bridge;family_share_65 |
| `market_day_top_percentile__top5pct` | 8,734 | 1.28 | 2.41 | 5.00 | 23.56% | 24.86% | train_blocked | train_bridge;density;p95;family_share_65 |
| `single_family_best_variant__R2_near_high_volume_expansion` | 9,537 | 1.40 | 2.63 | 4.00 | 32.89% | 28.73% | train_blocked | train_bridge;density;family_share_65 |
| `single_family_best_variant__R7_cross_sectional_momentum_rank_jump` | 9,786 | 1.43 | 2.70 | 4.00 | 29.33% | 38.12% | train_blocked | density;family_share_65 |

这里的 insight 是：compression 确实能降低 density，但目前 gate failure 和缺 membership 让它不能成为可执行方案。它更适合给 Experiment C 定义候选 ranker arms，而不是在 B 中直接支持某个 family。

## 对 Experiment C 的建议

1. 以 R6 为 transition primary candidate 起点。R6 在 train / robustness 的 transition readout 同时具备 recall 和 bridge 优势，是最值得做 positive ranker 的 family。
2. 不做 raw R-core union。必须先做 de-overlap / cooldown / top-k / ranker，否则会继承 57.83% rolling duplicate 的 collision 问题。
3. 将 fast-fail 10d 和 false-repair 20d 作为 rejector / quality-filter 的监督标签，不得作为 t0 entry feature。
4. T4/T7 暂时只作为 challenged incumbent、quality filter 或 negative control。只有当新的质量过滤能显著降低其 fast-fail，同时提高 bridge recall，才有资格重新进入 transition candidate pool。
5. risk_off 先保持 E1 baseline。R/T 在 risk_off 的 fast-fail source 需要补齐后，才可以重新讨论是否成为 support feature。
6. validation transition 与 validation risk_on 的小样本状态必须保留。阈值选择应依赖 train + robustness，一切 validation 数值只用于方向性 sanity check。

## 产物契约检查

| check | status |
|:--|:--|
| final decision | `regime_family_matrix_source_caveated_complete` |
| performance matrix required metric columns | complete |
| density granularity | `scope_level_only` for all 186 cells |
| density recomputation | `density_cell_recomputed_flag = False` for all cells |
| aggregate fast-fail schema | uses `event_split` / `event_count`; no boolean diagnostic label columns |
| post-replay retention | all null |
| T4/T7 recall source | `candidate_10d_retention_by_split_regime.csv` |
| T4/T7 incremental source | `not_available_publishable_source` for individual gated scopes |
| compression arms | `aggregate_frontier_only_no_event_membership`, hypothesis only |
