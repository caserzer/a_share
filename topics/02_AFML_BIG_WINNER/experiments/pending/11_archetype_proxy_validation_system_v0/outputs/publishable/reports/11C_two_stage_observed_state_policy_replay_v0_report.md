# 11C Two-stage Observed-state Policy Replay Report

## 结论

- final_status: `11C_two_stage_policy_statistics_incomplete`
- replay_internal_status: `11C_two_stage_policy_not_supported_diagnostic`
- reason_list: `11B_statistics_incomplete:risk_on_pre_pit_retention_recon_diff_gt_ceiling`
- selected_arm_variant_id: `B2_wait_confirm_K3__S1_reclaim_damage__target_1.00`
- selected_state_id: `S1_reclaim_damage`
- lane_b_rescue_status: `lane_b_rescue_readout_only_low_power`

本轮 11C 完成了 after-cost / capacity-constrained two-stage observed-state replay，但当前 11B 上游为 `11B_archetype_protected_retention_statistics_incomplete`，所以 11C 按需求被 ceiling 到 `11C_two_stage_policy_statistics_incomplete`。这不是 K3 replay 无法运行，而是 11B retention prerequisite 尚不能给出正式非歧视/歧视定性。

## 详细发现与研究洞察

### 1. 主 replay 结论：K3 wait-confirm 改善 failure exposure，但没有形成可支持策略

在 base_cost、primary capacity = 50、全体 Lane A ∪ Lane B composite 口径下，selected arm `B2_wait_confirm_K3__S1_reclaim_damage__target_1.00` 相对 B0 的主要变化如下：

| metric | B0 current baseline | B2 selected | delta / readout |
| --- | ---: | ---: | ---: |
| entry_filled_n | 971 | 740 | -231 |
| entry_rate | 0.2236 | 0.1704 | -0.0532 |
| net_median_return | -0.0970 | -0.0964 | +0.0006 |
| net_winsorized_mean_return | -0.0415 | -0.0328 | +0.0087 |
| net_EV_per_exposure_day | -0.000678 | -0.000554 | +0.000124 |
| winner_120_capture_rate | 0.2390 | 0.1951 | -0.0439 |
| winner_120_captured_n | 98 | 80 | -18 |
| big_failure_proxy_entry_rate | 0.0764 | 0.0433 | -0.0332 |
| false_repair_entry_rate | 0.0797 | 0.0454 | -0.0343 |
| fast_fail_realized_loss_rate | 0.9726 | 0.9697 | -0.0029 |
| turnover_notional | 38.2504 | 29.2556 | -8.9948 |
| cash_drag_mean | 0.5415 | 0.6663 | +0.1248 |
| board_concentration_hhi | 0.5024 | 0.5131 | +0.0108 |

Interpretation:

- K3 wait-confirm 确实在“少进坏样本”上有信号：big_failure / false_repair entry rate 下降约 3.3-3.4 个百分点，turnover 下降约 23.5%。
- 但它同时少捕获 18 个 winner，winner capture 从 23.90% 降到 19.51%。这个损失没有被 net EV 的小幅改善充分抵消。
- 全样本 EV/exposure-day 仍为负值，且 train split 的 lift 为负，所以不能把它解释成可执行策略改善。
- cash drag 从 54.15% 升到 66.63%，说明 observation-first 的收益改善主要来自“少交易、少暴露”，而不是单位风险收益显著增强。

### 2. Split 稳定性：robustness 看起来较好，但 train 不支持

| split | B0 net_EV/day | B2 net_EV/day | lift | B0 winner_capture | B2 winner_capture | B0 big_failure_rate | B2 big_failure_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | -0.000867 | -0.001064 | -0.000196 | 0.3955 | 0.2388 | 0.0963 | 0.0576 |
| validation | -0.000991 | -0.001003 | -0.000012 | 0.2000 | 0.4000 | 0.0976 | 0.0427 |
| robustness | -0.000192 | 0.000261 | +0.000453 | 0.1609 | 0.1609 | 0.0514 | 0.0319 |

Interpretation:

- robustness split 给出正向 EV lift，且 failure exposure 明显下降。
- train split 是主要否决点：EV lift 为 -0.000196，winner capture 大幅下降，`winner_capture_gate_ok = False`。
- validation winner 数只有 16，当前 positive readout 不能作为强 OOS 证据，只能作为低功率观察。

### 3. 成本敏感性：失败不是单纯交易成本造成的

| cost_scenario | B0 net_EV/day | B2 net_EV/day | lift | B0 turnover | B2 turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| zero_cost | -0.000635 | -0.000509 | +0.000126 | 38.2504 | 29.2556 |
| base_cost | -0.000678 | -0.000554 | +0.000124 | 38.2504 | 29.2556 |
| stress_cost | -0.000717 | -0.000595 | +0.000122 | 38.2504 | 29.2556 |

Interpretation:

- selected arm 在 zero/base/stress 三档成本下的 lift 都约为 +0.00012，但绝对 EV 仍为负。
- 因此当前结论不是“gross 有效、成本吃掉收益”，而是：等待确认降低了损失率和交易量，但没有把组合推到正 EV。

### 4. Capacity sensitivity：容量越宽，selected arm 越少坏，但仍未转正

