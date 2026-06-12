# Experiment C：Risk-on / Transition R-series Bridge-Positive Ranker 报告

最终决策：`risk_on_r_series_ranker_source_caveated_complete`

## 一页结论

本实验验证了一个更具体的问题：在 Experiment B 确认 R-family 尤其 R6 有较强 pre-replay bridge-positive 覆盖后，能否用 train-only 的 ranker、budget、cooldown、de-overlap 规则把 R-series 事件压缩成可直接入场的候选，或者至少成为 meta-label / rejector 的 feature source。当前结果是否定的：所有 `risk_on` 与 `transition` arm 都停留在 `diagnostic_only_or_no_candidate`，`risk_off` 只作为 diagnostic-only 输出。

- 评估 arm/regime 行数：`63`，其中 `risk_on` 21、`transition` 21、`risk_off` 21。
- direct-entry pass：`0`；feature-source pass：`0`。
- selected event rows：`452,074`，去重 canonical event：`49,219`；rejected event rows：`493,038`，去重 canonical event：`46,920`。
- 结论不是 “R-series 没有 bridge signal”，而是 “bridge signal 与 density、duplicate、fast-fail、false-repair、family concentration 不能同时满足 gate”。
- 所有 recall / bridge 结论都是 `pre_replay_capture_only`，不能解释为 post-filter trading signal retention。

## 核心发现与洞察

### Finding 1：Risk-on 的 bridge 覆盖存在，但质量成本太高

Risk-on 中 R-core stress pool 的 train bridge delta 为 +13.78pp、robustness bridge delta 为 +19.34pp，说明 R-family 对 risk-on bridge-positive episode 的覆盖确实强。但同一组事件的 density/E1 达 4.515，p95 density 达 23.548，rolling 10d duplicate 达 54.43%，fast-fail excess 达 +12.86pp。这组数值说明原始 R-core 更像 “召回压力池”，不是可直接执行的事件族。

压缩后最接近 feature-source 的 risk-on 形态是 `top_k_per_instrument_month_family_aware`：density/E1 降到 2.351，p95 为 11.961，duplicate 降到 11.05%，bridge delta 仍有 train +11.29pp / robustness +13.26pp。但它仍被 fast-fail 与 false-repair 卡住：fast-fail excess +15.28pp，false-repair excess +15.74pp。因此 risk-on 的下一步不是再放宽 density，而是先做成本标签或 replay 过滤。

### Finding 2：Transition 的核心问题不是密度，而是 bridge robustness 不成立

Transition 中 R-core stress pool 的 train bridge delta 只有 +1.98pp，robustness bridge delta 为 -5.82pp。这说明 transition 的 R-family 信号在 train 上没有形成足够强的增量，在 robustness 上还低于 E1。压缩 arm 虽然可以把 density/E1 压到 1.30 到 1.57 区间，例如 `top_k_per_instrument_month_family_aware` 的 density/E1 为 1.570、duplicate 为 9.90%，但 robustness bridge delta 仍为 -7.84pp。因此 transition 不应继续把问题定义成 “R-series 排序压缩”，而应回到 event-family / regime definition 的选择问题。

### Finding 3：R6 单体干净，但不足以作为 entry backbone

R6 单体的好处是 duplicate 为 0，risk-on density/E1 只有 1.358、p95 为 6.698。但 risk-on R6-only 的 train bridge delta 只有 +3.70pp，低于 direct-entry 所需 +5pp，同时 single-family share 为 100.00%，fast-fail excess 为 +12.38pp。Transition R6-only 更弱，train bridge delta 为 -4.86pp、robustness bridge delta 为 -10.00pp。R6 可以作为重要特征或候选机制，但不能单独升级为 entry candidate。

### Finding 4：OOS 读数显示 rank score 能解释部分 bridge，但不能解释质量成本

