# 18D Payoff-state Feature Representation Diagnostic Report

## 结论摘要

18D 的诊断结论是：

- `decision_state = 18D_feature_representation_refresh_supported`
- `next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md`
- `all_hard_gates_pass = True`
- 推荐进入 18E 刷新的候选族为 `M1|M3|M5|M2`
- 暂缓或仅 appendix 的候选族为 `M4`

这仍然是 feature representation 诊断，不是 policy 结论。18D 不授权 entry
policy、exit policy、holding policy、portfolio backtest、model deployment、
production signal 或 live trading。

核心判断：18C 的失败更像是当前 23 个 feature 对 payoff-state 的表达能力不足，而不是
简单换一个略高容量模型就能解决。18D 因此支持进入 18E，补充 payoff-state
形态、相对位置、非对称空间和二阶 money-flow proxy 特征。

## 关键发现与洞察

1. 18C 的 primary robustness rank IC 只有 `0.064398`，低于 `0.08`
   materiality floor。当前特征上最好的辅助模型是
   `shallow_tree_payoff_depth2_v1`，robustness rank IC 为 `0.076792`，
   比 primary ridge 高 `0.012394`，仍低于 `0.015` 的 capacity delta threshold。
   这说明容量提升没有形成可靠 rescue，只能给出 `thin_margin_caveat`。

2. bounded train-only grouped CV probe 也没有救回当前特征。depth-3 decision tree
   grouped CV rank IC 为 `0.008962`，比 primary CV rank IC 低 `0.004714`；
   depth-4 为 `0.007576`，更弱。现有 feature 的问题更像 representation
   bottleneck，而不是模型容量太低。

3. `M1` 是最强候选族。它有 11 个候选、11 个 primary allowed、8 个
   train-prior orthogonal payoff candidates，去重后 priority score 为 `0.343334`。
   证据集中在 episode 内部修复路径、回撤/回补位置、失败修复次数和 path entropy，
   正好对应 18C 当前 return/high-distance 特征缺失的 path morphology。

4. `M5` 的 t0 已知位置特征也有实质信息。它有 9 个候选，其中 7 个 primary allowed、
   6 个 orthogonal candidates，去重后 score 为 `0.223796`。但 `M5` 里有两个
   appendix-only 风险点：`m5_lifecycle_progress_to_t0` 使用完整 episode boundary，
   明确 look-ahead blocked；`m5_bars_since_reclaim` finite rate 只有 `79.5386%`，
   低于 primary 可用性要求。

5. `M3` 支持 payoff asymmetry，但有效信息主要来自 upside room 和 range position。
   `M3` 有 8 个候选、8 个 primary allowed、5 个 orthogonal candidates，
   score 为 `0.196162`。其中 `m3_upside_room_to_episode_high` 的 residual rank IC
   为 `0.069110`，是所有候选里最强的单项 train-prior residual evidence。

6. `M2` 的二阶 money-flow proxy 值得加入，但应作为 proxy 而不是订单流事实。
   `M2` 有 12 个候选、全部 primary allowed，其中 7 个在
   `f2_extended_participation_money` 控制集下仍保留 orthogonal evidence，score 为
   `0.164602`。最强项是 `m2_money_flow_reversal_accel_5v20`，residual rank IC
   为 `-0.042115`。这支持加入二阶资金压力、反转加速度、集中度和价量背离 persistence。

7. `M4` 没有通过刷新门。它只有 1 个 deferred row，0 个 primary allowed，
   score 为 `0.000000`，blocking reason 为
   `no_orthogonal_train_prior_or_deferred`。除非 18E 之前有新的 PIT regime/context
   数据，否则不应把 M4 当作主刷新方向。

## 决策门与授权边界

| gate | status |
|:--|:--|
| upstream_18c_contract_gate | pass |
| input_artifact_gate | pass |
| capacity_vs_representation_gate | pass |
| candidate_inventory_completeness_gate | pass |
| candidate_lineage_gate | pass |
| pit_t0_availability_gate | pass |
| orthogonal_payoff_information_gate | pass |
| feature_family_prioritization_gate | pass |
| search_accounting_gate | pass |

| authorization | value |
|:--|:--|
| entry_policy_authorized | False |
| exit_policy_authorized | False |
| holding_policy_authorized | False |
| portfolio_backtest_authorized | False |
| model_deployment_authorized | False |
| production_signal_authorized | False |
| live_trading_authorized | False |

