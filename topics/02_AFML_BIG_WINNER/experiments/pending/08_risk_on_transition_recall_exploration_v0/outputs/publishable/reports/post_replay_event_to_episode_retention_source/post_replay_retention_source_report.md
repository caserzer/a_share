# Experiment D - Post-Replay 事件到 Episode 留存源报告

最终决策：`post_replay_retention_source_source_caveated_complete`

## 摘要结论

Experiment D 的目标不是训练新模型，而是补齐 A/B/C 共同缺失的 post-replay event-to-episode retention source。当前运行已经把事件回放锚点与 06 episode 窗口重新连接，生成了本地 membership parquet，并把 scope 与 C arm 的 post-filter 留存读数发布出来。

- 本地 raw membership：`357,450` rows，hash `77979d5324d49a3522d8ad7a25aa67fa88639f7d49206de8c2e39d6f39e8b17e`。
- episode window：`4,986` rows；`episode_window_ready` = `4,986`；dedup conflict = `0`。
- scope retention：`990` rows；C arm retention：`1,890` rows；policy effect：`2,304` rows；reconciliation：`291` rows。
- 所有 `entry_support_allowed` 均为 `False`；oracle future-label policy 只允许 audit，不允许作为 entry/rejector 依据。
- 当前所有 published readout 的 `cell_sample_status` 都是 `diagnostic_only`：scope `990` 行，arm `1,890` 行。这不是 membership 构建失败，而是 D 继承 A/B/C source-caveated 历史口径并对 E1-missed 分母取保守状态后的结果。

核心发现：risk_on 的 R-core/R6 post-replay retention 很强，已经足够支撑下一步设计 cost rejector 的标签源；transition 的 train/validation 看上去强，但 robustness 明显塌陷，因此不能直接复用 risk_on ranker，仍应优先做 transition family rediscovery。

## 数据与覆盖

### 关键输入源

| source_id                                     | required_flag   | source_status   |   row_count | source_hash                                                      |
|:----------------------------------------------|:----------------|:----------------|------------:|:-----------------------------------------------------------------|
| 06_episode_reference                          | True            | available       |        2493 | 79fba58bb0fbd45569df9fbce93338dd26259fce0d2bbb8dab2090014d15c07e |
| 07_canonical_events                           | True            | available       |       15161 | a35a2742075b0ccbacc1745b96851ff3daef869303f07eafee3e6d2bd605bd57 |
| 07_event_labels                               | True            | available       |       15161 | 2ad39e2c93f3bdf303e9b01435b5b6c002201510a5b6852c76ddc73d9e7a01a3 |
| candidate_family_canonical_events             | True            | available       |      177108 | 1bb1c445d494cb59c57a9fbb5057dfc8b61e34e8f0f8187c27bd9ce209273cb8 |
| candidate_family_capture                      | True            | available       |      857592 | ffc107a57c8612d8537e84f9c28c50708f7cfa3d6978befe276d870580918d81 |
| candidate_family_event_labels                 | True            | available       |      331318 | a6fbb17753e2f6c7bf54bfeccc2aff03419a9891bd87bb4f75e1667a1f0bd5b8 |
| candidate_scope_mapping_contract              | True            | available       |          36 | c99625e0ca82e717aa03aa497e652a47c2dcda7f17c41512575bf299de994d16 |
| regime_family_performance_matrix              | True            | available       |         186 | e3a58055ba99b2e771bf34a545e54d5879bea09e00985ba27d9b77b678e92063 |
| risk_on_r_series_ranker_bridge_recall_readout | True            | available       |         189 | bdf94b573213fdeb72d5ea9a8bd39895939b26e6c4e36523850e81c19516e6d8 |
| risk_on_r_series_ranker_selected_events       | True            | available       |       28135 | 77cce898ec3126a3c0f6bf162ce6825974cfa42db0a9973ea295f7fb7e08b265 |

### Episode Window / Denominator

| window             | episode_window_source_status   |   row_count |   episode_n |   dedup_conflict_n |
|:-------------------|:-------------------------------|------------:|------------:|-------------------:|
| low_to_first_50pct | episode_window_ready           |        2493 |        2493 |                  0 |
| low_to_high        | episode_window_ready           |        2493 |        2493 |                  0 |

