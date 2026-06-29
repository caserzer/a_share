# 16X Payoff-aligned Continuation Label Power Precheck Report

## 1. 单行裁决

`decision_state = 16X_payoff_precheck_not_supported`；`next_allowed_requirement = none`。

16X 的问题很窄：在 16E-postmortem 已关闭 survival-score continuation-as-action 主线之后，只检查“把 continuation target 从 0/1 survival 改成 realized h20 payoff severity”是否已经具备足够的 OOS rank separability。它不是 label 重做、不是 policy、不是 utility，也不授权 entry/exit/holding、组合回测、生产信号或 live trading。

本次不支持的直接原因来自 3 个 payoff separability gate：

| blocking_reason | observed | required | margin |
| --- | ---: | ---: | ---: |
| `robustness_rank_ic_floor` | 0.051877 | >= 0.060000 | -0.008123 |
| `payoff_monotone_flag` | Spearman 0.163636 | >= 0.600000 | -0.436364 |
| `payoff_minus_survival_margin` | -0.000723 | > +0.030000 | -0.030723 |

结论：payoff target 不是没有任何信号，cluster bootstrap CI 也排除了 0；但这个信号在 robustness 上太弱、没有十分位单调性，并且没有比 survival probe 多出可用增量。因此不值得投入完整的 16B2 -> 16C2 -> 16D2 -> 16E2 payoff-aligned 重链。

## 2. 上游 16E-postmortem Replay

16X 先复验 16E-postmortem 的关闭状态，确认它不是绕过 `next_allowed = none` 的 continuation stage，而是 topic-level research restart 下的最小功效预检。

| observed_decision_state | observed_next_allowed_requirement | observed_continuation_as_action_mainline_closed | observed_directionality_gate | train_monotonicity_spearman | robustness_monotonicity_spearman | observed_no_new_computation_gate | upstream_postmortem_authorization_gate |
| --- | --- | ---: | --- | ---: | ---: | --- | --- |
| 16E_postmortem_mainline_closed_no_path_supported | none | 1 | fail | 0.903030 | 0.030303 | pass | pass |

解释：旧 16D survival score 在 train 上能按 realized payoff 排序，但到了 robustness 几乎完全失效。16E 已经证明“把 survival probability 当成 continuation action score”这条主线不能继续；16X 只检查“换成 payoff target”是否有足够证据重新开一条 label redesign 起点。

## 3. 输入、血缘与 No-new-computation 证据

所有 16X 必需输入均可读、schema pass，且进入 `input_artifact_audit.csv`。关键输入规模如下：

| artifact_key | row_count | role |
| --- | ---: | --- |
| `upstream_16e_postmortem_decision` | 1 | 复验 16E mainline closed 裁决 |
| `upstream_16e_postmortem_score_bucket_monotonicity_readout` | 30 | 复验 survival-score payoff 排序坍塌 |
| `upstream_16e_postmortem_manifest` | 100 | 复验 postmortem lineage |
| `upstream_16c_t0_feature_contract` | 50 | 冻结 feature whitelist / forbidden list |
| `upstream_16c_t0_feature_panel` | 23,405 | 唯一允许的逐行 t0 feature 与 payoff base 来源 |
| `upstream_16c_separability_score_panel` | 52,017 | 16C score lineage 输入 |
| `upstream_16c_fold_assignment_panel` | 14,962 | train primary universe 的 grouped-CV fold 来源 |
| `upstream_16b_base_rate_readout` | 135 | 16B survival label / horizon / threshold lineage |

Feature contract 复验为 pass：

| feature_contract_source | expected | actual | allowed_primary_model_feature_n | forbidden_as_model_feature_n | missing_feature_column_n | forbidden_feature_used_n | payoff_base_column_used_as_feature | label_or_future_column_used_as_feature_n | gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 16C_t0_feature_contract.csv:allowed_primary_model_feature_true | 27 | 27 | 27 | 23 | 0 | 0 | 0 | 0 | pass |

