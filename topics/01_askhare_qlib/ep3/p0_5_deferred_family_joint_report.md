# EP3 P0.5 与 Deferred-Family 联合复盘报告

> 生成范围：EP3 engineering baseline no-go 之后的 P0.5 anchor failure diagnostic，以及本次 `failed_lookalike_avoidance` deferred-family audit。
> 本报告只读取已生成 artifacts，不重新训练、不重新选择阈值、不修改 P0/P0.5 frozen outputs。

## 1. 一句话结论

EP3 当前这条从 A/C anchor 到 failed-lookalike deferred family 的路径，应该停止。P0.5 已经证明 A/C 不是简单的公式太窄或窗口位置问题，而是 matched baseline lift 与 tail risk 问题；本次 deferred-family audit 虽然把 validation trigger rate 提升到接近 20%，但 H20 mean lift、robustness mean lift、robustness p05 tail 仍然输给 matched-delay baseline。因此不支持写 P0.6 freeze，也不支持继续做同一条 failed-lookalike refinement。

核心数据：

- P0.5 validator: `passed`。
- Deferred-family validator: `passed`。
- Deferred-family final decision: `stop_deferred_family`。
- Deferred validation trigger rate: `18.47%`。
- Deferred validation mean diff vs matched-delay: `-2.06%`。
- Deferred robustness mean diff vs matched-delay: `-1.13%`。
- Deferred robustness p05 diff vs matched-delay: `-2.46%`。

## 2. 数据来源与规模

| artifact                                         |   rows |   columns |
|:-------------------------------------------------|-------:|----------:|
| p0_5_anchor_event_diagnostic_panel.parquet       |    862 |        60 |
| p0_5_baseline_event_diagnostic_panel.parquet     |   9734 |        51 |
| deferred_family_formula_diagnostic_panel.parquet | 285454 |        17 |
| deferred_family_event_panel.parquet              |   5197 |        38 |
| deferred_family_matched_baseline_panel.parquet   |   4603 |        29 |

Manifest 状态：

| phase                    | manifest                                     | validation_status   |
|:-------------------------|:---------------------------------------------|:--------------------|
| EP3 engineering baseline | ep3_engineering_baseline_manifest.json       | passed              |
| EP3 P0.5 diagnostic      | p0_5_anchor_failure_diagnostic_manifest.json | passed              |
| EP3 deferred family      | deferred_family_manifest.json                | passed              |

## 3. EP3 P0 Engineering Baseline 的失败链条

P0 baseline 的两个 primary family 是 `pullback_hold_restrengthen` 与 `second_breakout`。它们在 lifecycle recall 上并不弱，说明 winner lifecycle 里确实能看到类似 anchor；但 forward-audit executable events 的 trigger/lift/tail 没有过关。

| family                     |   passed_gates |   failed_gates | lifecycle_recall   | validation_trigger_rate   | validation_mean_diff_vs_delay   | validation_p05_diff_vs_delay   | robustness_mean_diff_vs_delay   | robustness_p05_diff_vs_delay   |
|:---------------------------|---------------:|---------------:|:-------------------|:--------------------------|:--------------------------------|:-------------------------------|:--------------------------------|:-------------------------------|
| pullback_hold_restrengthen |              7 |              8 | 34.46%             | 14.37%                    | -2.22%                          | -1.52%                         | 1.61%                           | -0.52%                         |
| second_breakout            |              9 |              6 | 46.11%             | 11.94%                    | -0.88%                          | -4.08%                         | -0.50%                          | -4.35%                         |

解读：

- `pullback_hold_restrengthen` lifecycle recall 达到 34.46%，但 validation trigger 只有 14.37%，且 validation mean diff vs matched-delay 为 -2.22%。
- `second_breakout` lifecycle recall 达到 46.11%，但 validation trigger 只有 11.94%，且 validation mean diff vs matched-delay 为 -0.88%。
- 所以 P0 的问题不是“winner 里完全找不到形态”，而是这些形态转成可执行 forward-audit anchor 后没有稳定 lift。

## 4. P0.5 Diagnostic：为什么 A/C 不值得继续修

### 4.1 P0.5 决策

| decision_scope   | anchor_family_id           | recommended_decision              |   validation_interpretable_partition_count |   robustness_interpretable_partition_count | supporting_hypothesis_ids                                                                      | decision_rule_status   |
|:-----------------|:---------------------------|:----------------------------------|-------------------------------------------:|-------------------------------------------:|:-----------------------------------------------------------------------------------------------|:-----------------------|
| family           | pullback_hold_restrengthen | stop_current_family               |                                          8 |                                          8 | h4_matched_baseline_too_strong_or_anchor_no_lift;h5_tail_risk_not_trigger_rate_is_core_failure | passed                 |
| family           | second_breakout            | stop_current_family               |                                         10 |                                          7 | h4_matched_baseline_too_strong_or_anchor_no_lift;h5_tail_risk_not_trigger_rate_is_core_failure | passed                 |
| overall          | all                        | write_deferred_family_requirement |                                         18 |                                         15 | 不适用                                                                                         | passed                 |

