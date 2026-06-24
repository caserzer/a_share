# 13G Event Survival Opportunity and Defense Overlay Diagnostic Report

## 裁决

单行裁决：`decision_state = 13G_stop_label_panel_only_no_overlay_utility`；`overlay_capacity_readout = label_panel_only_no_overlay_utility`；`primary_failure_reason = overlay_utility_gate_failed`。

13G 只评估 `repair_range_participation_core_30` 这个 event 在固定 event-level denominator 上的 survival / opportunity 路径，以及一个低自由度 rule-based defense / participation overlay。结果不授权 sequence mining、meta-labeling、bet sizing 或 entry policy：`sequence_mining_authorized = False`，`meta_labeling_authorized = False`，`bet_sizing_authorized = False`，`confirmatory_status = False`。

核心结论：event 本身确实携带机会信息，但当前规则 overlay 不是可用的风险预算调节器。它能避开大量 bad-side，但同时几乎把 winner opportunity 一起砍掉；在 50bps 主成本口径下，train 和 robustness 的 per-event utility 明确变差，validation 的小幅改善不能覆盖跨 split 不稳定性。

## 数据完整性与分母

13G 的 denominator 是 event-level，不是 winner episode-level。所有 27 个 label endpoint、overlay actions、skip/reduce events 都共享同一 analysis denominator。

| split_bucket   |   raw_event_n |   analysis_event_n |   analysis_event_fraction |   entry_not_executable_n |   entry_price_missing_n |   max_horizon_path_incomplete_n |   split_lineage_missing_n |   qfq_bar_mapping_missing_n | 13f_row_level_used   |
|:---------------|--------------:|-------------------:|--------------------------:|-------------------------:|------------------------:|--------------------------------:|--------------------------:|----------------------------:|:---------------------|
| train          |          6232 |               6232 |                       100 |                        0 |                       0 |                               0 |                         0 |                           0 | False                |
| validation     |          2627 |               2627 |                       100 |                        0 |                       0 |                               0 |                         0 |                           0 | False                |
| robustness     |          4813 |               4813 |                       100 |                        0 |                       0 |                               0 |                         0 |                           0 | False                |

Lineage / manifest audit：

| audit_family             |   check_n |   fail_n |
|:-------------------------|----------:|---------:|
| upstream_lineage_audit   |        26 |        0 |
| 13C_manifest_schema_hash |         6 |        0 |

13C manifest schema/hash 校验已通过；13F 只作为 delayed-entry negative lineage，`13f_row_level_used = False`。本次没有 not-evaluable rows，因此 13G 的负面结论不是 coverage failure，也不是 max-horizon cohort 不完整导致的假阴性。

## Primary Endpoint 路径读数

主端点固定为 `up_0p3_before_down_m0p15_H60`，即 event 后 60 sessions 内 `+30% MFE` 是否先于 `-15% MAE` 发生。

| split_bucket   |   analysis_event_n |   upper_hit_rate |   lower_hit_rate |   winner_before_fail_rate |   fail_before_winner_rate |   survive_without_fail_rate |   opportunity_without_fail_rate |   same_bar_ambiguous_rate |   upper_first_minus_lower_first_winner_rate_delta |   median_time_to_upper |   median_time_to_lower |   mfe_return_mean |   mae_return_mean |
|:---------------|-------------------:|-----------------:|-----------------:|--------------------------:|--------------------------:|----------------------------:|--------------------------------:|--------------------------:|--------------------------------------------------:|-----------------------:|-----------------------:|------------------:|------------------:|
| train          |               6232 |            19.38 |            29.8  |                     18.82 |                     29.48 |                       70.2  |                           18.82 |                         0 |                                                 0 |                   26   |                     29 |             18.28 |            -11.29 |
| validation     |               2627 |            10.13 |            24.02 |                     10.01 |                     23.98 |                       75.98 |                           10.01 |                         0 |                                                 0 |                   35.5 |                     42 |             14.34 |            -10.24 |
| robustness     |               4813 |            14.25 |            11.84 |                     14.25 |                     11.84 |                       88.16 |                           14.25 |                         0 |                                                 0 |                   35   |                     36 |             15.79 |             -7.65 |