| split      | market_regime_bucket   | window             |   target_episode_denominator_n |   bridge_episode_denominator_n |   pre_replay_any_captured_episode_n |   pre_replay_any_recall |
|:-----------|:-----------------------|:-------------------|-------------------------------:|-------------------------------:|------------------------------------:|------------------------:|
| robustness | risk_off               | low_to_first_50pct |                            477 |                            477 |                                 386 |                   0.809 |
| robustness | risk_off               | low_to_high        |                            477 |                            477 |                                 396 |                   0.830 |
| robustness | risk_on                | low_to_first_50pct |                            181 |                            181 |                                  89 |                   0.492 |
| robustness | risk_on                | low_to_high        |                            181 |                            181 |                                  90 |                   0.497 |
| robustness | transition             | low_to_first_50pct |                            100 |                            100 |                                  40 |                   0.400 |
| robustness | transition             | low_to_high        |                            100 |                            100 |                                  41 |                   0.410 |
| train      | risk_off               | low_to_first_50pct |                            761 |                            761 |                                 577 |                   0.758 |
| train      | risk_off               | low_to_high        |                            761 |                            761 |                                 583 |                   0.766 |
| train      | risk_on                | low_to_first_50pct |                            225 |                            225 |                                 142 |                   0.631 |
| train      | risk_on                | low_to_high        |                            225 |                            225 |                                 145 |                   0.644 |
| train      | transition             | low_to_first_50pct |                            304 |                            304 |                                 189 |                   0.622 |
| train      | transition             | low_to_high        |                            304 |                            304 |                                 189 |                   0.622 |
| validation | risk_off               | low_to_first_50pct |                            342 |                            342 |                                 284 |                   0.830 |
| validation | risk_off               | low_to_high        |                            342 |                            342 |                                 296 |                   0.865 |
| validation | risk_on                | low_to_first_50pct |                             22 |                             22 |                                   9 |                   0.409 |
| validation | risk_on                | low_to_high        |                             22 |                             22 |                                   9 |                   0.409 |
| validation | transition             | low_to_first_50pct |                             81 |                             81 |                                  57 |                   0.704 |
| validation | transition             | low_to_high        |                             81 |                             81 |                                  58 |                   0.716 |

解读：06 episode 分母仍是 `2,493` 个目标 episode，每个 episode 有 `low_to_first_50pct` 和 `low_to_high` 两个窗口，所以 window audit 共 `4,986` 行。validation/risk_on 只有 `22` 个 episode，validation/transition 只有 `81` 个 episode；这两个 cell 的结论只能作为方向性诊断。

### Scope Mapping 与 C Arm Coverage

| source_id                    | required_flag   | source_status   |   row_count | source_row_filter                                                                            |
|:-----------------------------|:----------------|:----------------|------------:|:---------------------------------------------------------------------------------------------|
| 07_E1_only                   | True            | available       |        6820 | triggered_channels contains E1_early_ema60_repair                                            |
| 07_full_union                | False           | available       |       15161 | all rows in 07 canonical publishable table                                                   |
| 08_R1_event_regime_gated     | True            | available       |       14363 | triggered_family_variants contains R1_relative_strength_breakout__event_regime_gated         |
| 08_R2_event_regime_gated     | True            | available       |        9537 | triggered_family_variants contains R2_near_high_volume_expansion__event_regime_gated         |
| 08_R6_event_regime_gated     | True            | available       |       16204 | triggered_family_variants contains R6_market_breadth_thrust__event_regime_gated              |
| 08_R7_event_regime_gated     | True            | available       |        9786 | triggered_family_variants contains R7_cross_sectional_momentum_rank_jump__event_regime_gated |
| 08_R8_event_regime_gated     | True            | available       |       12896 | triggered_family_variants contains R8_persistent_distance_above_ema__event_regime_gated      |
| 08_R_core_event_regime_gated | True            | available       |       47914 | triggered_family_variants contains any R1/R2/R6/R7/R8 event_regime_gated variant             |
| 08_T4_gated                  | True            | available       |        1463 | triggered_family_variants contains T4 event_regime_gated                                     |
| 08_T7_gated                  | True            | available       |         629 | triggered_family_variants contains T7 event_regime_gated                                     |
| 08_selected_T4_T7_union      | True            | available       |        2063 | triggered_family_variants contains selected T4/T7 event_regime_gated variants                |

C arm coverage：`21` 个 arm_id，`63` 个 arm×target_regime 组合，risk_off/risk_on/transition 各 `{'risk_off': 21, 'risk_on': 21, 'transition': 21}`。source coverage audit 中 C arm enrichment blocking rows = `0`。

## Scope Post-Replay Retention

下表使用 `low_to_first_50pct` + `post_replay_executable_horizon_complete`，这是非 oracle 的主要 post-replay source readout。