P0.5 的结论是两个 A/C family 都 `stop_current_family`，overall 才允许进入 deferred-family requirement。这个意思不是 A/C 可以继续作为策略候选，而是说需要换一个问题：解释 A/C 为什么失败，并尝试新的 deferred-family 审计。

### 4.2 P0.5 Hypothesis Audit

| anchor_family_id           | hypothesis_id                                    | support_status   | support_rule_status   | requires_new_requirement   | evidence_summary                                                                         |
|:---------------------------|:-------------------------------------------------|:-----------------|:----------------------|:---------------------------|:-----------------------------------------------------------------------------------------|
| pullback_hold_restrengthen | h1_formula_too_narrow                            | rejected         | failed                | False                      | validation_positive_partitions=0; robustness_not_collapsed=0                             |
| pullback_hold_restrengthen | h2_window_position_problem                       | rejected         | failed                | False                      | validation_positive_partitions=0; robustness_not_collapsed=0                             |
| pullback_hold_restrengthen | h3_ep2_reference_pollution                       | rejected         | failed                | False                      | validation_cross_split_ratio=0.03896103896103896; robustness_cross_split_ratio=0.0       |
| pullback_hold_restrengthen | h4_matched_baseline_too_strong_or_anchor_no_lift | supported        | passed                | True                       | {"validation": true, "robustness": true}                                                 |
| pullback_hold_restrengthen | h5_tail_risk_not_trigger_rate_is_core_failure    | supported        | passed                | True                       | {"validation": true, "robustness": true}                                                 |
| second_breakout            | h1_formula_too_narrow                            | rejected         | failed                | False                      | validation_positive_partitions=0; robustness_not_collapsed=0                             |
| second_breakout            | h2_window_position_problem                       | rejected         | failed                | False                      | validation_positive_partitions=0; robustness_not_collapsed=0                             |
| second_breakout            | h3_ep2_reference_pollution                       | rejected         | failed                | False                      | validation_cross_split_ratio=0.015625; robustness_cross_split_ratio=0.017241379310344827 |
| second_breakout            | h4_matched_baseline_too_strong_or_anchor_no_lift | supported        | passed                | True                       | {"validation": true, "robustness": true}                                                 |
| second_breakout            | h5_tail_risk_not_trigger_rate_is_core_failure    | supported        | passed                | True                       | {"validation": true, "robustness": true}                                                 |

关键发现：

- `h1_formula_too_narrow` rejected：没有找到 validation-positive 且 robustness 不崩的公式 margin partition。
- `h2_window_position_problem` rejected：窗口位置/年龄分桶也没有救出稳定 lift。
- `h3_ep2_reference_pollution` rejected：cross-split reference 不是主因。
- `h4_matched_baseline_too_strong_or_anchor_no_lift` supported：matched-delay 暴露出 A/C 没有真实 anchor lift。
- `h5_tail_risk_not_trigger_rate_is_core_failure` supported：tail/concentration 风险是核心失败之一。

### 4.3 P0.5 Trigger 数据

| split      | anchor_family_id           |   anchor_trigger_count |   ep2_launch_episode_count | trigger_rate_per_launch_episode   |   unique_instrument_count |   unique_instrument_year_count | interpretation_status   |
|:-----------|:---------------------------|-----------------------:|---------------------------:|:----------------------------------|--------------------------:|-------------------------------:|:------------------------|
| robustness | pullback_hold_restrengthen |                    100 |                        775 | 12.90%                            |                        81 |                             86 | interpretable           |
| train      | pullback_hold_restrengthen |                    229 |                       1153 | 19.86%                            |                       132 |                            184 | interpretable           |
| validation | pullback_hold_restrengthen |                     91 |                        536 | 16.98%                            |                        76 |                             80 | interpretable           |
| robustness | second_breakout            |                    132 |                        775 | 17.03%                            |                        99 |                            113 | interpretable           |
| train      | second_breakout            |                    221 |                       1153 | 19.17%                            |                       140 |                            191 | interpretable           |
| validation | second_breakout            |                     70 |                        536 | 13.06%                            |                        63 |                             67 | interpretable           |

### 4.4 P0.5 Matched-Delay Lift 数据