| capacity_slots | B0 entry_n | B2 entry_n | B0 net_EV/day | B2 net_EV/day | lift | B0 cash_drag | B2 cash_drag |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 407 | 401 | -0.000561 | -0.001016 | -0.000455 | 0.4970 | 0.5835 |
| 50 | 971 | 740 | -0.000678 | -0.000554 | +0.000124 | 0.5415 | 0.6663 |
| 100 | 1602 | 1149 | -0.000764 | -0.000514 | +0.000250 | 0.6116 | 0.7305 |

Interpretation:

- capacity = 20 时 selected arm 反而更差，说明 tighter capacity 下等待确认可能错过有限仓位中的较好窗口。
- capacity = 50/100 时 selected arm 相对 B0 更好，但仍为负 EV，且 cash drag 继续升高。
- 这更像“减少暴露带来的风险压缩”，不是强 alpha 转化。

### 5. Trial sizing：小仓试探没有价值，主要是在提前买入坏样本

在 selected state `S1_reclaim_damage`、target = 1.00 下：

| arm | split | entry_n | net_EV/day | winner_capture | big_failure_rate | false_repair_rate | turnover |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B2 wait-confirm | all | 740 | -0.000554 | 0.1951 | 0.0433 | 0.0454 | 29.2556 |
| B3 trial 0% | all | 740 | -0.000554 | 0.1951 | 0.0433 | 0.0454 | 29.2556 |
| B3 trial 10% | all | 2842 | -0.000712 | 0.6122 | 0.2316 | 0.2316 | 35.8103 |
| B3 trial 25% | all | 2369 | -0.000920 | 0.5341 | 0.1957 | 0.1966 | 43.7141 |
| B2 wait-confirm | train | 329 | -0.001064 | 0.2388 | 0.0576 | 0.0602 | 12.8682 |
| B3 trial 10% | train | 1170 | -0.001282 | 0.8060 | 0.2692 | 0.2768 | 15.4660 |
| B3 trial 25% | train | 1034 | -0.001321 | 0.7687 | 0.2331 | 0.2407 | 19.2177 |

Interpretation:

- `trial_size = 0%` 与 B2 完全等价，符合预注册。
- 10%/25% trial 会显著提高 winner capture，但更大幅度提高 big_failure / false_repair exposure。
- 这说明“小仓试探”并没有提供有效信息优势；它只是把 K3 前无法区分的 bad path 提前买进来。
- 当前 11C 更支持 observation-first，而不是 staged sizing。

### 6. Lane B rescue：有研究价值，但 power 不足，不能进入 policy conclusion

Lane B 是 10C reference-slice rejected candidates；本轮只允许 delayed-confirmation rescue readout。

| split | arm | entry_n | net_EV/day | winner_capture | winner_n_captured / denominator | big_failure_rate | false_repair_rate | turnover |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | B0 lane-B carry | 100 | -0.005543 | 0.2097 | 13 / 62 | 0.1879 | 0.2182 | 3.8091 |
| all | LB2 delayed rescue | 73 | -0.001087 | 0.2903 | 18 / 62 | 0.0788 | 0.0848 | 2.8820 |
| train | B0 lane-B carry | 36 | -0.007659 | 0.6667 | 4 / 6 | 0.2609 | 0.2935 | 1.3696 |
| train | LB2 delayed rescue | 21 | -0.004357 | 0.1667 | 1 / 6 | 0.1196 | 0.1196 | 0.7986 |
| robustness | B0 lane-B carry | 46 | -0.006568 | 0.1633 | 8 / 49 | 0.1467 | 0.1848 | 1.7483 |
| robustness | LB2 delayed rescue | 37 | 0.001068 | 0.2653 | 13 / 49 | 0.0598 | 0.0707 | 1.5032 |

Interpretation:

- Lane B 的 all / robustness readout 很有意思：LB2 比 Lane-B B0 carry 更低 failure exposure、更高 winner capture，并且 robustness EV 转正。
- 但 train 只有 21 个 state-positive entries、1 个 winner，低于 100 entries / 20 winners 的 floor；robustness 也只有 37 entries，低于 50 entries floor。
- 因此 Lane B 当前只能作为 future research readout。它提示“被 10C 拒绝后路径自证”可能是一个新事件类型，但本轮不能据此改变 t0 gate。

### 7. Top-k 与 bootstrap：结果不够稳健

| split | bootstrap CI p05 | bootstrap median | bootstrap CI p95 | top1_share | top5_share | top-k status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| train | -0.000591 | -0.000191 | 0.000181 | 0.1612 | 0.6352 | topk_dependent |
| validation | -0.000559 | -0.000005 | 0.000492 | n/a | n/a | validation_low_power |
| robustness | -0.000173 | 0.000446 | 0.001090 | 0.1299 | 0.5447 | ok |

Interpretation:

- train 的 instrument-block bootstrap CI 横跨 0，median 也为负；即使 raw total net PnL lift 为正，也不够稳。
- train top5 contribution share = 63.52%，超过 60% ceiling，触发 top-k dependency。
- robustness bootstrap 较好，但 top10 removal 后 EV lift 变成 -0.000457，说明 robustness 也不是完全免疫于头部 instrument 贡献。

### 8. 综合判断