| candidate_scope_id           | split      | market_regime_bucket   |   target_episode_denominator_n |   post_replay_any_captured_episode_n |   post_replay_any_recall |   e1_missed_post_replay_capture_n | cell_sample_status   |
|:-----------------------------|:-----------|:-----------------------|-------------------------------:|-------------------------------------:|-------------------------:|----------------------------------:|:---------------------|
| 08_R_core_event_regime_gated | robustness | risk_on                |                            181 |                                  171 |                    0.945 |                                84 | diagnostic_only      |
| 08_R6_event_regime_gated     | robustness | risk_on                |                            181 |                                  163 |                    0.901 |                                77 | diagnostic_only      |
| 08_R2_event_regime_gated     | robustness | risk_on                |                            181 |                                  134 |                    0.740 |                                52 | diagnostic_only      |
| 07_E1_only                   | robustness | risk_on                |                            181 |                                   89 |                    0.492 |                                 0 | diagnostic_only      |
| 08_selected_T4_T7_union      | robustness | risk_on                |                            181 |                                   36 |                    0.199 |                                 9 | diagnostic_only      |
| 08_R_core_event_regime_gated | train      | risk_on                |                            225 |                                  221 |                    0.982 |                                80 | diagnostic_only      |
| 08_R6_event_regime_gated     | train      | risk_on                |                            225 |                                  216 |                    0.960 |                                77 | diagnostic_only      |
| 08_R2_event_regime_gated     | train      | risk_on                |                            225 |                                  196 |                    0.871 |                                74 | diagnostic_only      |
| 07_E1_only                   | train      | risk_on                |                            225 |                                  142 |                    0.631 |                                 0 | diagnostic_only      |
| 08_selected_T4_T7_union      | train      | risk_on                |                            225 |                                   49 |                    0.218 |                                15 | diagnostic_only      |
| 08_R6_event_regime_gated     | validation | risk_on                |                             22 |                                   22 |                    1.000 |                                13 | diagnostic_only      |
| 08_R_core_event_regime_gated | validation | risk_on                |                             22 |                                   22 |                    1.000 |                                13 | diagnostic_only      |
| 08_R2_event_regime_gated     | validation | risk_on                |                             22 |                                   20 |                    0.909 |                                12 | diagnostic_only      |
| 07_E1_only                   | validation | risk_on                |                             22 |                                    9 |                    0.409 |                                 0 | diagnostic_only      |
| 08_selected_T4_T7_union      | validation | risk_on                |                             22 |                                    3 |                    0.136 |                                 2 | diagnostic_only      |
| 08_R_core_event_regime_gated | robustness | transition             |                            100 |                                   50 |                    0.500 |                                11 | diagnostic_only      |
| 08_R2_event_regime_gated     | robustness | transition             |                            100 |                                   45 |                    0.450 |                                 9 | diagnostic_only      |
| 08_R6_event_regime_gated     | robustness | transition             |                            100 |                                   43 |                    0.430 |                                 7 | diagnostic_only      |
| 07_E1_only                   | robustness | transition             |                            100 |                                   40 |                    0.400 |                                 0 | diagnostic_only      |
| 08_selected_T4_T7_union      | robustness | transition             |                            100 |                                   12 |                    0.120 |                                 2 | diagnostic_only      |
| 08_R_core_event_regime_gated | train      | transition             |                            304 |                                  301 |                    0.990 |                               112 | diagnostic_only      |
| 08_R6_event_regime_gated     | train      | transition             |                            304 |                                  292 |                    0.961 |                               108 | diagnostic_only      |
| 08_R2_event_regime_gated     | train      | transition             |                            304 |                                  260 |                    0.855 |                                95 | diagnostic_only      |
| 07_E1_only                   | train      | transition             |                            304 |                                  188 |                    0.618 |                                 0 | diagnostic_only      |
| 08_selected_T4_T7_union      | train      | transition             |                            304 |                                   70 |                    0.230 |                                25 | diagnostic_only      |
| 08_R_core_event_regime_gated | validation | transition             |                             81 |                                   79 |                    0.975 |                                24 | diagnostic_only      |
| 08_R6_event_regime_gated     | validation | transition             |                             81 |                                   77 |                    0.951 |                                22 | diagnostic_only      |
| 07_E1_only                   | validation | transition             |                             81 |                                   57 |                    0.704 |                                 0 | diagnostic_only      |
| 08_R2_event_regime_gated     | validation | transition             |                             81 |                                   51 |                    0.630 |                                15 | diagnostic_only      |
| 08_selected_T4_T7_union      | validation | transition             |                             81 |                                    7 |                    0.086 |                                 0 | diagnostic_only      |

发现：