| split      | anchor_family_id           |   anchor_event_count |   baseline_event_count |   unique_instrument_year_count | anchor_mean_after_cost_return_H20   | baseline_mean_after_cost_return_H20   | mean_diff_vs_baseline   | anchor_p05_after_cost_return_H20   | baseline_p05_after_cost_return_H20   | p05_diff_vs_baseline   | anchor_instrument_year_positive_rate   | baseline_instrument_year_positive_rate   | interpretation_status   |
|:-----------|:---------------------------|---------------------:|-----------------------:|-------------------------------:|:------------------------------------|:--------------------------------------|:------------------------|:-----------------------------------|:-------------------------------------|:-----------------------|:---------------------------------------|:-----------------------------------------|:------------------------|
| robustness | pullback_hold_restrengthen |                   57 |                     57 |                             49 | -0.45%                              | -2.06%                                | 1.61%                   | -13.26%                            | -12.74%                              | -0.52%                 | 38.78%                                 | 32.00%                                   | interpretable           |
| train      | pullback_hold_restrengthen |                  179 |                    179 |                            147 | 0.15%                               | -0.05%                                | 0.19%                   | -18.31%                            | -18.96%                              | 0.65%                  | 48.30%                                 | 39.86%                                   | interpretable           |
| validation | pullback_hold_restrengthen |                   73 |                     73 |                             66 | -5.74%                              | -3.65%                                | -2.09%                  | -20.55%                            | -18.97%                              | -1.57%                 | 22.73%                                 | 34.85%                                   | interpretable           |
| robustness | second_breakout            |                   57 |                     57 |                             55 | -1.22%                              | -0.22%                                | -1.00%                  | -15.50%                            | -11.13%                              | -4.37%                 | 41.82%                                 | 34.55%                                   | interpretable           |
| train      | second_breakout            |                  181 |                    181 |                            155 | -0.40%                              | -0.25%                                | -0.16%                  | -22.30%                            | -18.37%                              | -3.93%                 | 42.58%                                 | 44.52%                                   | interpretable           |
| validation | second_breakout            |                   63 |                     63 |                             61 | -1.98%                              | -1.22%                                | -0.77%                  | -17.69%                            | -13.60%                              | -4.09%                 | 36.07%                                 | 32.79%                                   | interpretable           |

### 4.5 P0.5 Tail / Concentration 数据

| split      | anchor_family_id           | failed_lookalike_rate   | top1_instrument_year_pnl_share   | top5_instrument_exposure_share   | anchor_max_adverse_excursion_mean_H20   | baseline_max_adverse_excursion_mean_H20   | mae_worsening_vs_baseline   | interpretation_status   |
|:-----------|:---------------------------|:------------------------|:---------------------------------|:---------------------------------|:----------------------------------------|:------------------------------------------|:----------------------------|:------------------------|
| robustness | pullback_hold_restrengthen | 50.00%                  | 13.36%                           | 19.30%                           | -7.88%                                  | -8.39%                                    | 0.00%                       | interpretable           |
| train      | pullback_hold_restrengthen | 50.28%                  | 4.67%                            | 12.15%                           | -9.42%                                  | -9.11%                                    | 0.31%                       | interpretable           |
| validation | pullback_hold_restrengthen | 51.01%                  | 20.55%                           | 12.99%                           | -12.09%                                 | -10.34%                                   | 1.75%                       | interpretable           |
| robustness | second_breakout            | 50.00%                  | 11.78%                           | 15.52%                           | -9.46%                                  | -6.79%                                    | 2.67%                       | interpretable           |
| train      | second_breakout            | 49.16%                  | 8.02%                            | 9.78%                            | -10.14%                                 | -9.89%                                    | 0.25%                       | interpretable           |
| validation | second_breakout            | 48.78%                  | 17.67%                           | 15.62%                           | -9.89%                                  | -9.57%                                    | 0.32%                       | interpretable           |

### 4.6 P0.5 中看起来“频率足够”的分桶也没有解决问题

下面是 validation 中 trigger rate >= 20% 且 interpretable 的 matched-delay 分桶。它们即使触发足够，mean/p05 也没有形成可进入 P1 的证据。

| anchor_family_id           | diagnostic_axis   |   diagnostic_bucket |   anchor_event_count |   unique_instrument_year_count | trigger_rate_per_launch_episode   | mean_diff_vs_baseline   | p05_diff_vs_baseline   |
|:---------------------------|:------------------|--------------------:|---------------------:|-------------------------------:|:----------------------------------|:------------------------|:-----------------------|
| pullback_hold_restrengthen | vol20_bucket      |                   4 |                   24 |                             23 | 29.87%                            | -4.40%                  | -1.67%                 |
| second_breakout            | ret_60d_bucket    |                   4 |                   53 |                             52 | 25.25%                            | -1.44%                  | -5.49%                 |
| pullback_hold_restrengthen | ret_60d_bucket    |                   4 |                   31 |                             30 | 23.27%                            | -3.79%                  | -1.88%                 |
| pullback_hold_restrengthen | money_bucket      |                   4 |                   34 |                             32 | 21.50%                            | -3.59%                  | -2.70%                 |
| second_breakout            | money_bucket      |                   4 |                   44 |                             42 | 21.03%                            | -1.74%                  | -4.64%                 |
| pullback_hold_restrengthen | money_bucket      |                   3 |                   25 |                             24 | 20.16%                            | -2.70%                  | -4.81%                 |