Payoff target 血缘也为 pass。`payoff_target_id = realized_h20_payoff_severity_v1` 直接使用 16C panel 既有列 `step_end_price_ratio_minus_one_for_label_rule`；与既有 close ratio 的一致性差异最大值为 `2.220446e-16`，属于浮点容差级别，不是重新计算价格或 forward return。

| payoff_base_column | train finite | robustness finite | validation finite | primary_probe_universe | train n | robustness n | validation n | neutral excluded | lineage gate |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| step_end_price_ratio_minus_one_for_label_rule | 1.000000 | 1.000000 | 1.000000 | binary_positive_negative_rows_only | 14,962 | 1,872 | 505 | 1 | pass |

No-new-computation audit 有 3 条，全部 pass：

| check_id | source_artifact_key | source_columns | allowed_transform_type | creates_new_price_or_return_cost_or_drawdown | gate |
| --- | --- | --- | --- | ---: | --- |
| `payoff_raw_passthrough` | upstream_16c_t0_feature_panel | step_end_price_ratio_minus_one_for_label_rule | column_alias | 0 | pass |
| `payoff_raw_close_ratio_lineage_cross_check` | upstream_16c_t0_feature_panel | step_start_qfq_close, step_end_qfq_close | lineage_consistency_check_only | 0 | pass |
| `label_class_derivation` | upstream_16c_t0_feature_panel | continuation_positive, continuation_negative, continuation_neutral | deterministic_label_state_derivation | 0 | pass |

含义：这次失败不能归因于输入缺失、feature 泄漏、payoff target 不可审计、价格重算或 hidden utility 计算。它是一个干净的 separability failure。

## 4. Probe 规格与样本功效

两个 probe 都只使用 16C frozen 27 个 allowed primary features。Robustness 只作为 confirmatory split，不参与拟合或调参；validation 只作 stress readout。

| probe_id | target_id | family | regularization | feature_contract_n | train_primary_probe_step_n | preprocessing_train_only | cv_scheme | fold_assignment_join_gate |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| survival_logistic_probe_v1 | continuation_survival_h20_no_deep_drawdown | ridge_logistic | C=1.0 | 27 | 14,962 | 1 | episode_cluster_grouped_cv_over_16c_train_binary_fold_assignment | pass |
| payoff_rank_probe_v1 | realized_h20_payoff_severity_v1 | ridge_regression | alpha=1.0 | 27 | 14,962 | 1 | episode_cluster_grouped_cv_over_16c_train_binary_fold_assignment | pass |

Power gate 本身通过：

| train_primary_probe_step_n | train_episode_cluster_n | robustness_primary_probe_step_n | robustness_episode_cluster_n | validation_primary_probe_step_n | train_cv_valid_fold_n | valid_bootstrap_resample_n | power_gate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 14,962 | 652 | 1,872 | 204 | 505 | 5 | 2,000 | pass |

解释：robustness 有 1,872 个 binary primary rows、204 个 episode clusters，足够做这次预检。最终裁决不是 `low_power`，而是“样本足够，但 payoff separability 不够”。

## 5. Survival-vs-payoff Rank IC

Rank IC 使用同一个 primary probe universe，衡量 probe score 与 realized h20 payoff 的 Spearman 排序相关。

| split_bucket | survival_rank_ic | payoff_rank_ic | payoff_minus_survival | payoff/train ratio | survival/train ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 0.157138 | 0.186701 | +0.029563 | 1.000000 | 1.000000 |
| robustness | 0.052600 | 0.051877 | -0.000723 | 0.277858 | 0.334744 |
| validation | 0.084679 | 0.075871 | -0.008808 | 0.406377 | 0.538884 |

Train CV median 仍然看起来不错：

| probe_id | cv_rank_ic_median |
| --- | ---: |
| survival_logistic_probe_v1 | 0.154382 |
| payoff_rank_probe_v1 | 0.176200 |