- risk_on：R-core 在 train/robustness 的 post-replay recall 分别为 `98.2%` / `94.5%`，对应 E1-missed post-replay capture `80` / `84`。R6 单因子也很强，train/robustness recall 为 `96.0%` / `90.1%`。
- transition：R-core train recall `99.0%`，但 robustness 只有 `50.0%`；这个 split gap 比 risk_on 大得多，说明 transition 不是简单的 risk_on 外推问题。
- T4/T7 negative-control 继续偏弱：risk_on train 的 T4/T7 union recall 只有 `21.8%`，transition train 只有 `23.0%`；它们不适合作为 transition recall 主指标。
- E1 本身在 risk_on/transition 的 post-replay recall 明显低于 R-core/R6：risk_on train E1 为 `63.1%`，transition train E1 为 `61.8%`。D 确认 E1 不是 post-replay retention 的上限，而是一个需要被补充的 baseline。

## C Arm Post-Replay Retention

### Top Arm Readout

| target_regime   | split      | arm_id                                  |   target_episode_denominator_n |   post_replay_any_recall |   e1_missed_post_replay_capture_n |   selected_event_n |   filter_drop_rate |
|:----------------|:-----------|:----------------------------------------|-------------------------------:|-------------------------:|----------------------------------:|-------------------:|-------------------:|
| risk_on         | train      | baseline_r_core_no_ranker_diagnostic    |                            225 |                    0.942 |                                80 |              16603 |              0.002 |
| risk_on         | train      | cross_family_collision_suppression      |                            225 |                    0.942 |                                80 |              16614 |              0.003 |
| risk_on         | train      | r6_r1_r2_r7_bridge_pool                 |                            225 |                    0.929 |                                80 |              13071 |              0.003 |
| risk_on         | robustness | baseline_r_core_no_ranker_diagnostic    |                            181 |                    0.873 |                                78 |               9730 |              0.002 |
| risk_on         | robustness | cross_family_collision_suppression      |                            181 |                    0.873 |                                78 |               9731 |              0.002 |
| risk_on         | robustness | r6_r1_r2_r7_bridge_pool                 |                            181 |                    0.867 |                                78 |               7924 |              0.002 |
| risk_on         | validation | baseline_r_core_no_ranker_diagnostic    |                             22 |                    0.864 |                                11 |               4457 |              0.000 |
| risk_on         | validation | cross_family_collision_suppression      |                             22 |                    0.864 |                                11 |               4459 |              0.001 |
| risk_on         | validation | r6_r1_r2_r7_bridge_pool                 |                             22 |                    0.818 |                                10 |               3662 |              0.001 |
| transition      | train      | baseline_r_core_no_ranker_diagnostic    |                            304 |                    0.651 |                                80 |               7689 |              0.001 |
| transition      | train      | cross_family_collision_suppression      |                            304 |                    0.651 |                                80 |               7690 |              0.001 |
| transition      | train      | r6_r1_r2_r7_bridge_pool                 |                            304 |                    0.641 |                                80 |               6759 |              0.001 |
| transition      | robustness | baseline_r_core_no_ranker_diagnostic    |                            100 |                    0.310 |                                 4 |               3225 |              0.001 |
| transition      | robustness | top_k_per_instrument_20d_family_aware   |                            100 |                    0.310 |                                 4 |               1925 |              0.001 |
| transition      | robustness | top_k_per_instrument_month_family_aware |                            100 |                    0.310 |                                 4 |               2277 |              0.001 |
| transition      | validation | baseline_r_core_no_ranker_diagnostic    |                             81 |                    0.889 |                                23 |               6210 |              0.001 |
| transition      | validation | top_k_per_instrument_20d_family_aware   |                             81 |                    0.889 |                                23 |               2996 |              0.000 |
| transition      | validation | top_k_per_instrument_month_family_aware |                             81 |                    0.889 |                                23 |               3665 |              0.001 |

### Arm Aggregate

| target_regime   | split      |   max_any_recall |   median_any_recall |   max_e1_missed_capture_n |   active_arm_n |   arm_n |
|:----------------|:-----------|-----------------:|--------------------:|--------------------------:|---------------:|--------:|
| risk_on         | robustness |            0.873 |               0.729 |                        78 |             20 |      21 |
| risk_on         | train      |            0.942 |               0.822 |                        80 |             20 |      21 |
| risk_on         | validation |            0.864 |               0.682 |                        11 |             19 |      21 |
| transition      | robustness |            0.310 |               0.240 |                         4 |             18 |      21 |
| transition      | train      |            0.651 |               0.599 |                        80 |             20 |      21 |
| transition      | validation |            0.889 |               0.802 |                        23 |             20 |      21 |

发现：