P0.5 因此给出的正确动作是：停止 A/C 本身，写 deferred-family requirement，而不是继续在 A/C 内部调阈值。

## 5. Deferred-Family Audit：failed_lookalike_avoidance 的实际结果

本次 deferred-family audit 的问题是：是否能把 A/C-like 失败状态与后续 observable recovery 区分出来，从而形成一个更干净的 forward-audit family。

### 5.1 Formula Diagnostic 覆盖

| split      | lookalike_source_family   | formula_availability_status   |   rows |
|:-----------|:--------------------------|:------------------------------|-------:|
| robustness | A-like                    | available                     |  42943 |
| robustness | A-like                    | unavailable                   |   1122 |
| robustness | C-like                    | available                     |  43130 |
| robustness | C-like                    | unavailable                   |    935 |
| train      | A-like                    | available                     |  65315 |
| train      | A-like                    | unavailable                   |   2019 |
| train      | C-like                    | available                     |  65685 |
| train      | C-like                    | unavailable                   |   1649 |
| validation | A-like                    | available                     |  30742 |
| validation | A-like                    | unavailable                   |    586 |
| validation | C-like                    | available                     |  30742 |
| validation | C-like                    | unavailable                   |    586 |

按 failed condition count 分解：

| lookalike_source_family   |   failed_condition_count |   rows |
|:--------------------------|-------------------------:|-------:|
| A-like                    |                        0 |   3841 |
| A-like                    |                        1 |  29179 |
| A-like                    |                        2 |  85641 |
| A-like                    |                        3 |  22261 |
| A-like                    |                        4 |   1805 |
| C-like                    |                        0 |   4637 |
| C-like                    |                        1 |   5796 |
| C-like                    |                        2 |  80192 |
| C-like                    |                        3 |  40995 |
| C-like                    |                        4 |  11107 |

观察：A-like 的 exactly-one-failed rows 很多，但真正能转成 primary recovery 的很少；C-like 的 recovery 贡献更明显。

### 5.2 Event Panel 分解

| split      | lookalike_source_family   | event_type                      |   rows |
|:-----------|:--------------------------|:--------------------------------|-------:|
| robustness | A-like                    | clean_avoidance_state           |      5 |
| robustness | A-like                    | failure_lookalike_state         |    744 |
| robustness | A-like                    | recovery_after_failed_lookalike |      7 |
| robustness | C-like                    | clean_avoidance_state           |    155 |
| robustness | C-like                    | failure_lookalike_state         |    594 |
| robustness | C-like                    | recovery_after_failed_lookalike |    170 |
| train      | A-like                    | clean_avoidance_state           |      5 |
| train      | A-like                    | failure_lookalike_state         |   1107 |
| train      | A-like                    | recovery_after_failed_lookalike |     21 |
| train      | C-like                    | clean_avoidance_state           |    231 |
| train      | C-like                    | failure_lookalike_state         |    842 |
| train      | C-like                    | recovery_after_failed_lookalike |    236 |
| validation | A-like                    | clean_avoidance_state           |      5 |
| validation | A-like                    | failure_lookalike_state         |    512 |
| validation | A-like                    | recovery_after_failed_lookalike |      9 |
| validation | C-like                    | clean_avoidance_state           |     90 |
| validation | C-like                    | failure_lookalike_state         |    372 |
| validation | C-like                    | recovery_after_failed_lookalike |     92 |

Primary forward-audit events：

| split      | lookalike_source_family   |   primary_events |
|:-----------|:--------------------------|-----------------:|
| robustness | A-like                    |                6 |
| robustness | C-like                    |              148 |
| train      | A-like                    |               20 |
| train      | C-like                    |              233 |
| validation | A-like                    |                9 |
| validation | C-like                    |               90 |

核心观察：deferred-family 的可用事件几乎都来自 C-like。A-like 在 validation 只有 9 个 primary events，robustness 只有 6 个，不能成为主线证据。

### 5.3 Trigger 数据