本轮 11C 的核心发现不是“策略可用了”，而是：

- K3 observed state 可以把 failure exposure 压下来；
- wait-confirm 比 trial-entry 更干净；
- Lane B delayed rescue 有研究信号；
- 但 winner capture、train robustness、top-k sensitivity、11B upstream ceiling 都不足以支持 policy positive。

因此当前最稳妥的后续方向是：先把 11B retention frontier 的 statistics_incomplete 问题解决，再把 Lane B rescue 作为单独的 observed-state event 继续扩大样本和做 power audit；主策略侧则优先研究 observation-first，而不是 small trial entry。

## 运行命令与复现边界

- actual_command: `topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/src/run_11c_two_stage_observed_state_policy_replay.py --config topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/configs/config_11c_two_stage_observed_state_policy_replay.yaml`
- 主回放使用 `exit_contract_id = common_exit_120d_with_risk_stop_v1`：120 sessions horizon、risk stop from current weighted-average cost basis、delist haircut primary = 1.0。
- B0/B1/B2/B3/LB2 使用同一 exit contract；B1 只作为 B0 timing sanity check，不提供独立 policy 结论。

## Scope Reconciliation

主分母固定为 11A1/11A2/11B 的 `risk_on ∩ strict PIT-valid` universe。`all` split 中 10A risk_on pre-PIT 为 11,293 行，PIT-valid 为 4,665 行，因此 6,628 行 PIT-excluded rows 保持 out-of-scope，不混回当前可执行 universe。

| split      |   eleven_a1_risk_on_pre_pit_row_n |   eleven_a1_pit_valid_row_n |   pit_excluded_row_n |   eleven_c_pit_valid_row_n | denominator_row_match_flag   | scope_reconciliation_status   |
|:-----------|----------------------------------:|----------------------------:|---------------------:|---------------------------:|:-----------------------------|:------------------------------|
| all        |                             11293 |                        4665 |                 6628 |                       4665 | True                         | ok                            |
| train      |                              5836 |                        1708 |                 4128 |                       1708 | True                         | ok                            |
| validation |                              1898 |                         865 |                 1033 |                        865 | True                         | ok                            |
| robustness |                              3559 |                        2092 |                 1467 |                       2092 | True                         | ok                            |

## 11A2 Prerequisite

11A2 只授权 `K*=3` 的 post-t0 observed-state 诊断窗口；11C 不改变 t0 的 10C reference-slice 边界，仅在 `separation_detected_tradable`、K*=3、tradable window open 同时成立时做 replay。

| final_status                                                        |   pit_valid_evaluated_row_n |   unique_instrument_n |   confirmed_divergence_onset_day_C1_full_cohort | winner_realized_fraction_status   |
|:--------------------------------------------------------------------|----------------------------:|----------------------:|------------------------------------------------:|:----------------------------------|
| 11A2_post_t0_archetype_path_divergence_separation_detected_tradable |                        4665 |                   593 |                                               3 | tradable_window_open              |

11A2 divergence/tradability readout:

| contrast_id                    | cohort      |   confirmed_divergence_onset_day | return_direction_at_confirmed   | structure_direction_at_confirmed   | dual_channel_collinearity_flag   |
|:-------------------------------|:------------|---------------------------------:|:--------------------------------|:-----------------------------------|:---------------------------------|
| C1_winner_vs_big_failure_proxy | full_cohort |                                3 | winner_higher                   | winner_higher                      | dual_channel_collinear_readout   |
| C2_winner_vs_false_repair_only | full_cohort |                                3 | winner_higher                   | winner_higher                      | dual_channel_collinear_readout   |
| C3_winner_vs_fast_fail         | full_cohort |                                5 | winner_higher                   | winner_higher                      | dual_channel_collinear_readout   |
| C4_winner_vs_neutral           | full_cohort |                              nan | undetermined                    | undetermined                       | not_collinear                    |
| C5_winner_vs_all_nonwinner     | full_cohort |                              nan | undetermined                    | undetermined                       | not_collinear                    |

| contrast_id                    | cohort      |   confirmed_divergence_onset_day |   tradability_basis_eligible_n |   tradability_basis_excluded_n | winner_realized_fraction_status   |
|:-------------------------------|:------------|---------------------------------:|-------------------------------:|-------------------------------:|:----------------------------------|
| C1_winner_vs_big_failure_proxy | full_cohort |                                3 |                            414 |                             32 | tradable_window_open              |

## 11B 上游检查

- 11B final_status: `11B_archetype_protected_retention_statistics_incomplete`
- statistics_incomplete_reasons: `risk_on_pre_pit_retention_recon_diff_gt_ceiling`
- PIT-valid winner/nonwinner/relative retention: 0.8475 / 0.9274 / 0.9138

11B split readout:

| split      |   winner_n |   winner_retention |   nonwinner_retention |   relative_retention_winner_vs_nonwinner | split_retention_status   |
|:-----------|-----------:|-------------------:|----------------------:|-----------------------------------------:|:-------------------------|
| all        |        446 |           0.847534 |              0.927437 |                                 0.913845 | readout_only             |
| train      |        151 |           0.960265 |              0.938343 |                                 1.02336  | non_discriminatory       |
| validation |         16 |           0.5625   |              0.937574 |                                 0.599953 | validation_low_power     |
| robustness |        279 |           0.802867 |              0.913308 |                                 0.879077 | ambiguous                |