读数解释：

- train 的 winner-before-fail rate 是 18.82%，但 fail-before-winner rate 是 29.48%，坏侧更厚。
- validation 的 winner-before-fail rate 降到 10.01%，fail-before-winner rate 仍有 23.98%。这是“有 lift 但 entry edge 不成立”的典型形态：event 有机会尾部，但机会概率不足以覆盖坏侧路径。
- robustness 的 winner-before-fail rate 回升到 14.25%，fail-before-winner rate 降到 11.84%，说明 event 不是纯噪声；但它仍没有自动转化为可交易 entry，因为 overlay 后 utility 在 robustness 变差。
- same-bar ambiguity 为 0，upper-first sensitivity delta 为 0，本次结论不依赖 same-bar 优先级。

## Opportunity Sensitivity

### 固定 60d / -15% fail barrier，改变上行目标

| split_bucket   |   up_threshold |   analysis_event_n |   winner_before_fail_rate |   fail_before_winner_rate |   survive_without_fail_rate |
|:---------------|---------------:|-------------------:|--------------------------:|--------------------------:|----------------------------:|
| train          |            0.2 |               6232 |                     32.37 |                     28.87 |                       70.2  |
| train          |            0.3 |               6232 |                     18.82 |                     29.48 |                       70.2  |
| train          |            0.5 |               6232 |                      5.44 |                     29.7  |                       70.2  |
| validation     |            0.2 |               2627 |                     18.31 |                     23.64 |                       75.98 |
| validation     |            0.3 |               2627 |                     10.01 |                     23.98 |                       75.98 |
| validation     |            0.5 |               2627 |                      4.23 |                     24.02 |                       75.98 |
| robustness     |            0.2 |               4813 |                     26.91 |                     11.78 |                       88.16 |
| robustness     |            0.3 |               4813 |                     14.25 |                     11.84 |                       88.16 |
| robustness     |            0.5 |               4813 |                      4.45 |                     11.84 |                       88.16 |

Insight：+20% endpoint 的机会概率明显更高，validation 为 18.31%，robustness 为 26.91%；但 +20% 更像“反弹/参与机会”，不是 big winner。+50% endpoint 在 60d 内过稀，validation 只有 4.23%，robustness 4.45%，不足以支撑 winner-entry 训练。+30% 是折中端点，但 validation 只有 10.01%，仍不够作为独立 entry edge。

### 固定 +30% / -15%，改变 horizon

| split_bucket   |   horizon_sessions |   winner_before_fail_rate |   fail_before_winner_rate |   survive_without_fail_rate |
|:---------------|-------------------:|--------------------------:|--------------------------:|----------------------------:|
| train          |                 20 |                      7.45 |                      9.6  |                       90.4  |
| train          |                 60 |                     18.82 |                     29.48 |                       70.2  |
| train          |                120 |                     24.7  |                     45.8  |                       52.82 |
| validation     |                 20 |                      2.59 |                      3.39 |                       96.61 |
| validation     |                 60 |                     10.01 |                     23.98 |                       75.98 |
| validation     |                120 |                     14.47 |                     38.6  |                       61.06 |
| robustness     |                 20 |                      2.76 |                      2.6  |                       97.4  |
| robustness     |                 60 |                     14.25 |                     11.84 |                       88.16 |
| robustness     |                120 |                     27.32 |                     24.37 |                       75.36 |

Insight：20d 太早，机会尚未充分展开；120d 会提高 winner-before-fail，但 train / validation 的 fail-before-winner 也急剧上升。以 validation 为例，+30/-15 从 60d 延到 120d，winner rate 从 10.01% 升到 14.47%，但 fail rate 从 23.98% 升到 38.60%。这说明问题不是简单“等久一点”，而是坏侧成本随 horizon 同步累积。