| split      | event_type                      | trigger_rate_type                |   event_count |   canonical_launch_episode_count | trigger_rate_per_launch_episode   |   unique_instrument_count |   unique_instrument_year_count | interpretation_status   |
|:-----------|:--------------------------------|:---------------------------------|--------------:|---------------------------------:|:----------------------------------|--------------------------:|-------------------------------:|:------------------------|
| robustness | clean_avoidance_state           | diagnostic_clean_avoidance_state |           160 |                              775 | 20.65%                            |                       109 |                            136 | interpretable           |
| robustness | failure_lookalike_state         | diagnostic_failure_state         |          1338 |                              775 | 172.65%                           |                       251 |                            420 | interpretable           |
| robustness | recovery_after_failed_lookalike | gate_eligible_h20_recovery_event |           154 |                              775 | 19.87%                            |                       107 |                            133 | interpretable           |
| robustness | recovery_after_failed_lookalike | raw_recovery_event               |           177 |                              775 | 22.84%                            |                       116 |                            153 | interpretable           |
| train      | clean_avoidance_state           | diagnostic_clean_avoidance_state |           236 |                             1153 | 20.47%                            |                       142 |                            202 | interpretable           |
| train      | failure_lookalike_state         | diagnostic_failure_state         |          1949 |                             1153 | 169.04%                           |                       230 |                            642 | interpretable           |
| train      | recovery_after_failed_lookalike | gate_eligible_h20_recovery_event |           253 |                             1153 | 21.94%                            |                       142 |                            215 | interpretable           |
| train      | recovery_after_failed_lookalike | raw_recovery_event               |           257 |                             1153 | 22.29%                            |                       145 |                            219 | interpretable           |
| validation | clean_avoidance_state           | diagnostic_clean_avoidance_state |            95 |                              536 | 17.72%                            |                        75 |                             85 | interpretable           |
| validation | failure_lookalike_state         | diagnostic_failure_state         |           884 |                              536 | 164.93%                           |                       233 |                            343 | interpretable           |
| validation | recovery_after_failed_lookalike | gate_eligible_h20_recovery_event |            99 |                              536 | 18.47%                            |                        78 |                             86 | interpretable           |
| validation | recovery_after_failed_lookalike | raw_recovery_event               |           101 |                              536 | 18.84%                            |                        80 |                             88 | interpretable           |

按 source family 的 gate-eligible recovery trigger：

| split      | diagnostic_bucket   |   event_count |   canonical_launch_episode_count | trigger_rate_per_launch_episode   |   unique_instrument_count |   unique_instrument_year_count | interpretation_status   |
|:-----------|:--------------------|--------------:|---------------------------------:|:----------------------------------|--------------------------:|-------------------------------:|:------------------------|
| robustness | A-like              |             6 |                              775 | 0.77%                             |                         5 |                              5 | too_sparse              |
| robustness | C-like              |           148 |                              775 | 19.10%                            |                       104 |                            130 | interpretable           |
| train      | A-like              |            20 |                             1153 | 1.73%                             |                        20 |                             20 | interpretable           |
| train      | C-like              |           233 |                             1153 | 20.21%                            |                       138 |                            205 | interpretable           |
| validation | A-like              |             9 |                              536 | 1.68%                             |                         9 |                              9 | too_sparse              |
| validation | C-like              |            90 |                              536 | 16.79%                            |                        74 |                             80 | interpretable           |

解释：

- overall validation trigger rate 为 18.47%，接近但低于原 EP3 P0 的 20% 主 family 预算；作为 deferred bridge threshold，它超过了 10%。
- robustness trigger rate 为 19.87%，没有 collapse。
- 但 A-like trigger 基本不可用；C-like 是全部可解释 trigger 的主要来源。

### 5.4 Baseline Match 质量

| baseline_id                        | match_status   |   rows |
|:-----------------------------------|:---------------|-------:|
| all_launch_direct_baseline         | matched        |   2464 |
| industry_matched_baseline          | matched        |    403 |
| industry_matched_baseline          | unmatched      |    103 |
| matched_delay_baseline             | matched        |    506 |
| same_instrument_nonanchor_baseline | matched        |    407 |
| same_instrument_nonanchor_baseline | unmatched      |     99 |
| stopped_ac_anchor_baseline         | matched        |    621 |

matched-delay、same-instrument、industry 三类 baseline 都已经生成；same/industry 存在部分 unmatched，但 matched 数量足够用于整体诊断。

### 5.5 Deferred-Family H20 Lift vs Baselines