- risk_on arm 的上界稳定：train max recall `94.2%`，robustness max `87.3%`，validation max `86.4%`。top arm 基本是 R-core baseline / cross-family collision suppression / R6-R1-R2-R7 pool，说明信号来源主要来自 R-family coverage，而不是复杂 ranker 过滤。
- transition arm 的 split 不稳定：train max `65.1%`，robustness max `31.0%`，validation max `88.9%`。这不是一个可直接上线的 ranker 形态，更像 transition regime 下 episode 定义和候选 family 失配。
- `filter_drop_rate` 在 executable+horizon-complete policy 下非常低，多数 top arm 在 `0.0%~0.3%` 区间。这意味着 post-replay source 构建没有大量丢事件；真正的研究问题是如何在保留高 recall 的同时降低 fast-fail/false-repair 成本。

## E1-Missed Retention

D 的最重要新增读数是：在 E1 没抓到的 episode 中，哪些 family/arm 在 post-replay 后仍能抓到。

| market_regime_bucket   | split      | source_id                    |   e1_missed_episode_n |   source_post_replay_captures_e1_missed_n |   incremental_post_replay_capture_over_e1_rate |
|:-----------------------|:-----------|:-----------------------------|----------------------:|------------------------------------------:|-----------------------------------------------:|
| risk_on                | train      | 08_R_core_event_regime_gated |                    83 |                                        80 |                                          0.964 |
| risk_on                | train      | 08_R6_event_regime_gated     |                    83 |                                        77 |                                          0.928 |
| risk_on                | train      | 08_R1_event_regime_gated     |                    83 |                                        76 |                                          0.916 |
| risk_on                | robustness | 08_R_core_event_regime_gated |                    92 |                                        84 |                                          0.913 |
| risk_on                | robustness | 08_R6_event_regime_gated     |                    92 |                                        77 |                                          0.837 |
| risk_on                | robustness | 08_R1_event_regime_gated     |                    92 |                                        74 |                                          0.804 |
| risk_on                | validation | 08_R_core_event_regime_gated |                    13 |                                        13 |                                          1.000 |
| risk_on                | validation | 08_R6_event_regime_gated     |                    13 |                                        13 |                                          1.000 |
| risk_on                | validation | 08_R1_event_regime_gated     |                    13 |                                        13 |                                          1.000 |
| transition             | train      | 08_R_core_event_regime_gated |                   115 |                                       112 |                                          0.974 |
| transition             | train      | 08_R1_event_regime_gated     |                   115 |                                       110 |                                          0.957 |
| transition             | train      | 08_R6_event_regime_gated     |                   115 |                                       108 |                                          0.939 |
| transition             | robustness | 08_R_core_event_regime_gated |                    60 |                                        11 |                                          0.183 |
| transition             | robustness | 08_R1_event_regime_gated     |                    60 |                                         9 |                                          0.150 |
| transition             | robustness | 08_R2_event_regime_gated     |                    60 |                                         9 |                                          0.150 |
| transition             | validation | 08_R_core_event_regime_gated |                    24 |                                        24 |                                          1.000 |
| transition             | validation | 08_R1_event_regime_gated     |                    24 |                                        23 |                                          0.958 |
| transition             | validation | 08_R8_event_regime_gated     |                    24 |                                        22 |                                          0.917 |
| risk_off               | train      | 08_R_core_event_regime_gated |                   184 |                                       163 |                                          0.886 |
| risk_off               | train      | 08_R6_event_regime_gated     |                   184 |                                       156 |                                          0.848 |
| risk_off               | train      | 08_R1_event_regime_gated     |                   184 |                                       155 |                                          0.842 |
| risk_off               | robustness | 08_R_core_event_regime_gated |                    91 |                                        76 |                                          0.835 |
| risk_off               | robustness | 08_R6_event_regime_gated     |                    91 |                                        72 |                                          0.791 |
| risk_off               | robustness | 08_R1_event_regime_gated     |                    91 |                                        69 |                                          0.758 |
| risk_off               | validation | 08_R_core_event_regime_gated |                    58 |                                        36 |                                          0.621 |
| risk_off               | validation | 08_R1_event_regime_gated     |                    58 |                                        35 |                                          0.603 |
| risk_off               | validation | 08_R6_event_regime_gated     |                    58 |                                        33 |                                          0.569 |

发现：