OOS 表中，risk-on 的 `bridge_positive_vs_bridge_negative` 有 18/42 rows 为 positive，`e1_missed_captured_vs_still_missed` 有 15/42 rows 为 positive；transition 的 bridge-positive 有 23/42 rows 为 positive，但 E1-missed capture 只有 3/42 rows 为 positive。与此同时，`non_fast_fail_vs_fast_fail_10d`、`non_false_repair_vs_false_repair_20d`、`winner_120d` 在 risk-on/transition/risk-off 全部是 not_positive_or_low_power。洞察是：当前 rank score 有时能把 bridge-positive 往前排，但不能把 “低 fast-fail / 低 false-repair / 高 winner quality” 排出来。

### Finding 5：T4/T7 继续只是 negative control / quality filter，不是 transition recall backbone

T4/T7 union 的 transition train any recall 只有 23.03%、bridge recall 8.55%、fast-fail 28.74%；robustness any recall 12.00%、bridge recall 2.00%。它确实稀疏，但稀疏不等于高质量召回。这个结果支持 Experiment B 的判断：T4/T7 不应被拿来修 transition recall，只能作为负控或上下文质量过滤。

## 决策概览

| regime | tier | arms |
| --- | --- | --- |
| risk_off | risk_off_diagnostic_only | 21 |
| risk_on | diagnostic_only_or_no_candidate | 21 |
| transition | diagnostic_only_or_no_candidate | 21 |

| regime | direct pass | feature-source pass |
| --- | --- | --- |
| risk_off | 0 | 0 |
| risk_on | 0 | 0 |
| transition | 0 | 0 |

## 上游 source caveat 与标签边界

| source | decision/status | affects entry | affects feature-source | required caveat |
| --- | --- | --- | --- | --- |
| density_fast_fail_audit_manifest.json | density_fast_fail_audit_partial_source_complete / partial_source_complete | True | True | pre_replay_capture_only;no_post_filter_retention_claim |
| regime_family_matrix_manifest.json | regime_family_matrix_source_caveated_complete / source_caveated | True | True | source_caveated_complete |
| risk_off_regime_family_readouts | diagnostic_only / risk_off_not_candidate_support | False | False | risk_off_rows_diagnostic_only |

标签使用边界如下。`failure_10_label`、`event_false_repair_20d_label`、`bridge_positive_event_or_episode_capture` 只能作为 label / readout，不允许进入 t0 feature matrix。

| field | feature? | label? | readout? | reason |
| --- | --- | --- | --- | --- |
| rank_score | True | False | True | t0_or_earlier_score_feature |
| family_id | True | False | True | categorical_t0_feature |
| market_regime_bucket | True | False | True | event_regime_available_at_t0 |
| failure_10_label | False | True | True | future_fast_fail_label_not_t0_feature |
| event_false_repair_20d_label | False | True | True | future_false_repair_label_not_t0_feature |
| bridge_positive_event_or_episode_capture | False | True | True | pre_replay_label_not_t0_feature |
| event_big_winner_120d_label | False | True | True | secondary_downstream_label |

## Experiment A 密度基准

| scope | events | mean density | p95 density | dup10d |
| --- | --- | --- | --- | --- |
| 07_E1_only | 6,820 | 1.883 | 4.704 | 0.19% |
| 08_selected_T4_T7_union | 2,063 | 0.570 | 1.527 | 3.73% |
| 08_R_core_event_regime_gated | 47,914 | 13.227 | 38.121 | 57.83% |
| 08_R6_event_regime_gated | 16,204 | 4.473 | 12.226 | 0.00% |

这个基准解释了为什么 C 的 gate 不是追求 E1 绝对等价，而是设置 1.50x direct-entry density budget 与 2.50x feature-source density budget。E1 足够干净，R6 单体不拥挤，但 R-core union 的 duplicate 与 p95 density 过高。

## Risk-on 关键 arm 明细