| split      | baseline_id                        |   anchor_event_count |   baseline_event_count |   unique_instrument_year_count | anchor_mean_after_cost_return_H20   | baseline_mean_after_cost_return_H20   | mean_diff_vs_baseline   | anchor_p05_after_cost_return_H20   | baseline_p05_after_cost_return_H20   | p05_diff_vs_baseline   | mae_worsening_vs_baseline   | instrument_year_positive_rate_diff   | interpretation_status   |
|:-----------|:-----------------------------------|---------------------:|-----------------------:|-------------------------------:|:------------------------------------|:--------------------------------------|:------------------------|:-----------------------------------|:-------------------------------------|:-----------------------|:----------------------------|:-------------------------------------|:------------------------|
| robustness | all_launch_direct_baseline         |                  154 |                    746 |                            133 | 0.53%                               | -0.55%                                | 1.08%                   | -17.10%                            | -17.30%                              | 0.20%                  | -0.86%                      | 3.38%                                | interpretable           |
| robustness | industry_matched_baseline          |                  154 |                     96 |                            133 | 0.53%                               | -0.66%                                | 1.19%                   | -17.10%                            | -11.40%                              | -5.70%                 | -2.06%                      | 2.18%                                | interpretable           |
| robustness | matched_delay_baseline             |                  154 |                    154 |                            133 | 0.53%                               | 1.66%                                 | -1.13%                  | -17.10%                            | -14.64%                              | -2.46%                 | -0.63%                      | -0.32%                               | interpretable           |
| robustness | same_instrument_nonanchor_baseline |                  154 |                     97 |                            133 | 0.53%                               | 17.84%                                | -17.31%                 | -17.10%                            | -6.76%                               | -10.35%                | -6.16%                      | -41.05%                              | interpretable           |
| robustness | stopped_ac_anchor_baseline         |                  154 |                    115 |                            133 | 0.53%                               | -0.58%                                | 1.12%                   | -17.10%                            | -15.53%                              | -1.57%                 | -1.20%                      | 6.39%                                | interpretable           |
| train      | all_launch_direct_baseline         |                  253 |                   1126 |                            215 | -0.49%                              | -0.60%                                | 0.12%                   | -19.22%                            | -18.62%                              | -0.60%                 | -1.44%                      | -1.46%                               | interpretable           |
| train      | industry_matched_baseline          |                  253 |                    214 |                            215 | -0.49%                              | -1.86%                                | 1.37%                   | -19.22%                            | -17.45%                              | -1.77%                 | -1.15%                      | -2.21%                               | interpretable           |
| train      | matched_delay_baseline             |                  253 |                    250 |                            215 | -0.49%                              | -0.97%                                | 0.48%                   | -19.22%                            | -20.30%                              | 1.08%                  | 0.10%                       | 2.29%                                | interpretable           |
| train      | same_instrument_nonanchor_baseline |                  253 |                    218 |                            215 | -0.49%                              | 13.79%                                | -14.27%                 | -19.22%                            | -10.37%                              | -8.85%                 | -5.78%                      | -43.87%                              | interpretable           |
| train      | stopped_ac_anchor_baseline         |                  253 |                    365 |                            215 | -0.49%                              | -0.17%                                | -0.32%                  | -19.22%                            | -21.40%                              | 2.18%                  | -1.49%                      | -5.06%                               | interpretable           |
| validation | all_launch_direct_baseline         |                   99 |                    525 |                             86 | -3.31%                              | -2.26%                                | -1.05%                  | -19.12%                            | -17.58%                              | -1.54%                 | -2.13%                      | -2.33%                               | interpretable           |
| validation | industry_matched_baseline          |                   99 |                     92 |                             86 | -3.31%                              | -3.77%                                | 0.46%                   | -19.12%                            | -17.89%                              | -1.23%                 | -1.67%                      | -3.90%                               | interpretable           |
| validation | matched_delay_baseline             |                   99 |                     98 |                             86 | -3.31%                              | -1.25%                                | -2.06%                  | -19.12%                            | -18.92%                              | -0.20%                 | -0.68%                      | -5.81%                               | interpretable           |
| validation | same_instrument_nonanchor_baseline |                   99 |                     91 |                             86 | -3.31%                              | 8.97%                                 | -12.28%                 | -19.12%                            | -9.89%                               | -9.24%                 | -6.23%                      | -38.98%                              | interpretable           |
| validation | stopped_ac_anchor_baseline         |                   99 |                    141 |                             86 | -3.31%                              | -4.15%                                | 0.85%                   | -19.12%                            | -20.45%                              | 1.32%                  | -0.01%                      | 5.71%                                | interpretable           |

最关键的 matched-delay 对比：

- Train: mean diff +0.48%，p05 diff +1.08%，看起来有一点正向。
- Validation: mean diff -2.06%，p05 diff -0.20%，positive-rate diff -5.81%。
- Robustness: mean diff -1.13%，p05 diff -2.46%。

这说明 deferred recovery 不是完全没有 trigger，但作为“更好的 entry timing”失败了。matched-delay 继续更强，尤其在 robustness tail 上更明显。

### 5.6 Gate Audit