- risk_on train：E1 missed 83 个 episode，R-core post-replay 捕获 80 个，覆盖率 `96.4%`；R6 捕获 77 个，覆盖率 `92.8%`。这说明 risk_on 的 E1-missed 不是随机噪声，R 系列能系统性补齐。
- risk_on robustness：E1 missed 92 个，R-core 捕获 84 个，R6 捕获 77 个；robustness 仍维持高捕获，支持下一步做 cost rejector。
- transition train：E1 missed 115 个，R-core 捕获 112 个；但 transition robustness 只有 60 个 missed 中捕获 11 个。这个断裂是当前研究方向最重要的负面信号：transition 需要重新定义 family/trigger，而不是只调阈值。
- risk_off 不是本轮目标，但 R-core/R6 在 risk_off 也捕获大量 E1-missed，说明 R 系列很宽，后续 rejector 需要处理跨 regime 泛化和成本。

## Replay Policy / Cost Label 影响

下表展示 train split 中 risk_on 与 transition 的 audit-only oracle policy 对 recall 的影响。注意：这些 oracle policy 使用未来标签，不能作为可部署 entry/rejector。

| source_id                    | market_regime_bucket   | replay_policy_id                                      |   event_drop_rate |   any_recall_delta_pp |   e1_missed_capture_delta_n | policy_effect_interpretation                          |
|:-----------------------------|:-----------------------|:------------------------------------------------------|------------------:|----------------------:|----------------------------:|:------------------------------------------------------|
| 07_E1_only                   | risk_on                | post_replay_executable_horizon_complete               |             0.000 |                 0.000 |                           0 | executable_anchor_and_required_label_horizon_complete |
| 07_E1_only                   | risk_on                | post_replay_non_fast_fail_10d_oracle                  |             0.139 |                -7.556 |                           0 | audit_only_fast_fail_cost_removed                     |
| 07_E1_only                   | risk_on                | post_replay_non_false_repair_20d_oracle               |             0.224 |                -5.333 |                           0 | audit_only_false_repair_cost_removed                  |
| 07_E1_only                   | risk_on                | post_replay_non_fast_fail_and_non_false_repair_oracle |             0.244 |                -8.444 |                           0 | audit_only_fast_fail_and_false_repair_removed         |
| 07_E1_only                   | transition             | post_replay_executable_horizon_complete               |             0.000 |                 0.000 |                           0 | executable_anchor_and_required_label_horizon_complete |
| 07_E1_only                   | transition             | post_replay_non_fast_fail_10d_oracle                  |             0.172 |                -3.947 |                           0 | audit_only_fast_fail_cost_removed                     |
| 07_E1_only                   | transition             | post_replay_non_false_repair_20d_oracle               |             0.210 |                -4.934 |                           0 | audit_only_false_repair_cost_removed                  |
| 07_E1_only                   | transition             | post_replay_non_fast_fail_and_non_false_repair_oracle |             0.246 |                -6.250 |                           0 | audit_only_fast_fail_and_false_repair_removed         |
| 08_R6_event_regime_gated     | risk_on                | post_replay_executable_horizon_complete               |             0.000 |                 0.000 |                           0 | executable_anchor_and_required_label_horizon_complete |
| 08_R6_event_regime_gated     | risk_on                | post_replay_non_fast_fail_10d_oracle                  |             0.305 |                -4.000 |                          -4 | audit_only_fast_fail_cost_removed                     |
| 08_R6_event_regime_gated     | risk_on                | post_replay_non_false_repair_20d_oracle               |             0.391 |                -3.556 |                          -3 | audit_only_false_repair_cost_removed                  |
| 08_R6_event_regime_gated     | risk_on                | post_replay_non_fast_fail_and_non_false_repair_oracle |             0.430 |                -6.222 |                          -5 | audit_only_fast_fail_and_false_repair_removed         |
| 08_R6_event_regime_gated     | transition             | post_replay_executable_horizon_complete               |             0.000 |                 0.000 |                           0 | executable_anchor_and_required_label_horizon_complete |
| 08_R6_event_regime_gated     | transition             | post_replay_non_fast_fail_10d_oracle                  |             0.209 |                -5.921 |                         -11 | audit_only_fast_fail_cost_removed                     |
| 08_R6_event_regime_gated     | transition             | post_replay_non_false_repair_20d_oracle               |             0.255 |                -6.250 |                         -11 | audit_only_false_repair_cost_removed                  |
| 08_R6_event_regime_gated     | transition             | post_replay_non_fast_fail_and_non_false_repair_oracle |             0.287 |                -8.224 |                         -14 | audit_only_fast_fail_and_false_repair_removed         |
| 08_R_core_event_regime_gated | risk_on                | post_replay_executable_horizon_complete               |             0.000 |                 0.000 |                           0 | executable_anchor_and_required_label_horizon_complete |
| 08_R_core_event_regime_gated | risk_on                | post_replay_non_fast_fail_10d_oracle                  |             0.298 |                -1.778 |                          -2 | audit_only_fast_fail_cost_removed                     |
| 08_R_core_event_regime_gated | risk_on                | post_replay_non_false_repair_20d_oracle               |             0.383 |                -0.889 |                          -1 | audit_only_false_repair_cost_removed                  |
| 08_R_core_event_regime_gated | risk_on                | post_replay_non_fast_fail_and_non_false_repair_oracle |             0.421 |                -2.222 |                          -2 | audit_only_fast_fail_and_false_repair_removed         |
| 08_R_core_event_regime_gated | transition             | post_replay_executable_horizon_complete               |             0.000 |                 0.000 |                           0 | executable_anchor_and_required_label_horizon_complete |
| 08_R_core_event_regime_gated | transition             | post_replay_non_fast_fail_10d_oracle                  |             0.224 |                -1.645 |                          -4 | audit_only_fast_fail_cost_removed                     |
| 08_R_core_event_regime_gated | transition             | post_replay_non_false_repair_20d_oracle               |             0.266 |                -1.645 |                          -4 | audit_only_false_repair_cost_removed                  |
| 08_R_core_event_regime_gated | transition             | post_replay_non_fast_fail_and_non_false_repair_oracle |             0.307 |                -3.618 |                          -9 | audit_only_fast_fail_and_false_repair_removed         |