| arm | train bridge Δ | robust bridge Δ | density/E1 | p95 | dup10d | fast-fail Δ | false-repair Δ | family max share | blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_r_core_no_ranker_diagnostic | +13.78pp | +19.34pp | 4.515 | 23.548 | 54.43% | +12.86pp | +12.88pp | 28.29% | density;duplicate;false_repair;fast_fail;p95;sample_status |
| r6_r1_r2_r7_bridge_pool | +12.89pp | +18.23pp | 3.615 | 18.620 | 45.20% | +12.95pp | +12.55pp | 35.33% | density;duplicate;false_repair;fast_fail;oos_separability;p95 |
| top_k_per_instrument_month_family_aware | +11.29pp | +13.26pp | 2.351 | 11.961 | 11.05% | +15.28pp | +15.74pp | 54.01% | false_repair;fast_fail |
| cooldown_20d_ranked_within_bucket | +9.95pp | +9.39pp | 1.824 | 8.971 | 0.00% | +15.65pp | +16.18pp | 63.29% | false_repair;fast_fail |
| cooldown_40d_ranked_within_bucket | +5.93pp | +3.87pp | 1.374 | 6.728 | 0.00% | +14.45pp | +14.79pp | 71.22% | false_repair;fast_fail;oos_separability;selected_share |
| baseline_r6_only_risk_on_positive | +3.70pp | +6.08pp | 1.358 | 6.698 | 0.00% | +12.38pp | +12.85pp | 100.00% | false_repair;fast_fail;selected_share |
| r6_r2_low_fast_fail_support | +10.40pp | +12.71pp | 2.262 | 11.572 | 22.35% | +11.59pp | +11.13pp | 54.10% | duplicate;false_repair;fast_fail |

Risk-on 的主要 trade-off 很清楚：越保留 R-core 多族覆盖，bridge delta 越好，但 density、duplicate、fast-fail 同时升高；越用 cooldown/top-k 压缩，density 和 duplicate 改善，但 fast-fail / false-repair 仍明显高于 E1。`cooldown_20d` 把 duplicate 压到 0，但 fast-fail excess 仍为 +15.65pp，说明仅靠时间去重不能解决事件质量。

## Transition 关键 arm 明细

| arm | train bridge Δ | robust bridge Δ | density/E1 | p95 | dup10d | fast-fail Δ | false-repair Δ | family max share | blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_r_core_no_ranker_diagnostic | +1.98pp | -5.82pp | 2.511 | 13.135 | 43.50% | +5.92pp | +6.81pp | 33.00% | bridge;density;duplicate;false_repair;p95;sample_status |
| r6_r1_r2_r7_bridge_pool | +1.32pp | -5.82pp | 2.183 | 11.290 | 38.21% | +6.09pp | +7.14pp | 37.95% | bridge;duplicate;false_repair |
| top_k_per_instrument_month_family_aware | -1.55pp | -7.84pp | 1.570 | 7.810 | 9.90% | +7.04pp | +8.33pp | 52.56% | bridge;false_repair |
| cooldown_20d_ranked_within_bucket | -2.87pp | -7.84pp | 1.304 | 6.390 | 0.00% | +7.02pp | +8.22pp | 60.35% | bridge;false_repair |
| cooldown_40d_ranked_within_bucket | -5.85pp | -9.86pp | 1.104 | 5.325 | 0.00% | +6.47pp | +7.57pp | 64.02% | bridge;false_repair;recall |
| baseline_r6_only_transition_primary | -4.86pp | -10.00pp | 1.018 | 5.052 | 0.00% | +5.27pp | +6.16pp | 100.00% | bridge;false_repair;recall;selected_share |
| r6_r2_low_fast_fail_support | -3.21pp | -10.00pp | 1.298 | 6.457 | 13.44% | +5.70pp | +6.34pp | 72.27% | bridge;false_repair;recall;selected_share |

Transition 的主要 blocker 是 bridge / recall：即使 density 被压到 feature-source 许可区间，robustness bridge delta 仍为负。这里不应把失败归因于 “阈值太严”，因为最稠密和最稀疏的 arm 都没有形成稳定的 transition bridge 增量。

## Robustness Bridge Readout