| gate_name                                     | gate_value   | threshold   | comparison   | gate_passed   | failure_status_if_failed       | gate_source_report                         |
|:----------------------------------------------|:-------------|:------------|:-------------|:--------------|:-------------------------------|:-------------------------------------------|
| validation_trigger_rate                       | 18.47%       | 10.00%      | >=           | True          | 无                             | deferred_family_trigger_decomposition.csv  |
| validation_unique_instrument_year_count       | 86           | 25          | >=           | True          | 无                             | deferred_family_trigger_decomposition.csv  |
| validation_h20_mean_diff_vs_matched_delay     | -2.06%       | 0.00%       | >            | False         | failed_gate                    | deferred_family_matched_lift.csv           |
| validation_h20_p05_diff_vs_matched_delay      | -0.20%       | -0.30%      | >=           | True          | 无                             | deferred_family_matched_lift.csv           |
| validation_h20_mae_worsening_vs_matched_delay | -0.68%       | 0.50%       | <=           | True          | 无                             | deferred_family_matched_lift.csv           |
| validation_instrument_year_positive_rate_diff | -5.81%       | 0.00%       | >=           | False         | failed_gate                    | deferred_family_matched_lift.csv           |
| robustness_h20_mean_diff_vs_matched_delay     | -1.13%       | -0.10%      | >=           | False         | failed_gate                    | deferred_family_matched_lift.csv           |
| robustness_h20_p05_diff_vs_matched_delay      | -2.46%       | -0.50%      | >=           | False         | failed_gate                    | deferred_family_matched_lift.csv           |
| robustness_trigger_not_collapsed              | 19.87%       | 9.24%       | >=           | True          | 无                             | deferred_family_trigger_decomposition.csv  |
| persistent_failure_validation_tail_share      | 2.78%        | 50.00%      | >=           | False         | failed_formula_refinement_gate | deferred_family_ac_failure_attribution.csv |
| persistent_failure_robustness_tail_share      | 2.44%        | 30.00%      | >=           | False         | failed_formula_refinement_gate | deferred_family_ac_failure_attribution.csv |

Gate 层面的失败项：

- validation H20 mean diff vs matched-delay 失败。
- validation instrument-year positive-rate diff 失败。
- robustness H20 mean diff vs matched-delay 失败。
- robustness H20 p05 diff vs matched-delay 失败。
- persistent-failure attribution 两个 gate 都失败。

通过项只有 trigger、breadth、validation p05、validation MAE、robustness trigger-not-collapsed。也就是说，频率与覆盖不是主问题；真正问题仍然是 lift 与 tail。

### 5.7 A/C Failure Attribution

| split      | stopped_ac_family_id       | attribution_bucket      |   ac_event_count | ac_mean_after_cost_return_H20   | ac_p05_after_cost_return_H20   | ac_mae_mean_H20   | tail_event_share   | winner_capture_rate_50h120   | interpretation_status   |
|:-----------|:---------------------------|:------------------------|-----------------:|:--------------------------------|:-------------------------------|:------------------|:-------------------|:-----------------------------|:------------------------|
| robustness | pullback_hold_restrengthen | clean_avoidance         |                3 | -1.82%                          | -11.53%                        | -10.02%           | 0.00%              | 0.00%                        | too_sparse              |
| robustness | pullback_hold_restrengthen | no_deferred_match       |                8 | 0.72%                           | -7.88%                         | -7.55%            | 0.00%              | 0.00%                        | too_sparse              |
| robustness | pullback_hold_restrengthen | persistent_failure      |               41 | 0.04%                           | -12.55%                        | -7.38%            | 4.88%              | 17.07%                       | interpretable           |
| robustness | pullback_hold_restrengthen | recovered_after_failure |                5 | -5.53%                          | -16.18%                        | -11.25%           | 20.00%             | 0.00%                        | too_sparse              |
| robustness | second_breakout            | clean_avoidance         |               14 | 4.67%                           | -6.35%                         | -7.29%            | 0.00%              | 14.29%                       | too_sparse              |
| robustness | second_breakout            | no_deferred_match       |                2 | 2.02%                           | -7.49%                         | -5.42%            | 0.00%              | 0.00%                        | too_sparse              |
| robustness | second_breakout            | persistent_failure      |               16 | -1.99%                          | -14.15%                        | -10.50%           | 0.00%              | 6.25%                        | too_sparse              |
| robustness | second_breakout            | recovered_after_failure |               26 | -3.05%                          | -15.79%                        | -10.30%           | 11.54%             | 3.85%                        | interpretable           |
| validation | pullback_hold_restrengthen | clean_avoidance         |                1 | 32.27%                          | 32.27%                         | -6.49%            | 0.00%              | 0.00%                        | too_sparse              |
| validation | pullback_hold_restrengthen | no_deferred_match       |               17 | -4.13%                          | -21.07%                        | -11.73%           | 5.88%              | 5.88%                        | too_sparse              |
| validation | pullback_hold_restrengthen | persistent_failure      |               54 | -7.45%                          | -20.53%                        | -12.44%           | 5.56%              | 1.85%                        | interpretable           |
| validation | pullback_hold_restrengthen | recovered_after_failure |                5 | -2.36%                          | -14.18%                        | -10.68%           | 0.00%              | 0.00%                        | too_sparse              |
| validation | second_breakout            | clean_avoidance         |               15 | -5.74%                          | -16.76%                        | -9.18%            | 6.67%              | 6.67%                        | too_sparse              |
| validation | second_breakout            | no_deferred_match       |                1 | -10.01%                         | -10.01%                        | -20.02%           | 0.00%              | 0.00%                        | too_sparse              |
| validation | second_breakout            | persistent_failure      |                9 | -0.06%                          | -11.89%                        | -9.22%            | 0.00%              | 22.22%                       | too_sparse              |
| validation | second_breakout            | recovered_after_failure |               39 | -0.95%                          | -18.02%                        | -10.06%           | 7.69%              | 12.82%                       | interpretable           |