### Policy Aggregate

| source_id                    | replay_policy_id                                      |   avg_event_drop_rate |   min_any_delta_pp |   avg_any_delta_pp |   min_e1_missed_delta_n |
|:-----------------------------|:------------------------------------------------------|----------------------:|-------------------:|-------------------:|------------------------:|
| 07_E1_only                   | post_replay_executable_horizon_complete               |                 0.000 |              0.000 |              0.000 |                       0 |
| 07_E1_only                   | post_replay_non_false_repair_20d_oracle               |                 0.197 |             -7.622 |             -4.072 |                       0 |
| 07_E1_only                   | post_replay_non_fast_fail_10d_oracle                  |                 0.140 |             -8.642 |             -5.311 |                       0 |
| 07_E1_only                   | post_replay_non_fast_fail_and_non_false_repair_oracle |                 0.224 |            -11.111 |             -7.018 |                       0 |
| 08_R6_event_regime_gated     | post_replay_executable_horizon_complete               |                 0.000 |              0.000 |              0.000 |                       0 |
| 08_R6_event_regime_gated     | post_replay_non_false_repair_20d_oracle               |                 0.283 |            -11.602 |             -5.221 |                     -18 |
| 08_R6_event_regime_gated     | post_replay_non_fast_fail_10d_oracle                  |                 0.211 |             -9.945 |             -4.969 |                     -15 |
| 08_R6_event_regime_gated     | post_replay_non_fast_fail_and_non_false_repair_oracle |                 0.309 |            -12.707 |             -7.476 |                     -20 |
| 08_R_core_event_regime_gated | post_replay_executable_horizon_complete               |                 0.000 |              0.000 |              0.000 |                       0 |
| 08_R_core_event_regime_gated | post_replay_non_false_repair_20d_oracle               |                 0.286 |             -8.287 |             -3.564 |                     -15 |
| 08_R_core_event_regime_gated | post_replay_non_fast_fail_10d_oracle                  |                 0.216 |             -8.287 |             -3.071 |                     -15 |
| 08_R_core_event_regime_gated | post_replay_non_fast_fail_and_non_false_repair_oracle |                 0.315 |             -9.392 |             -5.417 |                     -17 |

发现：

- E1 对 fast-fail 和 false-repair 的 recall 损失更敏感：10d fast-fail oracle 平均带来 `-5.31pp` any-recall delta，20d false-repair 平均 `-4.07pp`，联合 oracle 平均 `-7.02pp`。
- R-core 的 recall 损失较小：10d fast-fail 平均 `-3.07pp`，20d false-repair 平均 `-3.56pp`，联合 oracle 平均 `-5.42pp`。这说明 R-core 不只是更宽，也相对更能承受成本过滤。
- R6 的成本压力最高：联合 oracle 平均 `-7.48pp`，最差 cell 到 `-12.71pp`；R6 适合作为高 recall source，但后续必须配 rejector，否则会把一部分 fast-fail/false-repair 成本带进候选集。

## Reconciliation / Leakage / Caveat

| source_experiment   | reconciliation_status           |   row_count |
|:--------------------|:--------------------------------|------------:|
| A                   | missing_upstream_value          |           2 |
| A                   | not_comparable_membership_basis |          10 |
| A                   | not_comparable_source_partial   |           9 |
| A                   | pass                            |          81 |
| C                   | pass                            |         189 |