| regime | arm | selected events | any recall | bridge recall | incremental recall | E1-missed captures | sample status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| risk_on | baseline_r_core_no_ranker_diagnostic | 9,730 | 87.29% | 54.14% | +43.09pp | 78 | diagnostic_only |
| risk_on | cross_family_collision_suppression | 9,731 | 87.29% | 54.14% | +43.09pp | 78 | sufficient_for_cell_readout |
| risk_on | r6_r1_r2_r7_bridge_pool | 7,924 | 86.74% | 53.04% | +43.09pp | 78 | sufficient_for_cell_readout |
| risk_on | r6_r1_r7_bridge_pool | 6,244 | 83.98% | 48.62% | +41.99pp | 76 | sufficient_for_cell_readout |
| risk_on | top_k_per_instrument_month_family_aware | 5,044 | 86.19% | 48.07% | +42.54pp | 77 | sufficient_for_cell_readout |
| risk_on | r6_r2_low_fast_fail_support | 5,017 | 79.56% | 47.51% | +39.78pp | 72 | sufficient_for_cell_readout |
| risk_on | cooldown_20d_ranked_within_bucket | 3,848 | 82.87% | 44.20% | +41.99pp | 76 | sufficient_for_cell_readout |
| risk_on | top_k_per_instrument_20d_family_aware | 3,848 | 82.87% | 44.20% | +41.99pp | 76 | sufficient_for_cell_readout |
| transition | baseline_r_core_no_ranker_diagnostic | 3,225 | 31.00% | 18.18% | +4.00pp | 4 | diagnostic_only |
| transition | r6_r1_r7_bridge_pool | 2,415 | 29.00% | 18.18% | +4.00pp | 4 | sufficient_for_cell_readout |
| transition | r6_r1_r2_r7_bridge_pool | 2,651 | 30.00% | 18.18% | +4.00pp | 4 | sufficient_for_cell_readout |
| transition | cross_family_collision_suppression | 3,225 | 31.00% | 18.18% | +4.00pp | 4 | sufficient_for_cell_readout |
| transition | cooldown_20d_ranked_within_bucket | 1,925 | 31.00% | 16.16% | +4.00pp | 4 | sufficient_for_cell_readout |
| transition | top_k_per_instrument_month_family_aware | 2,277 | 31.00% | 16.16% | +4.00pp | 4 | sufficient_for_cell_readout |
| transition | top_k_per_instrument_20d_family_aware | 1,925 | 31.00% | 16.16% | +4.00pp | 4 | sufficient_for_cell_readout |
| transition | cooldown_40d_ranked_within_bucket | 1,726 | 30.00% | 14.14% | +3.00pp | 3 | sufficient_for_cell_readout |

Risk-on robustness 的 top arms 仍能捕获 72 到 78 个 E1-missed cases，bridge recall 也能维持在 47% 到 54% 区间；transition robustness 只有 2 到 4 个 E1-missed captures，bridge recall 最高约 18.18%。这就是两个 regime 的本质差异：risk-on 是质量成本问题，transition 是 recall signal 本身不稳。

## OOS Separability Readout

| regime | label | status | rows |
| --- | --- | --- | --- |
| risk_off | bridge_positive_vs_bridge_negative | not_positive_or_low_power | 42 |
| risk_off | e1_missed_captured_vs_still_missed | not_positive_or_low_power | 42 |
| risk_off | non_false_repair_vs_false_repair_20d | not_positive_or_low_power | 42 |
| risk_off | non_fast_fail_vs_fast_fail_10d | not_positive_or_low_power | 42 |
| risk_off | winner_120d | not_positive_or_low_power | 42 |
| risk_on | bridge_positive_vs_bridge_negative | not_positive_or_low_power | 24 |
| risk_on | bridge_positive_vs_bridge_negative | positive | 18 |
| risk_on | e1_missed_captured_vs_still_missed | not_positive_or_low_power | 27 |
| risk_on | e1_missed_captured_vs_still_missed | positive | 15 |
| risk_on | non_false_repair_vs_false_repair_20d | not_positive_or_low_power | 42 |
| risk_on | non_fast_fail_vs_fast_fail_10d | not_positive_or_low_power | 42 |
| risk_on | winner_120d | not_positive_or_low_power | 42 |
| transition | bridge_positive_vs_bridge_negative | not_positive_or_low_power | 19 |
| transition | bridge_positive_vs_bridge_negative | positive | 23 |
| transition | e1_missed_captured_vs_still_missed | not_positive_or_low_power | 39 |
| transition | e1_missed_captured_vs_still_missed | positive | 3 |
| transition | non_false_repair_vs_false_repair_20d | not_positive_or_low_power | 42 |
| transition | non_fast_fail_vs_fast_fail_10d | not_positive_or_low_power | 42 |
| transition | winner_120d | not_positive_or_low_power | 42 |