18D 的下一步只允许生成或细化
`requirement_18e_payoff_state_feature_matrix_refresh.md`。它不能直接进入交易规则、
组合回测或上线信号。

## 18C 证据回放：容量不足还是表达不足

| metric | value | interpretation |
|:--|--:|:--|
| primary_ridge_robustness_rank_ic | 0.064398 | 18C primary 排序证据偏弱，低于 0.08 materiality floor |
| max_aux_existing_feature_rank_ic | 0.076792 | 现有特征上最好的辅助模型仍未越过 0.08 |
| max_aux_minus_primary_rank_ic | 0.012394 | 小于 0.015 capacity delta threshold |
| max_train_grouped_cv_probe_rank_ic | 0.008962 | bounded train-only probe 未显示容量 rescue |
| max_train_grouped_cv_probe_minus_primary_cv_rank_ic | -0.004714 | probe 比 primary CV 更弱 |
| max_aux_margin_to_floor | 0.003208 | 最好辅助模型距离 materiality floor 很近但仍不足 |
| max_aux_margin_to_capacity_delta_threshold | 0.002606 | 距离 capacity delta threshold 也很近，结论带 caveat |

capacity conclusion 为
`low_capacity_representation_gap_with_capacity_caveat`，capacity_margin_status 为
`thin_margin_caveat`。这不是说容量因素被完全排除，而是说在当前 evidence 下，
下一步更合理的是刷新 feature representation，而不是继续在同一组 23 个 feature
上调模型。

## 当前 Feature Gap 分解

| current family | represented information | missing payoff information | mapped candidate family | insight |
|:--|:--|:--|:--|:--|
| F1 | short return、MA spread、distance to highs | episode-internal repair path morphology | M1 | 当前只知道“涨跌和离高点距离”，缺少修复路径形状 |
| F2 | turnover、volume、money level z-score | signed inflow/outflow dynamics | M2 | 当前参与度特征多为水平值，缺少资金压力的方向、二阶变化和 persistence |
| F3 | board rank context | payoff asymmetry and path shape | M3 | 板块排名是 context，不等于上涨空间、下跌拥挤度或突破失败压力 |
| F4 | volatility、drawdown、intraday range | vol-adjusted repair quality | M1/M3 | 风险特征提供 ceiling，但不能表达修复质量和非对称空间 |
| F5 | board dummies、market cap、tradability | regime only if new PIT context exists | M4 | 静态 context 在 18C 证据弱，暂不作为主刷新方向 |

## 候选清单与 PIT/Lineage

候选清单完整性通过：

- expected_candidate_feature_n = `41`
- observed_candidate_feature_n = `41`
- missing_candidate_feature_n = `0`
- extra_candidate_feature_n = `0`

| family | candidate_n | primary_allowed_after_lineage | appendix_only | finite value range | future dependency rows | decision |
|:--|--:|--:|--:|:--|--:|:--|
| M1 | 11 | 11 | 0 | 21209 to 22508 / 23405 | 0 | primary allowed |
| M2 | 12 | 12 | 0 | 22508 to 22508 / 23405 | 0 | primary allowed |
| M3 | 8 | 8 | 0 | 21209 to 22508 / 23405 | 0 | primary allowed |
| M5 | 9 | 7 | 2 | 0 to 22508 / 23405 | 23405 | partial primary, partial appendix |
| M4 | 1 | 0 | 1 | 0 to 0 / 23405 | 0 | deferred |

被阻断或 appendix-only 的关键 rows：

| family | candidate_feature_id | finite rows | finite rate | blocking_reason | interpretation |
|:--|:--|--:|--:|:--|:--|
| M5 | m5_lifecycle_progress_to_t0 | 0 | 0.000000 | full_episode_boundary_after_t0 | 依赖完整 episode 结束边界，t0 不可知，不能进入 primary |
| M5 | m5_bars_since_reclaim | 18616 | 0.795386 | candidate_finite_rate_below_floor | t0 可知但覆盖率不足，只能 appendix |
| M4 | m4_regime_context_deferred | 0 | 0.000000 | m4_deferred_by_default | 没有新增 PIT context 证据，默认 deferred |

最重要的 look-ahead 结论：`m5_lifecycle_progress_to_t0` 明确使用
`uses_full_episode_boundary_after_t0 = True`，并且
`future_source_dependency_row_n = 23405`、
`future_normalizer_dependency_row_n = 23405`。因此它不能进入 18E 的 primary feature
matrix，除非后续能提供单独的 t0-frozen endpoint proof。