Persistent failure attribution 没有证明 deferred family 能解释 A/C 的 tail：

- validation persistent failure tail share 只有 2.78%，远低于 50% gate。
- robustness persistent failure tail share 只有 2.44%，远低于 30% gate。
- 这意味着 A/C 的坏 trade 不能主要归因于我们定义的 persistent failed-lookalike 状态。

### 5.8 Train-only Recovery Delay Freeze

| lookalike_source_family   | bin_edges   |   train_source_row_count | freeze_status   |
|:--------------------------|:------------|-------------------------:|:----------------|
| A-like                    | [10.0]      |                       20 | derived         |
| C-like                    | [3.0]       |                      233 | derived         |

A-like 的 train recovery delay median 是 10 天，但 train source rows 只有 20，刚到最低边界；C-like 的 median 是 3 天，source rows 233，更稳定。

## 6. 联合发现

### 6.1 A/C 不是一个值得继续修补的 anchor family

P0 和 P0.5 已经一致说明：A/C 在 winner lifecycle 中可见，但 forward audit 没有稳定 edge。P0.5 没有找到可冻结 partition，也没有找到公式 repair 的证据。本次 deferred-family audit 再次验证：就算从 A/C 的失败状态里构造 recovery，也无法稳定打赢 matched-delay baseline。

### 6.2 Trigger scarcity 不是唯一问题，也不是最核心问题

Deferred-family validation trigger rate 达到 18.47%，robustness 达到 19.87%，这已经比 P0 A/C 的部分 trigger 情况更接近可用。但 lift 仍然失败，所以“多找一些触发”不是解法。

### 6.3 C-like 比 A-like 更有结构，但仍不足以继续

C-like recovery 是 deferred-family 事件的主要来源：validation 90 个，robustness 148 个。A-like validation 只有 9 个，robustness 只有 6 个。即使只看 C-like 方向，整体 matched-delay lift 仍然没有过关。

### 6.4 matched-delay baseline 是当前最强反证

matched-delay 的含义是：如果这个形态真的是 anchor，那么不应只是“晚几天买”更好。但实际 validation/robustness 都显示 matched-delay 更强。这个结果直接削弱了“recovery transition 是有效 entry anchor”的解释。

### 6.5 Persistent failed-lookalike 没有解释 A/C tail

如果 failed-lookalike avoidance 是正确方向，那么 A/C 的尾部亏损应该大量集中在 persistent_failure。实际只有 2%-3% 左右，远低于 gate。这说明我们定义的 failure-lookalike 状态不是 A/C tail 的主要解释变量。

## 7. 我的判断

我不建议继续沿着 A/C 或 failed-lookalike_avoidance 做 P0.6。当前证据链已经比较完整：

1. P0：A/C lifecycle 可见，但 executable forward audit 失败。
2. P0.5：A/C 失败不是简单公式/窗口/EP2 reference 问题，而是 lift 与 tail 问题。
3. Deferred-family：从 A/C failed-lookalike 中构造 recovery，trigger 有改善，但 matched-delay lift 与 robustness tail 仍失败。

因此，合理动作是停止这条 family-repair 路线。如果 EP3 还要继续，下一步不应是对 A/C 做更细分桶，也不应继续围绕 failed-lookalike recovery 调条件；应该重新定义一个不依赖 A/C 形态的 winner formation source，或者回到更早的 lifecycle profiling 里寻找完全不同的 observable anchor。

## 8. 直接结论

| Scope | Decision | Reason |
| --- | --- | --- |
| A/C primary families | stop | P0/P0.5 matched-delay lift 与 tail 失败 |
| failed_lookalike_avoidance deferred family | stop | trigger 足够接近，但 validation/robustness lift 失败，persistent-failure attribution 失败 |
| P0.6 freeze/refinement | no-go | 没有 validation-positive 且 robustness-not-collapsed 的可靠 family 证据 |
| P1 validation | no-go | 当前没有可提交到 P1 的 anchor family |