| scope_or_arm_id          | split      | market_regime_bucket   |   upstream_value |   d_recomputed_pre_replay_value |   absolute_diff |
|:-------------------------|:-----------|:-----------------------|-----------------:|--------------------------------:|----------------:|
| 08_R8_event_regime_gated | train      | transition             |           0.8783 |                          0.8816 |          0.0033 |
| 08_selected_T4_T7_union  | robustness | risk_off               |           0.1677 |                          0.1698 |          0.0021 |
| 08_T7_gated              | robustness | risk_off               |           0.0860 |                          0.0881 |          0.0021 |
| 08_R6_event_regime_gated | robustness | risk_off               |           0.8700 |                          0.8721 |          0.0021 |
| 08_R2_event_regime_gated | robustness | risk_off               |           0.7883 |                          0.7904 |          0.0021 |
| 08_R7_event_regime_gated | robustness | risk_off               |           0.7358 |                          0.7379 |          0.0021 |
| 08_R8_event_regime_gated | train      | risk_off               |           0.8081 |                          0.8095 |          0.0013 |
| 08_R2_event_regime_gated | train      | risk_off               |           0.7806 |                          0.7819 |          0.0013 |
| 08_R7_event_regime_gated | train      | risk_off               |           0.7911 |                          0.7924 |          0.0013 |

| field_name                       | allowed_for_membership_join   | allowed_for_replay_filter   | allowed_as_t0_feature   | uses_future_information   | allowed_downstream_use    | leakage_status   |
|:---------------------------------|:------------------------------|:----------------------------|:------------------------|:--------------------------|:--------------------------|:-----------------|
| replay_anchor_pos                | True                          | True                        | False                   | False                     | membership_join_only      | pass             |
| captured_target_episode_id_first | False                         | False                       | False                   | True                      | reconciliation_audit_only | pass             |
| failure_10_label                 | False                         | True                        | False                   | True                      | oracle_replay_audit_only  | pass             |
| event_false_repair_20d_label     | False                         | True                        | False                   | True                      | oracle_replay_audit_only  | pass             |
| event_big_winner_120d_label      | False                         | True                        | False                   | True                      | downstream_label_only     | pass             |
| episode_membership               | False                         | False                       | False                   | True                      | post_replay_readout_only  | pass             |

解读：

- C arm 对账 `189/189 pass`，说明 D 对 C selected events 的 pre-replay membership 重算可以稳定复现上游 C readout。
- A 对账 `81 pass`，另有 `9` 行 `not_comparable_source_partial`，最大 absolute diff 为 `0.0033`；这些差异集中在 A partial/source-caveated 的 scope 与 split/regime cell，不应触发 contract-blocked。
- A 的 `all/all` 口径有 `10` 行 `not_comparable_membership_basis`，原因是 D 按 materialized replay window 重算 split/regime membership，而 A 的 all/all 是 pre-replay capture aggregate，不是同一 denominator basis。
- leakage audit 全部 pass；`failure_10_label` / `event_false_repair_20d_label` / `event_big_winner_120d_label` 只能用于 oracle audit 或 supervised label，不能作为 t0 feature。

## 研究方向判断

1. risk_on 方向应从“找 recall source”切换到“保 recall 的成本 rejector”。D 已证明 R-core/R6 在 post-replay 后仍能覆盖大量 E1-missed episode；继续扩大 family 的边际收益小于控制 fast-fail/false-repair 的收益。
2. transition 方向仍应重新选择 event family。train/validation 的高 recall 与 robustness 的低 recall 冲突，说明 transition 的 episode/触发机制不稳定；直接用 risk_on R-core ranker 会放大 regime mismatch。
3. T4/T7 不应再作为 recall incumbent。它们可以保留为 negative control 或机制对照，但不应作为 transition recall 目标。
4. D 产物解除的是 source bottleneck，不是 final trading gate。由于所有 cell 仍是 `diagnostic_only`，下一步 Experiment E/F 应消费 D 的 post-replay label source，但不能宣称 D 本身支持 direct entry。

## 发布物

- `post_replay_episode_window_audit.csv`: `4,986` rows
- `post_replay_source_coverage_audit.csv`: `79` rows
- `post_replay_scope_retention_by_split_regime.csv`: `990` rows
- `post_replay_arm_retention_by_split_regime.csv`: `1,890` rows
- `post_replay_policy_effect_summary.csv`: `2,304` rows
- `post_replay_e1_missed_retention_summary.csv`: `2,880` rows
- `post_replay_label_leakage_audit.csv`: `6` rows
- `post_replay_reconciliation_against_a_b_c.csv`: `291` rows