OOS 结果支持 “不要直接入场” 的结论。Bridge-positive 的 separability 偶尔为正，但 fast-fail、false-repair、winner 的 separability 没有给出可依赖证据。若后续要做 meta-label，应先补 replay/post-filter 标签，并把成本标签作为 supervised rejector 的主目标，而不是继续优化 bridge score。

## Selected Event 贡献与 scope reconstruction

| regime | scope | selected rows | unique canonical events |
| --- | --- | --- | --- |
| risk_on | 08_R1_event_regime_gated | 77,481 | 8,712 |
| risk_on | 08_R2_event_regime_gated | 38,530 | 7,083 |
| risk_on | 08_R6_event_regime_gated | 73,687 | 9,260 |
| risk_on | 08_R7_event_regime_gated | 23,190 | 4,628 |
| risk_on | 08_R8_event_regime_gated | 17,863 | 7,390 |
| risk_on | 08_R_core_event_regime_gated | 30,790 | 30,790 |
| risk_on | 08_T4_gated | 1,064 | 1,064 |
| risk_on | 08_T7_gated | 558 | 558 |
| transition | 08_R1_event_regime_gated | 55,631 | 5,651 |
| transition | 08_R2_event_regime_gated | 15,308 | 2,454 |
| transition | 08_R6_event_regime_gated | 63,575 | 6,944 |
| transition | 08_R7_event_regime_gated | 25,518 | 3,649 |
| transition | 08_R8_event_regime_gated | 11,285 | 3,252 |
| transition | 08_R_core_event_regime_gated | 17,124 | 17,124 |
| transition | 08_T4_gated | 399 | 399 |
| transition | 08_T7_gated | 71 | 71 |

C 已经按 Experiment A 的 scope mapping contract 重建单体 scope。selected rows 会因为同一个 canonical event 被多个 arm 选中而重复，因此报告同时给出 selected rows 与 unique canonical events。R6 与 R1 是 risk-on/transition 中最大的贡献族，R2 虽然有语义价值，但 score availability 为 0，只能以 budget/cooldown 方式参与，不能被当作 scored ranker family。

| family | rank score availability |
| --- | --- |
| R2_near_high_volume_expansion | 0% |
| T4_entropy_compression_then_directional_expansion | 0% |
| T7_board_relative_strength_break | 0% |
| R1_relative_strength_breakout | 100% |
| R7_cross_sectional_momentum_rank_jump | 100% |
| R6_market_breadth_thrust | 100% |
| R8_persistent_distance_above_ema | 100% |

## T4/T7 Negative Control

| split | scope | role | any recall | bridge recall | fast-fail | false-repair |
| --- | --- | --- | --- | --- | --- | --- |
| robustness | 08_selected_T4_T7_union | transition_quality_filter_candidate | 12.00% | 2.00% | 16.67% | 24.59% |
| train | 08_selected_T4_T7_union | transition_quality_filter_candidate | 23.03% | 8.55% | 28.74% | 30.52% |
| validation | 08_selected_T4_T7_union | transition_quality_filter_candidate | 8.64% | 3.70% | 25.48% | 29.94% |

T4/T7 的低密度不能补偿低 recall 与高 fast-fail。它们适合保留为 negative control 或 quality/context filter，不适合作为 transition recall 主线。

## Blocker 分布