## Family Prioritization

| family | planned priority | adjusted priority | candidates | primary allowed | orthogonal candidates | appendix-only | dedup groups | raw score | dedup score | recommendation |
|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| M1 | high | recommended | 11 | 11 | 8 | 0 | 10 | 0.401751 | 0.343334 | primary_refresh_candidate |
| M3 | high | recommended | 8 | 8 | 5 | 0 | 7 | 0.223063 | 0.196162 | primary_refresh_candidate |
| M5 | high_medium | recommended | 9 | 7 | 6 | 2 | 9 | 0.260208 | 0.223796 | primary_refresh_candidate |
| M2 | medium | recommended | 12 | 12 | 7 | 0 | 12 | 0.194750 | 0.164602 | primary_refresh_candidate |
| M4 | low | deferred | 1 | 0 | 0 | 1 | 1 | 0.000000 | 0.000000 | appendix_or_deferred |

priority score 使用 train-prior residual rank IC，且只使用 dedup-group representative。
robustness 和 validation rows 只做诊断，不参与推荐选择。这个设计可以降低
target readout 后选择候选的风险。

分数排序和研究优先级并不完全相同：按 dedup score，M5 高于 M3；但 18D 的
recommended_refresh_family_ids 仍为 `M1|M3|M5|M2`，因为 M3 对应 18C 明确缺失的
payoff asymmetry/path shape，而 M5 是位置诊断补充。18E 可以按这个集合刷新，
但建模时应继续检查 M3/M5 的共线性和边际贡献。

## M1：Episode 内部修复形态

M1 是最强 evidence family。它补充的是 18C 当前 F1 缺失的“怎么修复”，而不是简单的
“当前涨了多少”。

| candidate_feature_id | residual IC | raw IC | residual retention | orthogonal |
|:--|--:|--:|--:|:--|
| m1_pullback_from_episode_high_t0 | -0.065799 | -0.067410 | 0.976099 | True |
| m1_episode_drawdown_pre_t0 | -0.057684 | -0.049975 | 1.154242 | True |
| m1_close_location_trailing60_range | -0.054793 | -0.056170 | 0.975500 | True |
| m1_close_location_episode_range | -0.051236 | -0.055572 | 0.921982 | True |
| m1_failed_repair_count_low_to_t0 | 0.041929 | 0.034560 | 1.213217 | True |
| m1_up_down_run_imbalance_20 | -0.038909 | -0.042683 | 0.911573 | True |
| m1_path_transition_entropy_episode | 0.020017 | 0.039028 | 0.512887 | True |
| m1_repair_path_efficiency_episode | -0.012967 | -0.021805 | 0.594664 | True |

洞察：

- `pullback_from_episode_high_t0`、`episode_drawdown_pre_t0` 和 close-location
  相关特征的残差 IC 最大，说明 payoff-state ranking 对“修复后所处位置”和“前期回撤
  形状”敏感。
- `failed_repair_count_low_to_t0` 和 `path_transition_entropy_episode` 提供的是
  路径质量信息，不是单点价格位置。它们对 18C 当前 F1 特征是有意义的补充。
- `m1_close_location_episode_range` 与 `m1_episode_recovery_ratio_to_high_t0`
  被归入同一 range-location alias group，score 使用代表项，避免重复计分。

## M3：Payoff Asymmetry 与突破压力

M3 的有效证据主要集中在 upside room、range position 和 failed breakout。它解释的是
同样的 t0 位置下，上方空间、下方拥挤和突破失败压力是否改变 payoff-state ranking。

| candidate_feature_id | residual IC | raw IC | residual retention | orthogonal |
|:--|--:|--:|--:|:--|
| m3_upside_room_to_episode_high | 0.069110 | 0.067410 | 1.025216 | True |
| m3_asymmetric_range_position_t0 | -0.051236 | -0.055572 | 0.921982 | True |
| m3_failed_breakout_count_pre_t0 | 0.046902 | 0.042062 | 1.115063 | True |
| m3_upside_downside_room_ratio_t0 | 0.017580 | 0.055090 | 0.319119 | True |
| m3_upper_shadow_pressure_share_20 | 0.011333 | 0.010360 | 1.093966 | True |

洞察：