### 主端点 time-to-hit

| split_bucket   | touch_side   |   touch_n |   median_time_to_hit |   p25_time_to_hit |   p75_time_to_hit |
|:---------------|:-------------|----------:|---------------------:|------------------:|------------------:|
| robustness     | upper        |       686 |                 35   |                23 |                48 |
| robustness     | lower        |       570 |                 36   |                24 |                45 |
| train          | upper        |      1208 |                 26   |                14 |                39 |
| train          | lower        |      1857 |                 29   |                17 |                45 |
| validation     | upper        |       266 |                 35.5 |                20 |                46 |
| validation     | lower        |       631 |                 42   |                27 |                51 |

主端点中，上行触发的 median time-to-hit 在 validation / robustness 约 35 sessions，lower hit median 在 validation 42 sessions、robustness 36 sessions。机会和坏侧在时间上并没有形成稳定、可轻易提前分离的窗口。

## Rule Overlay 规则与动作分布

规则特征全部来自 t0 context 或 t0-known crowding，不使用未来 MFE/MAE/time-to-hit，也不使用 ex-post duplicate episode 作为 rule input。

| rule_feature_id                              | source_column                        |   threshold_q33 |   threshold_q66_or_p80 | threshold_source                          |   rule_feature_missing_fraction | rule_freeze_gate_status   |
|:---------------------------------------------|:-------------------------------------|----------------:|-----------------------:|:------------------------------------------|--------------------------------:|:--------------------------|
| t0_ret_20d_bucket                            | ret_20d                              |       0.0454342 |              0.0780018 | 13C_column_train_frozen                   |                               0 | pass                      |
| t0_max_drawdown_20d_bucket                   | max_drawdown_20d                     |      -0.0420792 |             -0.0273349 | 13C_column_train_frozen                   |                               0 | pass                      |
| t0_distance_to_20d_low_bucket                | distance_from_20d_low                |       0.0779661 |              0.104478  | 13C_column_train_frozen                   |                               0 | pass                      |
| t0_volatility_20d_bucket                     | volatility_20d                       |       0.0124732 |              0.0145214 | 13C_column_train_frozen                   |                               0 | pass                      |
| t0_liquidity_or_turnover_bucket              | turnover_zscore_20d                  |       1.1097    |              1.9989    | 13C_liquidity_or_turnover_train_frozen    |                               0 | pass                      |
| t0_prior_selected_event_count_20d_bucket     | t0_prior_selected_event_count_20d    |       1         |              4         | train_frozen_p80                          |                               0 | pass                      |
| t0_active_selected_event_count_120d_bucket   | t0_active_selected_event_count_120d  |       2         |              7         | train_frozen_p80                          |                               0 | pass                      |
| t0_market_selected_event_count_today_bucket  | t0_market_selected_event_count_today |      17         |             59         | train_frozen_p80                          |                               0 | pass                      |
| t0_compression_repair_feature_cluster_status | 13C_feature_cluster_dictionary       |     nan         |            nan         | neutral_fallback_no_non_outcome_direction |                               0 | pass                      |

动作分布：

| split_bucket   | action   |   event_n |   action_n |   action_fraction_pct |   ex_post_duplicate_action_n |   t0_known_crowded_action_n |
|:---------------|:---------|----------:|-----------:|----------------------:|-----------------------------:|----------------------------:|
| train          | increase |      6232 |        750 |                 12.03 |                          625 |                           0 |
| train          | keep     |      6232 |          0 |                  0    |                            0 |                           0 |
| train          | reduce   |      6232 |       2986 |                 47.91 |                         2708 |                        2082 |
| train          | skip     |      6232 |       2496 |                 40.05 |                         1971 |                         935 |
| validation     | increase |      2627 |        357 |                 13.59 |                          295 |                           0 |
| validation     | keep     |      2627 |          0 |                  0    |                            0 |                           0 |
| validation     | reduce   |      2627 |       1465 |                 55.77 |                         1314 |                        1119 |
| validation     | skip     |      2627 |        805 |                 30.64 |                          571 |                         251 |
| robustness     | increase |      4813 |        677 |                 14.07 |                          578 |                           0 |
| robustness     | keep     |      4813 |          0 |                  0    |                            0 |                           0 |
| robustness     | reduce   |      4813 |       2457 |                 51.05 |                         2289 |                        1746 |
| robustness     | skip     |      4813 |       1679 |                 34.88 |                         1330 |                         507 |