11B frontier reconciliation:

| comparison_scope    | split      |   b_recomputed_winner_n |   b_recomputed_winner_retention |   c10c_published_winner_retention |   winner_retention_abs_diff | retention_reconciliation_status          |
|:--------------------|:-----------|------------------------:|--------------------------------:|----------------------------------:|----------------------------:|:-----------------------------------------|
| score_cache_primary | train      |                    1491 |                        0.896043 |                          0.896043 |                 0           | ok                                       |
| score_cache_primary | validation |                     161 |                        0.757764 |                          0.757764 |                 0           | ok                                       |
| score_cache_primary | robustness |                     995 |                        0.871357 |                          0.871357 |                 1.11022e-16 | ok                                       |
| risk_on_pre_pit     | train      |                     669 |                        0.835575 |                          0.896043 |                 0.0604674   | retention_reconciliation_diff_gt_ceiling |
| risk_on_pre_pit     | validation |                      57 |                        0.578947 |                          0.757764 |                 0.178817    | retention_reconciliation_diff_gt_ceiling |
| risk_on_pre_pit     | robustness |                     498 |                        0.799197 |                          0.871357 |                 0.07216     | retention_reconciliation_diff_gt_ceiling |

`winner_shakeout_seed` sensitivity:

| split      |   eligible_n |   retention_rate |   relative_retention_vs_nonwinner |   relative_retention_ci_low_p05 |   relative_retention_ci_high_p95 | subgroup_status       |
|:-----------|-------------:|-----------------:|----------------------------------:|--------------------------------:|---------------------------------:|:----------------------|
| all        |           97 |         0.690722 |                          0.744764 |                        0.656397 |                         0.838108 | ok                    |
| train      |           23 |         0.956522 |                          1.01937  |                        0.932584 |                         1.07464  | subgroup_underpowered |
| validation |            3 |         0        |                          0        |                        0        |                         0        | subgroup_underpowered |
| robustness |           71 |         0.633803 |                          0.693964 |                        0.591853 |                         0.798276 | ok                    |

## Lane Population

Lane A 是 10C reference-slice kept candidates；Lane B 是 10C reference-slice rejected candidates，但 10C 在 t0 仍有效，Lane B 只能做 delayed-confirmation rescue readout。B0/B1 覆盖 deployed baseline kept set，即 Lane A ∪ Lane B。

| split      | lane_id                  |   row_n |   winner_n | tenc_slice_mode           | tenc_slice_selected_flag   | tenc_slice_decision_block_reason   |   tenb_join_hit_rate |   tenc_ref_join_hit_rate |
|:-----------|:-------------------------|--------:|-----------:|:--------------------------|:---------------------------|:-----------------------------------|---------------------:|-------------------------:|
| all        | all                      |    4665 |        446 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| all        | lane_A_10C_ref_kept      |    4013 |        348 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| all        | lane_B_10C_ref_rejected  |     330 |         62 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| all        | out_of_lane_10B_rejected |     322 |         36 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| train      | all                      |    1708 |        151 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| train      | lane_A_10C_ref_kept      |    1487 |        128 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| train      | lane_B_10C_ref_rejected  |      92 |          6 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| train      | out_of_lane_10B_rejected |     129 |         17 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| validation | all                      |     865 |         16 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| validation | lane_A_10C_ref_kept      |     766 |          8 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| validation | lane_B_10C_ref_rejected  |      54 |          7 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| validation | out_of_lane_10B_rejected |      45 |          1 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| robustness | all                      |    2092 |        279 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| robustness | lane_A_10C_ref_kept      |    1760 |        212 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| robustness | lane_B_10C_ref_rejected  |     184 |         49 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |
| robustness | out_of_lane_10B_rejected |     148 |         18 | keep_9000_reference_slice | False                      | not_selected                       |                    1 |                        1 |

## K3 Observed-state Registry And Leakage Audit

Primary observed-state 只允许 K3 return/path damage/reclaim/liquidity/executable status。`fast_fail touch`、future MFE/MAE、`winner_120`、`forward_return_120d` 和 label-derived barrier fields 只允许 readout-only 或 forbidden。

Feature registry summary:

| registry_status                | primary_policy_allowed_flag   |   feature_n |
|:-------------------------------|:------------------------------|------------:|
| forbidden                      | False                         |           3 |
| primary_allowed                | True                          |          11 |
| readout_only_forbidden_primary | False                         |           3 |

Selected state definition:

| state_id          | formula                                                                                                            |
|:------------------|:-------------------------------------------------------------------------------------------------------------------|
| S1_reclaim_damage | ep_close_vs_t0_close_at_3 >= 0 AND ep_breach_t0_low_through_3_flag == false AND entry_t0p4_executable_flag == true |

Label-overlap policy audit summary:

| label_overlap_audit_status   | entered_policy_routing_flag   |   feature_or_state_n |
|:-----------------------------|:------------------------------|---------------------:|
| ok                           | False                         |                    6 |
| ok                           | True                          |                   14 |

## Policy Arm Registry