关键问题发生在 OOS。Payoff probe 在 train 上比 survival probe 高 `+0.029563`，但 robustness 上变成 `-0.000723`，没有达到预注册的 `+0.03` 增量门槛。换句话说，payoff target 在训练期吸收了一些 payoff magnitude 信息，但这些信息没有稳定迁移到 robustness；它没有证明“换 target”能解决 16E 发现的 survival-score/payoff 解耦。

## 6. Robustness Decile Monotonicity

Robustness primary rows 按 payoff probe score 从低到高分十分位后，mean payoff 并不随 score 单调上升：

| decile_index | row_n | mean_payoff_raw | mean_probe_score |
| ---: | ---: | ---: | ---: |
| 1 | 188 | 0.037381 | -0.009748 |
| 2 | 187 | 0.036759 | 0.033078 |
| 3 | 187 | 0.066861 | 0.051438 |
| 4 | 187 | 0.072432 | 0.061707 |
| 5 | 187 | 0.093070 | 0.068047 |
| 6 | 187 | 0.059917 | 0.073340 |
| 7 | 187 | 0.061377 | 0.077919 |
| 8 | 187 | 0.048591 | 0.082513 |
| 9 | 187 | 0.058487 | 0.089013 |
| 10 | 188 | 0.062613 | 0.106341 |

| split_bucket | row_n | decile_monotonicity_spearman | monotone_flag | decile_1_mean | decile_10_mean | high_minus_low | top3_mean | bottom3_mean | max_payoff_decile |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 14,962 | 0.939394 | 1 | -0.013785 | 0.080853 | 0.094639 | 0.066088 | 0.010098 | 10 |
| robustness | 1,872 | 0.163636 | 0 | 0.037381 | 0.062613 | 0.025231 | 0.056564 | 0.047000 | 5 |
| validation | 505 | 0.369697 | 0 | 0.026672 | 0.080229 | 0.053557 | 0.043701 | 0.028924 | 10 |

最有解释力的是 robustness：最高 payoff 出现在第 5 十分位（`0.093070`），不是第 10 十分位；第 6 到第 8 十分位反而回落。Top score bucket 的 payoff 均值 `0.062613` 只比 bottom bucket 的 `0.037381` 高 `0.025231`，而 train 的对应差距是 `0.094639`。这说明 payoff probe 的 score 在 robustness 中更像一个弱的中段 hump，而不是可操作的、越高越好的 payoff rank surface。

## 7. Cluster-bootstrap CI 的正确解读

Bootstrap 读数如下：

| split_bucket | probe_id | rank_ic_spearman | ci_low | ci_high | ci_level | valid_resample_n | bootstrap_resample_n | ci_excludes_zero_flag |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| robustness | payoff_rank_probe_v1 | 0.051877 | 0.007706 | 0.097324 | 0.950000 | 2,000 | 2,000 | 1 |

这个 CI 排除 0，所以不能说 payoff target 完全没有信息。但它只能支持“存在很弱的正 rank IC”，不能支持“足够强、足够单调、且相对 survival 有增量”。16X 的 gate 设计本来就把这三件事分开：

| gate item | observed | required | status |
| --- | ---: | ---: | --- |
| robustness payoff rank IC | 0.051877 | >= 0.060000 | fail |
| payoff decile monotonicity | 0.163636 | >= 0.600000 | fail |
| payoff - survival rank IC margin | -0.000723 | > +0.030000 | fail |
| train CV payoff rank IC median | 0.176200 | >= 0.060000 | pass |
| cluster-bootstrap CI excludes zero | 1 | 1 | pass |

因此本次不是“统计功效不够导致无法判断”，也不是“payoff target 完全不可学”。更准确的表述是：payoff target 可学到一点 OOS 排序信息，但强度和形态都不足以触发重做链。

## 8. Search Accounting 与授权边界

Search accounting 全部 pass：

| payoff_target_config_frozen_before_training | probe_spec_frozen_before_training | no_new_price_or_return_computed | no_16c_model_refit | feature_contract_unchanged | threshold_id_unchanged | horizon_unchanged | validation_used_for_selection | robustness_used_for_probe_tuning | search_accounting_gate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | pass |