Insight：当前 rule family 明显偏防守。validation 中 reduce + skip 合计 86.41%，robustness 中 reduce + skip 合计 85.93%；keep 为 0。这种规则不会是“选择性加减仓”，而是近似系统性降风险。它能降低坏侧暴露，但容易把本来稀疏的 winner opportunity 一起过滤掉。

## Overlay Utility 与 Winner Retention

主经济 gate 使用 50bps，0bps / 100bps 为成本敏感性。

| split_bucket   |   analysis_event_n |   overlay_exposure_mean |   baseline_utility_per_event_mean_0bps |   overlay_utility_per_event_mean_0bps |   delta_overlay_vs_baseline_0bps |   baseline_utility_per_event_mean_50bps |   overlay_utility_per_event_mean_50bps |   delta_overlay_vs_baseline_50bps |   baseline_utility_per_event_mean_100bps |   overlay_utility_per_event_mean_100bps |   delta_overlay_vs_baseline_100bps |   baseline_exposure_day_return_50bps |   overlay_exposure_day_return_50bps |
|:---------------|-------------------:|------------------------:|---------------------------------------:|--------------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------------:|----------------------------------:|-----------------------------------------:|----------------------------------------:|-----------------------------------:|-------------------------------------:|------------------------------------:|
| train          |               6232 |                0.42009  |                               0.0086   |                             -0.000774 |                        -0.009374 |                                0.0036   |                              -0.006375 |                         -0.009976 |                                -0.0014   |                               -0.011977 |                          -0.010577 |                             7.9e-05  |                           -0.000338 |
| validation     |               2627 |                0.48268  |                              -0.006408 |                             -0.002219 |                         0.004189 |                               -0.011408 |                              -0.007899 |                          0.003509 |                                -0.016408 |                               -0.013578 |                           0.00283  |                            -0.000219 |                           -0.000312 |
| robustness     |               4813 |                0.466237 |                               0.034414 |                              0.014598 |                        -0.019817 |                                0.029414 |                               0.008894 |                         -0.02052  |                                 0.024414 |                                0.003191 |                          -0.021223 |                             0.00055  |                            0.000355 |

Winner / badside retention audit：

| split_bucket   |   winner_before_fail_n |   winner_retained_n |   winner_opportunity_retained_rate |   fail_before_winner_n |   badside_avoided_n |   badside_avoided_rate | badside_support_caveat   | winner_retention_support_caveat   |
|:---------------|-----------------------:|--------------------:|-----------------------------------:|-----------------------:|--------------------:|-----------------------:|:-------------------------|:----------------------------------|
| train          |                   1173 |                 122 |                              10.4  |                   1837 |                1622 |                  88.3  | False                    | False                             |
| validation     |                    263 |                  29 |                              11.03 |                    630 |                 540 |                  85.71 | False                    | False                             |
| robustness     |                    686 |                  81 |                              11.81 |                    570 |                 477 |                  83.68 | False                    | False                             |

关键发现：

- overlay 在 validation 的 50bps delta 为 0.003509，看似改善，但 train 为 -0.009976，robustness 为 -0.020520，主经济 gate 失败。
- badside avoided 很高：train 88.30%，validation 85.71%，robustness 83.68%。这说明 event 后的 bad-side context 是可识别的。
- 但 winner retained 极低：train 10.40%，validation 11.03%，robustness 11.81%。这不是可接受的 participation overlay，因为它主要通过牺牲 winner opportunity 来规避 bad-side。
- 在 0bps 下 train 和 robustness 也变差；在 100bps 下同样没有翻转。这排除了“只是交易成本太保守”的解释。