| arm_id                   | arm_variant_id                                                            | state_id                    |   trial_size |   upgrade_size | upgrade_size_semantics     | trial_zero_wait_confirm_equivalence_flag   | b0_b1_deployed_set_identical_flag   | b2_b3_composite_candidate_set_flag   |
|:-------------------------|:--------------------------------------------------------------------------|:----------------------------|-------------:|---------------:|:---------------------------|:-------------------------------------------|:------------------------------------|:-------------------------------------|
| B0_deployed_baseline     | B0_deployed_baseline__full                                                |                             |         0    |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B1_immediate_full_entry  | B1_immediate_full_entry__full                                             |                             |         0    |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S0_return_damage_basic__target_0.50                   | S0_return_damage_basic      |         0    |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S0_return_damage_basic__target_1.00                   | S0_return_damage_basic      |         0    |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.00__target_0.50 | S0_return_damage_basic      |         0    |            0.5 | target_total_position_size | True                                       | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.00__target_1.00 | S0_return_damage_basic      |         0    |            1   | target_total_position_size | True                                       | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.10__target_0.50 | S0_return_damage_basic      |         0.1  |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.10__target_1.00 | S0_return_damage_basic      |         0.1  |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.25__target_0.50 | S0_return_damage_basic      |         0.25 |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.25__target_1.00 | S0_return_damage_basic      |         0.25 |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S1_reclaim_damage__target_0.50                        | S1_reclaim_damage           |         0    |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S1_reclaim_damage__target_1.00                        | S1_reclaim_damage           |         0    |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_0.50      | S1_reclaim_damage           |         0    |            0.5 | target_total_position_size | True                                       | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_1.00      | S1_reclaim_damage           |         0    |            1   | target_total_position_size | True                                       | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.10__target_0.50      | S1_reclaim_damage           |         0.1  |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.10__target_1.00      | S1_reclaim_damage           |         0.1  |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.25__target_0.50      | S1_reclaim_damage           |         0.25 |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.25__target_1.00      | S1_reclaim_damage           |         0.25 |            1   | target_total_position_size | False                                      | True                                | True                                 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S2_return_reclaim_liquidity__target_0.50              | S2_return_reclaim_liquidity |         0    |            0.5 | target_total_position_size | False                                      | True                                | True                                 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S2_return_reclaim_liquidity__target_1.00              | S2_return_reclaim_liquidity |         0    |            1   | target_total_position_size | False                                      | True                                | True                                 |

## Primary Replay Readout

- B0 net EV/exposure-day: -0.000678
- selected net EV/exposure-day: -0.000554
- selected winner capture rate: 0.1951
- selected big failure entry rate: 0.0433
- selected false repair entry rate: 0.0454
- selected limit-up unfilled rate: 0.0000
- selected limit-down exit failure rate: 0.0006

B0/B1/B2/B3/LB0/LB2 primary-capacity cost readout excerpt:

| arm_id                   | arm_variant_id                                                       | lane_id                 | cost_scenario           |   entry_filled_n |   net_median_return |   net_winsorized_mean_return_1_99 |   net_ev_per_exposure_day |   winner_120_capture_rate |   big_failure_proxy_entry_rate |   false_repair_entry_rate |   turnover_notional |   transaction_cost_bps_paid |
|:-------------------------|:---------------------------------------------------------------------|:------------------------|:------------------------|-----------------:|--------------------:|----------------------------------:|--------------------------:|--------------------------:|-------------------------------:|--------------------------:|--------------------:|----------------------------:|
| B0_deployed_baseline     | B0_deployed_baseline__full                                           | all                     | base_cost               |              971 |         -0.0970178  |                        -0.0415282 |              -0.000677858 |                  0.239024 |                      0.0764449 |                 0.0796684 |            38.2504  |                     10.4615 |
| B1_immediate_full_entry  | B1_immediate_full_entry__full                                        | all                     | base_cost               |              971 |         -0.0970178  |                        -0.0415282 |              -0.000677858 |                  0.239024 |                      0.0764449 |                 0.0796684 |            38.2504  |                     10.4615 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S1_reclaim_damage__target_1.00                   | all                     | base_cost               |              740 |         -0.0964473  |                        -0.0327879 |              -0.000554331 |                  0.195122 |                      0.043288  |                 0.0453603 |            29.2556  |                     10.4706 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_1.00 | all                     | base_cost               |              740 |         -0.0964473  |                        -0.0327879 |              -0.000554331 |                  0.195122 |                      0.043288  |                 0.0453603 |            29.2556  |                     10.4706 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.10__target_1.00 | all                     | base_cost               |             2842 |         -0.00308458 |                        -0.0147832 |              -0.000712353 |                  0.612195 |                      0.231637  |                 0.231637  |            35.8103  |                     10.4697 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.25__target_1.00 | all                     | base_cost               |             2369 |         -0.00834614 |                        -0.019531  |              -0.000920406 |                  0.534146 |                      0.195717  |                 0.196638  |            43.7141  |                     10.4665 |
| LB0_rejected_no_trade    | LB0_rejected_no_trade__S1_reclaim_damage                             | lane_B_10C_ref_rejected | base_cost               |                0 |        nan          |                       nan         |             nan           |                  0        |                      0         |                 0         |             0       |                      0      |
| LB2_delayed_rescue_K3    | LB2_delayed_rescue_K3__S1_reclaim_damage__target_1.00                | lane_B_10C_ref_rejected | base_cost               |               73 |         -0.0974132  |                        -0.0381714 |              -0.00108662  |                  0.290323 |                      0.0787879 |                 0.0848485 |             2.88196 |                     10.467  |
| B0_deployed_baseline     | B0_deployed_baseline__full                                           | all                     | stress_cost             |              971 |         -0.0988037  |                        -0.0433808 |              -0.00071682  |                  0.239024 |                      0.0764449 |                 0.0796684 |            38.2504  |                     19.9229 |
| B1_immediate_full_entry  | B1_immediate_full_entry__full                                        | all                     | stress_cost             |              971 |         -0.0988037  |                        -0.0433808 |              -0.00071682  |                  0.239024 |                      0.0764449 |                 0.0796684 |            38.2504  |                     19.9229 |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S1_reclaim_damage__target_1.00                   | all                     | stress_cost             |              740 |         -0.0982339  |                        -0.0346511 |              -0.000595285 |                  0.195122 |                      0.043288  |                 0.0453603 |            29.2556  |                     19.9411 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_1.00 | all                     | stress_cost             |              740 |         -0.0982339  |                        -0.0346511 |              -0.000595285 |                  0.195122 |                      0.043288  |                 0.0453603 |            29.2556  |                     19.9411 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.10__target_1.00 | all                     | stress_cost             |             2842 |         -0.00327152 |                        -0.0153721 |              -0.000763625 |                  0.612195 |                      0.231637  |                 0.231637  |            35.8103  |                     19.9395 |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.25__target_1.00 | all                     | stress_cost             |             2369 |         -0.00881824 |                        -0.0203969 |              -0.000980705 |                  0.534146 |                      0.195717  |                 0.196638  |            43.7141  |                     19.933  |
| LB0_rejected_no_trade    | LB0_rejected_no_trade__S1_reclaim_damage                             | lane_B_10C_ref_rejected | stress_cost             |                0 |        nan          |                       nan         |             nan           |                  0        |                      0         |                 0         |             0       |                      0      |
| LB2_delayed_rescue_K3    | LB2_delayed_rescue_K3__S1_reclaim_damage__target_1.00                | lane_B_10C_ref_rejected | stress_cost             |               73 |         -0.0991987  |                        -0.0400281 |              -0.00115883  |                  0.290323 |                      0.0787879 |                 0.0848485 |             2.88196 |                     19.934  |
| B0_deployed_baseline     | B0_deployed_baseline__full                                           | all                     | zero_cost_decomposition |              971 |         -0.0950413  |                        -0.0394795 |              -0.000634779 |                  0.239024 |                      0.0764449 |                 0.0796684 |            38.2504  |                      0      |
| B1_immediate_full_entry  | B1_immediate_full_entry__full                                        | all                     | zero_cost_decomposition |              971 |         -0.0950413  |                        -0.0394795 |              -0.000634779 |                  0.239024 |                      0.0764449 |                 0.0796684 |            38.2504  |                      0      |
| B2_wait_confirm_K3       | B2_wait_confirm_K3__S1_reclaim_damage__target_1.00                   | all                     | zero_cost_decomposition |              740 |         -0.0944701  |                        -0.0307279 |              -0.000509053 |                  0.195122 |                      0.043288  |                 0.0453603 |            29.2556  |                      0      |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_1.00 | all                     | zero_cost_decomposition |              740 |         -0.0944701  |                        -0.0307279 |              -0.000509053 |                  0.195122 |                      0.043288  |                 0.0453603 |            29.2556  |                      0      |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.10__target_1.00 | all                     | zero_cost_decomposition |             2842 |         -0.00287372 |                        -0.0141321 |              -0.000655667 |                  0.612195 |                      0.231637  |                 0.231637  |            35.8103  |                      0      |
| B3_trial_then_upgrade_K3 | B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.25__target_1.00 | all                     | zero_cost_decomposition |             2369 |         -0.00783133 |                        -0.0185734 |              -0.000853736 |                  0.534146 |                      0.195717  |                 0.196638  |            43.7141  |                      0      |
| LB0_rejected_no_trade    | LB0_rejected_no_trade__S1_reclaim_damage                             | lane_B_10C_ref_rejected | zero_cost_decomposition |                0 |        nan          |                       nan         |             nan           |                  0        |                      0         |                 0         |             0       |                      0      |
| LB2_delayed_rescue_K3    | LB2_delayed_rescue_K3__S1_reclaim_damage__target_1.00                | lane_B_10C_ref_rejected | zero_cost_decomposition |               73 |         -0.0954373  |                        -0.0361184 |              -0.00100677  |                  0.290323 |                      0.0787879 |                 0.0848485 |             2.88196 |                      0      |

Event-level 与 portfolio-constrained readout:

| arm_id               | arm_variant_id                                     |   entry_filled_n |   entry_rate |   turnover_notional |   transaction_cost_bps_paid |   capital_utilization_mean |   cash_drag_mean |   max_concurrent_positions |   limit_up_unfilled_rate |   limit_down_exit_failure_rate |
|:---------------------|:---------------------------------------------------|-----------------:|-------------:|--------------------:|----------------------------:|---------------------------:|-----------------:|---------------------------:|-------------------------:|-------------------------------:|
| B0_deployed_baseline | B0_deployed_baseline__full                         |              971 |     0.223578 |             38.2504 |                     10.4615 |                   0.458453 |         0.541547 |                         40 |                        0 |                    0.00115128  |
| B2_wait_confirm_K3   | B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 |              740 |     0.170389 |             29.2556 |                     10.4706 |                   0.333699 |         0.666301 |                         40 |                        0 |                    0.000569801 |

MAE / drawdown / board concentration:

| arm_id               | arm_variant_id                                     |   mae_p50 |    mae_p95 |   max_drawdown_p95 |   board_concentration_hhi |   industry_concentration_hhi |
|:---------------------|:---------------------------------------------------|----------:|-----------:|-------------------:|--------------------------:|-----------------------------:|
| B0_deployed_baseline | B0_deployed_baseline__full                         | -0.107304 | -0.0331656 |         -0.0331656 |                  0.502381 |                          nan |
| B2_wait_confirm_K3   | B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | -0.107207 | -0.0314641 |         -0.0314641 |                  0.513148 |                          nan |

当前 report 中 sector/industry concentration 为 `NaN`，原因是 11C 输入只冻结了 board metadata，未冻结 PIT industry/sector source；因此本轮只对 board concentration 作正式 capacity readout。

## State / Arm Selection

| arm_variant_id                                                                 | arm_id                   | state_id                    |   trial_size |   upgrade_size |   state_positive_entry_n_train |   state_positive_winner_n_train |   net_ev_per_exposure_day_lift_vs_B0_train | winner_capture_gate_ok   | failure_exposure_gate_ok   | train_pre_gate_pass_flag   |   train_policy_selection_score | selected_policy_flag   | selection_status                                 |
|:-------------------------------------------------------------------------------|:-------------------------|:----------------------------|-------------:|---------------:|-------------------------------:|--------------------------------:|-------------------------------------------:|:-------------------------|:---------------------------|:---------------------------|-------------------------------:|:-----------------------|:-------------------------------------------------|
| B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_1.00           | B3_trial_then_upgrade_K3 | S1_reclaim_damage           |            0 |            1   |                            550 |                              52 |                               -0.000196489 | False                    | True                       | False                      |                   -0.000196489 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00                             | B2_wait_confirm_K3       | S1_reclaim_damage           |            0 |            1   |                            550 |                              52 |                               -0.000196489 | False                    | True                       | False                      |                   -0.000196489 | True                   | best_diagnostic_candidate_no_train_pre_gate_pass |
| B2_wait_confirm_K3__S0_return_damage_basic__target_1.00                        | B2_wait_confirm_K3       | S0_return_damage_basic      |            0 |            1   |                            667 |                              68 |                               -0.000354089 | False                    | True                       | False                      |                   -0.000354089 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.00__target_1.00      | B3_trial_then_upgrade_K3 | S0_return_damage_basic      |            0 |            1   |                            667 |                              68 |                               -0.000354089 | False                    | True                       | False                      |                   -0.000354089 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B2_wait_confirm_K3__S2_return_reclaim_liquidity__target_1.00                   | B2_wait_confirm_K3       | S2_return_reclaim_liquidity |            0 |            1   |                            421 |                              42 |                               -0.000422779 | False                    | True                       | False                      |                   -0.000422779 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B3_trial_then_upgrade_K3__S2_return_reclaim_liquidity__trial_0.00__target_1.00 | B3_trial_then_upgrade_K3 | S2_return_reclaim_liquidity |            0 |            1   |                            421 |                              42 |                               -0.000422779 | False                    | True                       | False                      |                   -0.000422779 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B3_trial_then_upgrade_K3__S1_reclaim_damage__trial_0.00__target_0.50           | B3_trial_then_upgrade_K3 | S1_reclaim_damage           |            0 |            0.5 |                            550 |                              52 |                               -0.000489831 | True                     | True                       | False                      |                   -0.000489831 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B2_wait_confirm_K3__S1_reclaim_damage__target_0.50                             | B2_wait_confirm_K3       | S1_reclaim_damage           |            0 |            0.5 |                            550 |                              52 |                               -0.000489831 | True                     | True                       | False                      |                   -0.000489831 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B3_trial_then_upgrade_K3__S0_return_damage_basic__trial_0.00__target_0.50      | B3_trial_then_upgrade_K3 | S0_return_damage_basic      |            0 |            0.5 |                            667 |                              68 |                               -0.000554455 | True                     | True                       | False                      |                   -0.000554455 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B2_wait_confirm_K3__S0_return_damage_basic__target_0.50                        | B2_wait_confirm_K3       | S0_return_damage_basic      |            0 |            0.5 |                            667 |                              68 |                               -0.000554455 | True                     | True                       | False                      |                   -0.000554455 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B3_trial_then_upgrade_K3__S2_return_reclaim_liquidity__trial_0.00__target_0.50 | B3_trial_then_upgrade_K3 | S2_return_reclaim_liquidity |            0 |            0.5 |                            421 |                              42 |                               -0.000729128 | False                    | True                       | False                      |                   -0.000729128 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |
| B2_wait_confirm_K3__S2_return_reclaim_liquidity__target_0.50                   | B2_wait_confirm_K3       | S2_return_reclaim_liquidity |            0 |            0.5 |                            421 |                              42 |                               -0.000729128 | False                    | True                       | False                      |                   -0.000729128 | False                  | best_diagnostic_candidate_no_train_pre_gate_pass |