授权位全部保持 false：

| payoff_aligned_label_redo_authorized | entry_policy_authorized | exit_policy_authorized | holding_policy_authorized | chained_simulation_authorized | portfolio_backtest_authorized | model_deployment_authorized | production_signal_authorized | live_trading_authorized |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

这很重要：16X 即使通过，也最多只能授权 `requirement_16b2_payoff_aligned_continuation_label_design_diagnostic.md` 这个重做链起点。本次没有通过，所以 `next_allowed_requirement = none`。

## 9. Findings And Insight

**Finding 1 - 失败不是 lineage 或数据卫生问题。**

输入、feature contract、payoff target lineage、fold assignment、no-new-computation、search accounting 全部 pass。Payoff base column 来自 16C 既有 panel，finite rate 在 train/robustness/validation 都是 1.0，且没有把 payoff base、label、future close 或 split boundary 偷放进 feature matrix。这个结论可以排除“实现漏读列/特征污染/重新算收益导致失败”的解释。

**Finding 2 - train 上的 payoff signal 没有 OOS 稳定迁移。**

Payoff probe 在 train 的 rank IC 是 `0.186701`，高于 survival probe 的 `0.157138`；train CV median 也是 `0.176200`，远高于 0.06 floor。但 robustness rank IC 只有 `0.051877`，只剩 train 的约 27.8%，并且略低于 survival probe 的 `0.052600`。这说明直接回归 payoff magnitude 在训练集能解释一部分收益大小，但目前 16C t0 feature contract 没有提供能稳定外推的 payoff state。

**Finding 3 - Decile 形态比单个 IC 更保守，也更接近可用性判断。**

如果 payoff score 真能成为后续 label redesign 的依据，高分桶应该系统性对应更高 realized payoff。Robustness 中最高 payoff 出现在第 5 桶，不在第 10 桶；第 8 桶低于第 3、4、5、6、7、9、10 桶。这个形态不适合拿去做 continuation label threshold、defense threshold 或 policy candidate。

**Finding 4 - Bootstrap CI 排除 0 只是“弱信号存在”，不是“重链值得做”。**

CI `[0.007706, 0.097324]` 说明 payoff probe 的 OOS rank IC 不是纯零，但 gate 还要求 rank IC floor、decile monotonicity 和相对 survival 的增量。三项全部失败时，正确动作是关闭重做链，而不是把弱正 IC 放大成 label redesign 授权。

**Finding 5 - Validation stress 没有提供反证。**

Validation payoff rank IC 为 `0.075871`，但仍低于 validation survival rank IC `0.084679`，且 validation decile monotonicity 只有 `0.369697`，没有达到 0.6。虽然 validation 不参与选择或 gate，但它没有显示“robustness 偶然失效、validation 已恢复单调”的模式。

**Finding 6 - 下一步不应是调 threshold 或重跑 16D/16E。**

当前瓶颈在 t0 feature 对 payoff magnitude 的 OOS separability，而不是 policy cutoff、utility cost tier 或 drawdown gate。继续在 survival-score continuation action 上做 threshold/policy 搜索，或立刻投入 16B2 payoff label 重链，都会把问题推到下游。更合理的研究方向是回到 topic-level 上游：检查 entry alpha、payoff state 表征、或者 winner episode 中能否在更早阶段识别 payoff magnitude，而不是在现有 16C feature contract 下继续包装 continuation score。

## 10. Final Decision

`16X_payoff_precheck_not_supported` 是一个有效的关闭裁决：

1. Hard lineage gates pass，说明输入与审计链可信。
2. Power gate pass，说明不是样本太少导致无法判断。
3. Payoff separability gate fail，说明换成 payoff-aligned target 这条路当前没有足够 OOS 支持。
4. 所有部署、policy、utility、backtest 授权保持 false。
5. `next_allowed_requirement = none`；continuation-as-action 主线保持关闭。