| regime | blocker combination | arms |
| --- | --- | --- |
| risk_off | risk_off_diagnostic_only | 21 |
| risk_on | bridge;duplicate;false_repair;fast_fail;recall | 5 |
| risk_on | false_repair;fast_fail | 3 |
| risk_on | bridge;duplicate;false_repair;fast_fail | 2 |
| risk_on | density;duplicate;false_repair;fast_fail;p95 | 2 |
| risk_on | false_repair;fast_fail;selected_share | 2 |
| risk_on | bridge;density;duplicate;false_repair;fast_fail;oos_separability;p95;recall;sample_status;selected_share;source | 1 |
| risk_on | bridge;false_repair;fast_fail;recall;sample_status;selected_share | 1 |
| risk_on | bridge;false_repair;fast_fail;recall;selected_share | 1 |
| risk_on | density;duplicate;false_repair;fast_fail;oos_separability;p95 | 1 |
| risk_on | density;duplicate;false_repair;fast_fail;p95;sample_status | 1 |
| risk_on | duplicate;false_repair;fast_fail | 1 |
| risk_on | false_repair;fast_fail;oos_separability;selected_share | 1 |
| transition | bridge;duplicate;false_repair;oos_separability;recall | 5 |
| transition | bridge;false_repair | 3 |
| transition | bridge;false_repair;recall;selected_share | 3 |
| transition | bridge;duplicate;false_repair | 2 |
| transition | bridge;duplicate;false_repair;recall | 2 |
| transition | bridge;density;duplicate;false_repair;fast_fail;oos_separability;p95;recall;sample_status;selected_share;source | 1 |
| transition | bridge;density;duplicate;false_repair;p95 | 1 |
| transition | bridge;density;duplicate;false_repair;p95;sample_status | 1 |
| transition | bridge;false_repair;fast_fail;oos_separability;recall;sample_status;selected_share | 1 |

Risk-on blocker 主要集中在 fast-fail / false-repair / duplicate / density 的组合；transition blocker 主要集中在 bridge / recall，再叠加 duplicate 和 false-repair。这个差异决定了后续路线：risk-on 需要 rejector/replay 过滤，transition 需要重新定义 event family 或 regime bridge 标签。

## 结论与下一步

1. 不建议把任何 R-series arm 推进为 direct-entry candidate。当前所有 arm 都没有通过 gate。
2. 不建议把当前 ranker 输出直接升级为 feature-source。即使部分 arm 有 bridge separability，fast-fail / false-repair / winner separability 不足。
3. Risk-on 可保留 `top_k_per_instrument_month_family_aware`、`cooldown_20d_ranked_within_bucket`、`r6_r2_low_fast_fail_support` 作为后续 replay/rejector 的诊断候选，但不能宣称可交易。
4. Transition 不应继续围绕 T4/T7 或 raw R-core 修补。更优先的是重新选择 transition event family，或重新定义 transition bridge-positive 标签的 source。
5. 下一阶段如果继续推进，应先实现 post-filter replay / event-to-episode retention source，再训练成本 rejector；否则 bridge recall 的表观改善会持续被 fast-fail 和 false-repair 抵消。

## Binding Drift Audit

No binding drift was detected against current A/B source tables.

## 输出清单

- `risk_on_r_series_ranker_arm_frontier.csv`: 63 rows
- `risk_on_r_series_ranker_bridge_recall_readout.csv`: 189 rows
- `risk_on_r_series_ranker_decision_tiers.csv`: 63 rows
- `risk_on_r_series_ranker_density_fast_fail_readout.csv`: 252 rows
- `risk_on_r_series_ranker_deoverlap_audit.csv`: 186,155 rows
- `risk_on_r_series_ranker_failure_distribution.csv`: 63 rows
- `risk_on_r_series_ranker_family_budget_audit.csv`: 154 rows
- `risk_on_r_series_ranker_feature_spec.csv`: 15 rows
- `risk_on_r_series_ranker_label_policy_audit.csv`: 7 rows
- `risk_on_r_series_ranker_oos_separability.csv`: 630 rows
- `risk_on_r_series_ranker_rejected_events.csv.gz`: 493,038 rows
- `risk_on_r_series_ranker_selected_events.csv.gz`: 452,074 rows
- `risk_on_r_series_ranker_source_caveat_audit.csv`: 3 rows
- `risk_on_r_series_ranker_transition_reselection_readout.csv`: 378 rows