- `m3_upside_room_to_episode_high` 是单项最强 residual evidence，支持把“距离 episode
  high 的上行空间”纳入 18E。
- `m3_upside_downside_room_ratio_t0` 的 raw IC 为 `0.055090`，但 residual IC 降到
  `0.017580`，说明一部分信息已经被 volatility/participation 或其他 path 变量解释。
  18E 中它适合作为补充，而不是核心单项。
- downside 相关的两个特征被归为同一 group，且没有成为 orthogonal candidate。下行拥挤
  可能仍可保留为 appendix/diagnostic，但不应成为主刷新权重来源。

## M5：t0 已知的位置与年龄诊断

M5 的核心价值是把 episode 位置和年龄显式化。它不是完整生命周期进度预测，因为完整
episode 结束边界在 t0 不可知。

| candidate_feature_id | residual IC | raw IC | residual retention | orthogonal |
|:--|--:|--:|--:|:--|
| m5_episode_age_to_t0 | 0.058699 | 0.059512 | 0.986345 | True |
| m5_nonoverlap_step_index_to_t0 | 0.058699 | 0.059512 | 0.986345 | True |
| m5_bars_since_episode_high_t0 | 0.041233 | 0.047833 | 0.862010 | True |
| m5_low_to_t0_age_ratio | -0.039523 | -0.038397 | 1.029324 | True |
| m5_bars_since_episode_low | 0.014731 | 0.017869 | 0.824385 | True |
| m5_high_to_t0_age_ratio | 0.010911 | 0.018614 | 0.586188 | True |

洞察：

- `m5_episode_age_to_t0` 与 `m5_nonoverlap_step_index_to_t0` 的 evidence 完全相同
  或高度接近。虽然它们在 declared dedup group 中是分开的，18E 仍应检查矩阵 rank、
  VIF 或相关性，必要时只保留一个。
- `bars_since_episode_high_t0` 和 `low_to_t0_age_ratio` 表明 payoff state 与
  “高点/低点到 t0 的相对时间结构”有关。这类变量是 t0-known，可以进入 primary。
- `m5_lifecycle_progress_to_t0` 不可进入 primary。它的名称看似是 t0 progress，但计算
  依赖 full episode boundary，因此是 look-ahead risk。

## M2：二阶 Money-flow Proxy

M2 使用的是 signed daily money-flow proxies，不是真实 order flow。18D 只把它作为
participation 和 pressure 的 proxy 来使用。

推荐 M2 时使用的控制集是 `f2_extended_participation_money`，不是
`base_vol_participation`。在 train split 中：

| control set | rows | recommendation eligible | orthogonal candidates | abs residual IC sum |
|:--|--:|--:|--:|--:|
| base_vol_participation | 12 | 0 | 0 | 0.262130 |
| f2_extended_participation_money | 12 | 12 | 7 | 0.194750 |

这意味着 M2 的 evidence 必须在控制现有 F2 participation/money 特征后仍存在，才允许
影响推荐。

| candidate_feature_id | residual IC | raw IC | residual retention | orthogonal |
|:--|--:|--:|--:|:--|
| m2_money_flow_reversal_accel_5v20 | -0.042115 | -0.045837 | 0.918788 | True |
| m2_flow_concentration_top3_share_20 | -0.024602 | -0.032066 | 0.767244 | True |
| m2_money_flow_persistence_trailing20 | 0.022790 | 0.014097 | 1.616672 | True |
| m2_turnover_compression_20_vs_60 | -0.021641 | -0.046154 | 0.468879 | True |
| m2_net_signed_money_flow_trailing20 | -0.021293 | -0.054852 | 0.388198 | True |
| m2_positive_money_flow_share_trailing20 | -0.018870 | -0.055115 | 0.342373 | True |
| m2_flow_price_divergence_persistence_20 | -0.013291 | -0.008913 | 1.491182 | True |

洞察：

- 最强项是 `money_flow_reversal_accel_5v20`，它是二阶变化项，符合“资金压力拐点”
  比单纯 money level 更接近 payoff-state morphology 的直觉。
- `flow_concentration_top3_share_20` 和 `flow_price_divergence_persistence_20`
  补充的是集中冲击和价量背离持续性，不应与当前 F2 money z-score 混为一类。
- `net_signed_money_flow_trailing20` raw IC 较强但 residual retention 只有 `0.388198`，
  表明相当一部分信息已被现有 participation/money 控制解释。18E 应保留但降低
  解释强度，不应把它当成独立主因。