## Top-k And Bootstrap

| arm_variant_id                                     | split      |   top_k | ranking_metric          |   removed_instrument_n |   net_ev_per_exposure_day_lift_after_removal |   top1_instrument_contribution_share |   top5_instrument_contribution_share |   top_episode_contribution_share | topk_dependency_status   |   raw_total_net_pnl_lift |
|:---------------------------------------------------|:-----------|--------:|:------------------------|-----------------------:|---------------------------------------------:|-------------------------------------:|-------------------------------------:|---------------------------------:|:-------------------------|-------------------------:|
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | train      |       1 | contribution_to_net_pnl |                      1 |                                 -0.000188065 |                             0.161228 |                             0.635214 |                        0.079964  | topk_dependent           |                0.0600391 |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | train      |       3 | contribution_to_net_pnl |                      3 |                                 -0.000301338 |                             0.161228 |                             0.635214 |                        0.079964  | topk_dependent           |                0.0600391 |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | train      |       5 | contribution_to_net_pnl |                      5 |                                 -0.000481012 |                             0.161228 |                             0.635214 |                        0.079964  | topk_dependent           |                0.0600391 |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | train      |      10 | contribution_to_net_pnl |                     10 |                                 -0.000651984 |                             0.161228 |                             0.635214 |                        0.079964  | topk_dependent           |                0.0600391 |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | robustness |       1 | contribution_to_net_pnl |                      1 |                                  0.000311824 |                             0.129932 |                             0.544732 |                        0.0986013 | ok                       |                0.123737  |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | robustness |       3 | contribution_to_net_pnl |                      3 |                                  8.27434e-05 |                             0.129932 |                             0.544732 |                        0.0986013 | ok                       |                0.123737  |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | robustness |       5 | contribution_to_net_pnl |                      5 |                                 -6.16944e-05 |                             0.129932 |                             0.544732 |                        0.0986013 | ok                       |                0.123737  |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | robustness |      10 | contribution_to_net_pnl |                     10 |                                 -0.000456559 |                             0.129932 |                             0.544732 |                        0.0986013 | ok                       |                0.123737  |

| arm_variant_id                                     | split      |   bootstrap_n | block_key   | metric                             |   resampled_instrument_n |   sample_unique_metric_n |   sample_std |       ci_low |     ci_high |       median | bootstrap_status   |
|:---------------------------------------------------|:-----------|--------------:|:------------|:-----------------------------------|-------------------------:|-------------------------:|-------------:|-------------:|------------:|-------------:|:-------------------|
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | train      |          1000 | instrument  | net_ev_per_exposure_day_lift_vs_B0 |                      317 |                     1000 |  0.000244736 | -0.000591433 | 0.000181286 | -0.000190825 | ok                 |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | validation |          1000 | instrument  | net_ev_per_exposure_day_lift_vs_B0 |                      294 |                     1000 |  0.000323593 | -0.000558695 | 0.000492459 | -5.32864e-06 | ok                 |
| B2_wait_confirm_K3__S1_reclaim_damage__target_1.00 | robustness |          1000 | instrument  | net_ev_per_exposure_day_lift_vs_B0 |                      451 |                     1000 |  0.000375071 | -0.000172916 | 0.00108951  |  0.00044641  | ok                 |

## Lane B Rescue Power

| split      | selected_state_id   |   lane_B_state_positive_entry_n |   lane_B_state_positive_winner_n |   entry_floor |   winner_floor | power_pass_flag   | lane_b_rescue_status                 |
|:-----------|:--------------------|--------------------------------:|---------------------------------:|--------------:|---------------:|:------------------|:-------------------------------------|
| train      | S1_reclaim_damage   |                              21 |                                1 |           100 |             20 | False             | lane_b_rescue_readout_only_low_power |
| robustness | S1_reclaim_damage   |                              37 |                               13 |            50 |             10 | False             | lane_b_rescue_readout_only_low_power |

## 预注册失败模式

| case | status | conclusion |
| --- | --- | --- |
| Case 1 gross-only | readout | 若 zero-cost 有效但 base-cost 无效，则 separability 不可交易 |
| Case 2 top-k | see topk table | top-k dependency 不支持 policy |
| Case 3 failure exposure | see failure exposure metrics | failure exposure 恶化则不支持 |
| Case 4 Lane A only | readout | 只允许 upgrade/hold，不允许 Lane B rescue conclusion |
| Case 5 Lane B low power | see lane_b table | 只允许 readout，不授权交易 |
| Case 6 wait-confirm preferred | readout | observation-first 优先 |
| Case 7 trial-entry preferred | readout | staged sizing candidate 仍需成本/容量/涨跌停复核 |
| Case 8 11B statistics_incomplete | triggered | 11C 可输出 replay readout，但最终不得 positive |

## 措辞边界

本报告不改变 t0 的 10C reference-slice 边界；Lane B 只作为 delayed-confirmation rescue readout。