## Uniqueness / Density

| split_bucket   |   event_n |   average_uniqueness |   median_uniqueness |   p90_concurrency |   event_density_per_instrument_year |   rolling_20d_event_count_p95 |   duplicate_episode_event_count |   duplicate_episode_fraction_pct |
|:---------------|----------:|---------------------:|--------------------:|------------------:|------------------------------------:|------------------------------:|--------------------------------:|---------------------------------:|
| train          |      6232 |                0.236 |               0.17  |             10.79 |                               2.965 |                             7 |                            5304 |                            85.11 |
| validation     |      2627 |                0.257 |               0.176 |             10.9  |                               3.567 |                             7 |                            2180 |                            82.98 |
| robustness     |      4813 |                0.22  |               0.158 |             12.03 |                               6.085 |                             7 |                            4197 |                            87.2  |

Insight：event density 和 overlap 是重要风险。average uniqueness 只有 0.220-0.257，p90 concurrency 约 10.8-12.0，duplicate episode fraction 高达 82.98%-87.20%。这意味着这些 event 经常在同一标的的 120d path 内重叠，utility 很容易被重复事件吞掉。当前 `duplicate_delta_share = 0` 是因为 overlay 总体没有正改善，不代表 density 风险不存在；它只是说明“没有可归因的正 utility 可以被 density artifact 解释”。

## Findings

1. **Event 有机会信息，但不是 winner entry edge。** 主端点 validation winner-before-fail 只有 10.01%，低于 fail-before-winner 的 23.98%。robustness 好一些，但跨 split 不稳定。
2. **机会标签应拆分为 survival / opportunity / bad-side，而不是继续训练 big_winner_120d。** +20%/60d 显示更强 opportunity，但 +50% 太稀疏；+30% 仍不足以直接作为 entry。
3. **当前 rule overlay 过度防守。** 它能避开 83.68%-88.30% 的 fail-before-winner，但只保留 10.40%-11.81% 的 winner-before-fail，经济上不可接受。
4. **坏侧识别比机会保留更容易。** 这支持把 event 作为 defense context 继续研究，但不支持立即做高自由度 meta-labeling。
5. **密度/重复事件是 utility 损耗核心之一。** 高 duplicate episode fraction 表明 denominator 中存在大量重叠机会，后续必须做 event de-dup / cooldown / capital occupancy 约束，否则 lift 会被重复暴露稀释。

## Research Insight

13G 的实质结论不是“event 没用”，而是“event 不适合直接决定买入，也不适合当前规则直接调仓”。更准确的定位是：event 是一个 opportunity / survival carrier，可以告诉我们某些状态下未来存在上行路径；但要变成风险预算调节器，必须先解决 winner retention，而不是只最大化 badside avoided。

下一步如果继续，不应马上进入自由度高的 meta-labeling。更稳妥的方向是低自由度修正：

- 先做 event de-dup / cooldown，降低同一标的 120d overlap 对 utility 的吞噬。
- 把 defense overlay 拆成两层：第一层只识别 fast-fail / severe bad-side；第二层必须加 winner-retention floor，不允许通过牺牲 80% 以上 winner 来换取坏侧规避。
- 将 +20% opportunity、+30% opportunity、-15% fail、survive-without-fail 分开评估，不再让单一 big_winner label 承担所有目标。
- 只有当低自由度 rule overlay 在 validation 和 robustness 同时改善 after-cost utility，并且 winner retained 达到门槛，才值得另开 confirmatory requirement。当前 13G 不满足这个条件。

## Boundary

本报告不得解释为 alpha discovered、deployable strategy、confirmed edge、meta-labeling ready、bet sizing ready 或 position sizing validated。13G 的正确用途是约束后续研究方向：优先修复 opportunity retention 与 density/cooldown 问题，而不是扩大模型自由度。