## De-dup 与候选选择纪律

18D 的 score 使用 dedup-group representative，避免因为同一概念的别名重复提高 family
score。主要非 singleton group：

| family | dedup group | candidate ids | candidate_n | implication |
|:--|:--|:--|--:|:--|
| M1 | m1_range_location_group | `m1_close_location_episode_range`, `m1_episode_recovery_ratio_to_high_t0` | 2 | 两者表达 range/recovery 位置，score 只按代表项计 |
| M3 | m3_downside_room_group | `m3_downside_crowding_to_episode_low`, `m3_downside_room_to_episode_low_t0` | 2 | downside room 信息重叠，未形成 primary orthogonal candidate |

其他 M2、M5 以及多数 M1/M3 候选为 singleton group。即使如此，18E 仍需要在 feature
matrix 刷新后做相关性和稳定性检查，尤其是 `m5_episode_age_to_t0` 与
`m5_nonoverlap_step_index_to_t0`。

## Missingness 与 Split 证据口径

train-prior rows 是唯一可影响推荐的证据；robustness 和 validation rows 只用于诊断。

| family | train eligible rows | train missing min | train missing median | train missing max | orthogonal candidates |
|:--|--:|--:|--:|--:|--:|
| M1 | 11 | 0.032205 | 0.032205 | 0.083428 | 8 |
| M2 | 12 | 0.032205 | 0.032205 | 0.032205 | 7 |
| M3 | 8 | 0.032205 | 0.032205 | 0.083428 | 5 |
| M5 | 9 | 0.032205 | 0.032205 | 1.000000 | 6 |
| M4 | 1 | 1.000000 | 1.000000 | 1.000000 | 0 |

M1/M3 的 max missingness 为 `0.083428`，来自 episode path 需要低点到 t0 路径的候选。
M2 的 missingness 更稳定，全部为 `0.032205`。M5 的 max missingness 为 `1.000000`，
对应 `m5_lifecycle_progress_to_t0` 的完整 episode boundary block。

## 18E 刷新建议

18E 应按以下边界刷新 feature matrix：

1. Primary include:
   `M1`, `M3`, `M5` 中通过 lineage/PIT 的 t0-known features，以及 `M2` 中通过
   `f2_extended_participation_money` residualization 的二阶 money-flow proxy features。

2. Primary exclude:
   `m5_lifecycle_progress_to_t0`，因为它使用 full episode boundary after t0；
   `m5_bars_since_reclaim`，因为 finite rate 只有 `79.5386%`；
   `M4`，因为没有 primary PIT evidence。

3. M2 需要明确命名为 proxy feature family。报告和 requirement 中应避免把它写成真实
   order-flow 或逐笔资金流。

4. 18E 应继续复核共线性和 alias risk。重点检查 M1 range-location group、
   M3 downside group、M5 age/index pair，以及 M2 trailing/acceleration/curvature
   之间的相关性。

5. 18E 仍不能直接选择交易阈值或 policy。它的目标是生成 refresh 后的 feature matrix，
   再交给后续 separability 或 utility gate 验证。

## 数据来源与审计

| source_artifact_alias | resolved_source_status | artifact_n |
|:--|:--|--:|
| eighteen_a_handoff | pass | 4 |
| eighteen_c_handoff | pass | 13 |
| ep18_current_feature_matrix | pass | 5 |
| ep18_matrix_row_keys | pass | 1 |
| ep18_planning | pass | 2 |
| episode_geometry_panel | pass | 6 |
| market_or_regime_context_panel | pass | 2 |
| pit_money_flow_proxy_panel | pass | 1 |
| pit_price_path_panel | pass | 1 |
| pre_t0_supply_zone_panel | pass | 2 |

Search accounting 共 20 项检查全部 pass，关键约束包括：

- no_feature_selection_from_target_correlation_before_lineage = True
- no_candidate_added_after_target_readout = True
- no_candidate_removed_after_target_readout = True
- no_feature_selection_from_robustness = True
- no_feature_selection_from_validation = True
- no_final_model_training = True
- delayed_features_not_primary = True
- no_entry_policy_authorized = True
- no_portfolio_backtest_authorized = True
- no_live_trading_authorized = True

因此，本报告的 publishable 结论只支持 feature representation refresh，不支持任何
交易或部署动作。
