# 16C Sequential Continuation Separability Diagnostic Report

## 1. 单行裁决

`decision_state = 16C_sequential_continuation_separability_ready_for_policy_preflight`；`next_allowed_requirement = requirement_16d_sequential_continuation_policy_preflight.md`。

16C 的结论是：16B 设计出的 h20/up50 continuation label 在 t0 可观测状态上存在可复验的 train-only separability，并且这个 separability 没有只集中在 15B known-failed morphology context 里。因此它可以进入 16D 的 policy preflight。

这不是交易授权。16C 仍不授权 entry、exit、holding、收益、cost、production signal 或 model deployment。

| gate | status | evidence |
| --- | --- | --- |
| input_artifact_gate | pass | 49 个 input artifact hash 已写入 manifest；required inputs schema/read 全部通过 |
| upstream_16b_authorization_gate | pass | 16B decision、next requirement、base-rate、qfq/source、known-failed overlap 与 step lineage 复验通过 |
| step_label_binding_gate | pass | 23,405 个 primary h20/up50 step 无 duplicate、无 positive/negative overlap、无 horizon bound violation |
| feature_lineage_gate | pass | 27 个 t0 feature 的 max source pos/date 都不晚于 step_start |
| feature_leakage_gate | pass | 无 step_end、cluster_end、label、path taxonomy、split/identity 或 validation/robustness fit 泄漏 |
| train_cv_separability_gate | pass | grouped CV median AUC 0.675971；purged chronological CV median AUC 0.646587 |
| robustness_separability_gate | pass | robustness AUC 0.672220；PR-AUC lift 0.099183；cluster bootstrap AUC CI low 0.647004 |
| known_failed_context_independence_gate | pass | non-known-failed robustness AUC 0.688768，且样本 907 steps / 97 clusters |
| search_accounting_gate | pass | 无 model family grid、无 hyperparameter grid、无 feature selection grid；validation/robustness 未参与选择 |

Finding：16C ready 的核心不是单一表上的 AUC 超线，而是三层证据同时成立：train-only CV 有稳定排序能力，robustness split 上不塌，剔除 known-failed context 后仍有独立 separability。

## 2. 16B Authorization Replay

16C 只在 16B 明确授权 separability diagnostic 后运行。这里复验的是 16B 的 lineage，而不是重新设计 label。

| authorization_status | upstream_decision_state | upstream_next_allowed_requirement | step_generation_lineage_sane | soft_overlap_partial_coverage_caveat | known_failed_context_exposure_caveat |
| --- | --- | --- | ---: | ---: | ---: |
| pass | 16B_continuation_label_ready_for_separability_diagnostic | requirement_16c_sequential_continuation_separability_diagnostic.md | true | true | true |

| split | labelable_step_n | positive_step_n | negative_step_n | neutral_step_n | labelable_positive_rate | labelable_negative_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 20,245 | 10,078 | 4,884 | 5,283 | 0.497802 | 0.241245 |
| robustness | 2,496 | 1,346 | 526 | 624 | 0.539263 | 0.210737 |
| validation | 664 | 325 | 180 | 159 | 0.489458 | 0.271084 |

Finding：16B 的两个 caveat 被继承而不是抹掉。`soft_overlap_partial_coverage_caveat=true` 说明 15C2 soft membership 覆盖仍不适合作为 hard gate；`known_failed_context_exposure_caveat=true` 说明 16D 不能假装 morphology 风险不存在。它们不阻断 16C，是因为 16C 的 hard question 是 t0 separability 是否存在且是否脱离 known-failed context。

## 3. Target Denominator

16C 使用 16B 的 `continuation_survival_h20_no_deep_drawdown` primary label。neutral rows 不进入 binary AUC/PR-AUC，但保留在 denominator audit 中。

| split | labelable_step_n | binary_step_n | positive_n | negative_n | neutral_n | binary_positive_rate | labelable_positive_rate | neutral_rate | episode_cluster_n | instrument_n | feature_complete_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 20,245 | 14,962 | 10,078 | 4,884 | 5,283 | 0.673573 | 0.497802 | 0.260953 | 652 | 590 | 1.000000 |
| robustness | 2,496 | 1,872 | 1,346 | 526 | 624 | 0.719017 | 0.539263 | 0.250000 | 204 | 195 | 1.000000 |
| validation | 664 | 505 | 325 | 180 | 159 | 0.643564 | 0.489458 | 0.239458 | 40 | 40 | 1.000000 |

Interpretation：

- 训练样本不是 20,245，而是 binary denominator 14,962；其中 positive 10,078、negative 4,884。20,245 是 labelable denominator，包含 5,283 个 neutral。
- Binary positive rate 明显高于 labelable positive rate，是因为 neutral 被排除：train 从 0.497802 变成 0.673573，robustness 从 0.539263 变成 0.719017。
- Neutral 占比在 train/robustness/validation 上分别为 26.10% / 25.00% / 23.95%，不是边角噪音。16D 如果进入 policy preflight，必须继续明确 neutral 的处理方式，不能把 neutral 默认为 negative。
- 样本有效性主要来自 non-overlap h20 step 与 cluster grouping，而不是把 overlapping step 当独立样本放大功效。

## 4. Feature Contract And Lineage

Primary model 使用 27 个 t0-observable feature：20 个 qfq rolling market state，7 个 PIT membership context。所有 feature 都在 step_start 当下或之前可得。

| split | feature_family | feature_n | max_missing_rate | max_pit_context_missing_rate | status |
| --- | --- | ---: | ---: | ---: | --- |
| train | qfq_rolling_market_state | 20 | 0.000000 | 0.000000 | pass |
| train | pit_membership_context | 7 | 0.000000 | 0.000000 | pass |
| robustness | qfq_rolling_market_state | 20 | 0.000000 | 0.000000 | pass |
| robustness | pit_membership_context | 7 | 0.000000 | 0.000000 | pass |
| validation | qfq_rolling_market_state | 20 | 0.000000 | 0.000000 | pass |
| validation | pit_membership_context | 7 | 0.000000 | 0.000000 | pass |

| feature_family | lineage_status | feature_n |
| --- | --- | ---: |
| qfq_rolling_market_state | pass | 20 |
| pit_membership_context | pass | 7 |

| leakage_status | feature_n |
| --- | ---: |
| pass | 27 |

Finding：feature coverage 很干净，所有 split 的 feature_complete_rate 都是 1.0。更重要的是，15B path_type、known_failed_family、step_end、cluster_end、label outcome、split/identity 都没有进入 feature matrix。16C 的信号不是把 taxonomy 或 label future 泄漏进模型后得到的。

## 5. Train-only CV Evidence

16C 同时使用两套 train-only CV：episode-cluster grouped CV 用来防止同一 episode cluster 跨 fold；instrument-purged chronological CV 用来验证时间切分下的排序能力。两者都必须通过。

| cv_scheme | valid_fold_n | test_binary_step_n_sum | test_positive_n_sum | test_negative_n_sum | auc_min | auc_median | auc_max | pr_lift_median | rank_ic_median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| episode_cluster_grouped_cv | 5 | 14,962 | 10,078 | 4,884 | 0.667452 | 0.675971 | 0.689362 | 0.122421 | 0.285613 |
| instrument_purged_chronological_cv | 5 | 14,962 | 10,078 | 4,884 | 0.625273 | 0.646587 | 0.707460 | 0.097050 | 0.237331 |

| cv_scheme | model_id | auc_median | ap_median | pr_lift_median | rank_ic_median |
| --- | --- | ---: | ---: | ---: | ---: |
| episode_cluster_grouped_cv | intercept_only_baseline | 0.500000 | 0.677328 | 0.000000 |  |
| episode_cluster_grouped_cv | ridge_logistic_bar_state_v1 | 0.675971 | 0.798467 | 0.122421 | 0.285613 |
| episode_cluster_grouped_cv | single_depth2_tree_bar_state_v1 | 0.642791 | 0.756851 | 0.080219 | 0.245759 |
| instrument_purged_chronological_cv | intercept_only_baseline | 0.500000 | 0.686094 | 0.000000 |  |
| instrument_purged_chronological_cv | ridge_logistic_bar_state_v1 | 0.646587 | 0.791641 | 0.097050 | 0.237331 |
| instrument_purged_chronological_cv | single_depth2_tree_bar_state_v1 | 0.634170 | 0.749166 | 0.071029 | 0.241736 |

Finding：

- Ridge logistic 在两套 CV 都明显高于 intercept baseline。Grouped CV median AUC 0.675971，purged chronological median AUC 0.646587，说明信号不是只靠 cluster leakage。
- Depth-2 tree 也有正信号，但弱于 ridge logistic。这个结构合理：单个浅树能读出粗状态，线性多特征组合更稳定。
- Purged chronological CV 的 median AUC 比 grouped CV 低约 0.0294，这是预期内的时间压力折损；但最弱 fold AUC 仍为 0.625273，全部 fold 都高于 0.50。

Insight：AFML 口径下，这不是“找到一个模型就能交易”，而是证明 continuation label 对 t0 状态不是完全随机。16D 可以进入 policy preflight，但必须继续把 CV 方案、sample uniqueness、cost 和 action rule 分开验证。

## 6. OOS Robustness And Validation

Primary model 只在 train 上拟合；robustness/validation 只做 OOS readout，不参与选择。

| split | model_id | binary_step_n | positive_n | negative_n | episode_cluster_n | roc_auc | average_precision | binary_positive_rate | pr_auc_lift_vs_binary_base | cluster_bootstrap_auc_ci_low | cluster_bootstrap_auc_ci_high |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | intercept_only_baseline | 14,962 | 10,078 | 4,884 | 652 | 0.500000 | 0.673573 | 0.673573 | 0.000000 |  |  |
| train | ridge_logistic_bar_state_v1 | 14,962 | 10,078 | 4,884 | 652 | 0.680264 | 0.800662 | 0.673573 | 0.127089 |  |  |
| train | single_depth2_tree_bar_state_v1 | 14,962 | 10,078 | 4,884 | 652 | 0.647308 | 0.755644 | 0.673573 | 0.082071 |  |  |
| robustness | intercept_only_baseline | 1,872 | 1,346 | 526 | 204 | 0.500000 | 0.719017 | 0.719017 | 0.000000 |  |  |
| robustness | ridge_logistic_bar_state_v1 | 1,872 | 1,346 | 526 | 204 | 0.672220 | 0.818200 | 0.719017 | 0.099183 | 0.647004 | 0.700160 |
| robustness | single_depth2_tree_bar_state_v1 | 1,872 | 1,346 | 526 | 204 | 0.634296 | 0.781280 | 0.719017 | 0.062263 |  |  |
| validation | intercept_only_baseline | 505 | 325 | 180 | 40 | 0.500000 | 0.643564 | 0.643564 | 0.000000 |  |  |
| validation | ridge_logistic_bar_state_v1 | 505 | 325 | 180 | 40 | 0.610632 | 0.712213 | 0.643564 | 0.068648 |  |  |
| validation | single_depth2_tree_bar_state_v1 | 505 | 325 | 180 | 40 | 0.585333 | 0.685583 | 0.643564 | 0.042019 |  |  |

Finding：

- Robustness 是主 OOS gate。Ridge logistic 在 robustness 上 AUC 0.672220，PR-AUC lift 0.099183，cluster bootstrap AUC CI low 0.647004，均显著高于最低要求。
- Validation 是 stress readout，不参与选择。它的 AUC 0.610632 低于 train/robustness，但仍高于 baseline；这说明压力集有折损，但没有直接推翻 separability。
- Robustness binary positive rate 是 0.719017，高于 train 0.673573。PR-AUC 必须看 lift 而不是 raw AP，否则会被 base rate 抬高误导。

Insight：16C 的 OOS 证据最有价值的地方是 robustness split 没有 collapse。Validation 的 505 个 binary steps / 40 clusters 太小，适合作为 caveat，不适合作为模型选择依据。

## 7. Known-failed Context Rebuild

15B taxonomy 在 16C 中从 publishable membership 与冻结规则重建；local cache 只作为加速和一致性复验来源，不能单独作为 row-level truth。

| rule_closure_status | source_15b_anchor_n | joined_cluster_n | joined_anchor_n | missing_cluster_n | path_type_enum_status | taxonomy_rebuild_source | anchor_metric_cache_status | taxonomy_cache_consistency_status | taxonomy_rebuild_status | known_failed_context_rebuild_gate |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |
| pass | 417,131 | 2,867 | 417,131 | 0 | pass | 15b_anchor_path_shape_feature_panel_cache_acceleration | pass | pass | pass | pass |

16C 重新计算 known-failed family 的 positive step overlap，并与 16B readout 精确对齐：

| split | known_failed_family | recomputed_positive_step_n | recomputed_failed_family_positive_step_n | source_16b_failed_family_positive_step_n | count_delta_vs_16b | aggregate_rebuild_status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| train | choppy_reversal_winner | 10,078 | 110 | 110 | 0 | pass |
| train | late_rescue_winner | 10,078 | 5,066 | 5,066 | 0 | pass |
| train | jump_repricing_winner | 10,078 | 58 | 58 | 0 | pass |
| train | unclassified_mixed_path | 10,078 | 2,180 | 2,180 | 0 | pass |
| robustness | choppy_reversal_winner | 1,346 | 0 | 0 | 0 | pass |
| robustness | late_rescue_winner | 1,346 | 214 | 214 | 0 | pass |
| robustness | jump_repricing_winner | 1,346 | 68 | 68 | 0 | pass |
| robustness | unclassified_mixed_path | 1,346 | 391 | 391 | 0 | pass |
| validation | choppy_reversal_winner | 325 | 0 | 0 | 0 | pass |
| validation | late_rescue_winner | 325 | 222 | 222 | 0 | pass |
| validation | jump_repricing_winner | 325 | 11 | 11 | 0 | pass |
| validation | unclassified_mixed_path | 325 | 47 | 47 | 0 | pass |

Finding：known-failed context rebuild 是可证伪的，并且这次没有 drift。所有 known-failed family 的 recomputed count 与 16B source count 完全一致，`count_delta_vs_16b = 0`。这说明 16C 后续 context 读数不是一个新的 taxonomy 口径，而是对 16B 的一致性复验和分层诊断。

## 8. Context-independence Readout

这个 section 回答一个关键问题：16C 的 separability 是否只来自 late-rescue 或其他 known-failed morphology。如果只在 known-failed context 内有效，就不能把 label 推到 16D，只能降级为 morphology-conditioned readout。

| split | context_stratum | binary_step_n | positive_n | negative_n | episode_cluster_n | roc_auc | average_precision | binary_positive_rate | pr_auc_lift_vs_binary_base | valid_stratum_power | context_independence_status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| train | all_steps | 14,962 | 10,078 | 4,884 | 652 | 0.680264 | 0.800662 | 0.673573 | 0.127089 | true | readout |
| train | late_rescue_context | 7,603 | 5,066 | 2,537 | 164 | 0.682338 | 0.794963 | 0.666316 | 0.128647 | true | readout |
| train | non_late_rescue_context | 7,359 | 5,012 | 2,347 | 488 | 0.678550 | 0.807288 | 0.681071 | 0.126217 | true | readout |
| train | known_failed_context_any | 11,197 | 7,410 | 3,787 | 402 | 0.682627 | 0.795595 | 0.661784 | 0.133810 | true | readout |
| train | non_known_failed_context | 3,765 | 2,668 | 1,097 | 250 | 0.675634 | 0.819425 | 0.708632 | 0.110793 | true | pass |
| robustness | all_steps | 1,872 | 1,346 | 526 | 204 | 0.672220 | 0.818200 | 0.719017 | 0.099183 | true | readout |
| robustness | late_rescue_context | 319 | 214 | 105 | 20 | 0.642590 | 0.757502 | 0.670846 | 0.086656 | true | readout |
| robustness | non_late_rescue_context | 1,553 | 1,132 | 421 | 184 | 0.676800 | 0.829807 | 0.728912 | 0.100895 | true | readout |
| robustness | known_failed_context_any | 965 | 663 | 302 | 107 | 0.651039 | 0.782316 | 0.687047 | 0.095269 | true | readout |
| robustness | non_known_failed_context | 907 | 683 | 224 | 97 | 0.688768 | 0.849604 | 0.753032 | 0.096572 | true | pass |
| validation | all_steps | 505 | 325 | 180 | 40 | 0.610632 | 0.712213 | 0.643564 | 0.068648 | true | readout |
| validation | late_rescue_context | 368 | 222 | 146 | 13 | 0.594132 | 0.648476 | 0.603261 | 0.045215 | true | readout |
| validation | non_late_rescue_context | 137 | 103 | 34 | 27 | 0.642490 | 0.841359 | 0.751825 | 0.089534 | true | readout |
| validation | known_failed_context_any | 452 | 280 | 172 | 29 | 0.600748 | 0.684477 | 0.619469 | 0.065008 | true | readout |
| validation | non_known_failed_context | 53 | 45 | 8 | 11 | 0.666667 | 0.899335 | 0.849057 | 0.050279 | false | pass |

Finding：

- Train 的 non-known-failed context 仍有 3,765 binary steps / 250 clusters，AUC 0.675634，PR-AUC lift 0.110793。
- Robustness 的 non-known-failed context 仍有 907 binary steps / 97 clusters，AUC 0.688768，PR-AUC lift 0.096572。
- Late-rescue context 本身也有 separability，但它不是唯一来源。Robustness 中 late_rescue_context AUC 0.642590，而 non_late_rescue_context AUC 0.676800，更强。
- Validation 的 non_known_failed_context 只有 53 steps / 11 clusters，`valid_stratum_power=false`，只能作为压力读数，不能支撑或反驳 hard decision。

Insight：这一步是 16C 最关键的 AFML 防线。16B 曾经担心 continuation label 只是重新发现 late-rescue/known-failed morphology。16C 的分层结果说明，t0 状态对 continuation survival 的排序能力在非 known-failed context 中仍然存在，所以不应把它降级为“只适用于 15B 失败形态的 readout”。

## 9. Feature Signal Shape

Feature importance 是诊断读数，不是 feature selection。这里没有做 post-hoc 搜索，所有 feature contract 在拟合前冻结。

Grouped CV top features：

| feature_name | feature_family | mean_abs_coef_or_importance | median_rank | rank_iqr | sign_consistency_fold_share | selected_in_top_decile_fold_share | collinearity_caveat |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| distance_to_20d_low | qfq_rolling_market_state | 0.496817 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |  |
| intraday_range_20d_mean | qfq_rolling_market_state | 0.475070 | 2.000000 | 0.000000 | 1.000000 | 1.000000 |  |
| history_ready_240d_flag | pit_membership_context | 0.428443 | 4.000000 | 0.000000 | 1.000000 | 0.200000 | history_depth_feature_pair |
| history_observed_sessions_before_usable_date | pit_membership_context | 0.424453 | 3.000000 | 2.000000 | 1.000000 | 0.600000 | history_depth_feature_pair |
| ma_20_60_spread | qfq_rolling_market_state | 0.355114 | 5.000000 | 1.000000 | 1.000000 | 0.000000 |  |
| turnover_rate_20d_zscore | qfq_rolling_market_state | 0.310078 | 8.000000 | 8.000000 | 0.800000 | 0.200000 |  |
| distance_to_60d_low | qfq_rolling_market_state | 0.305613 | 6.000000 | 1.000000 | 1.000000 | 0.000000 |  |
| volatility_60d | qfq_rolling_market_state | 0.240166 | 9.000000 | 3.000000 | 1.000000 | 0.000000 |  |
| turnover_rate_20d_mean | qfq_rolling_market_state | 0.226701 | 10.000000 | 4.000000 | 1.000000 | 0.000000 |  |
| money_20d_zscore | qfq_rolling_market_state | 0.220951 | 8.000000 | 10.000000 | 1.000000 | 0.000000 |  |

Purged chronological CV top features：

| feature_name | feature_family | mean_abs_coef_or_importance | median_rank | rank_iqr | sign_consistency_fold_share | selected_in_top_decile_fold_share | collinearity_caveat |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| distance_to_20d_low | qfq_rolling_market_state | 0.488223 | 2.000000 | 2.000000 | 1.000000 | 0.800000 |  |
| intraday_range_20d_mean | qfq_rolling_market_state | 0.484244 | 4.000000 | 4.000000 | 1.000000 | 0.400000 |  |
| history_observed_sessions_before_usable_date | pit_membership_context | 0.397029 | 3.000000 | 2.000000 | 1.000000 | 0.600000 | history_depth_feature_pair |
| history_ready_240d_flag | pit_membership_context | 0.379152 | 5.000000 | 4.000000 | 1.000000 | 0.400000 | history_depth_feature_pair |
| ma_20_60_spread | qfq_rolling_market_state | 0.340520 | 6.000000 | 2.000000 | 1.000000 | 0.200000 |  |
| distance_to_60d_low | qfq_rolling_market_state | 0.303394 | 7.000000 | 5.000000 | 1.000000 | 0.200000 |  |
| turnover_rate_20d_zscore | qfq_rolling_market_state | 0.283049 | 8.000000 | 3.000000 | 1.000000 | 0.000000 |  |
| money_20d_zscore | qfq_rolling_market_state | 0.252482 | 19.000000 | 18.000000 | 0.800000 | 0.400000 |  |
| volatility_60d | qfq_rolling_market_state | 0.235928 | 10.000000 | 4.000000 | 1.000000 | 0.000000 |  |
| max_drawdown_20d | qfq_rolling_market_state | 0.224823 | 13.000000 | 5.000000 | 1.000000 | 0.000000 |  |

Univariate train decile spreads：

| feature_name | feature_family | train_frozen_bin_positive_minus_negative_rate_spread |
| --- | --- | ---: |
| intraday_range_20d_mean | qfq_rolling_market_state | 0.388110 |
| turnover_rate_20d_mean | qfq_rolling_market_state | 0.377422 |
| volatility_60d | qfq_rolling_market_state | 0.352705 |
| volatility_20d | qfq_rolling_market_state | 0.337341 |
| distance_to_60d_low | qfq_rolling_market_state | 0.331842 |
| turnover_rate_60d_mean | qfq_rolling_market_state | 0.328657 |
| ret_60d | qfq_rolling_market_state | 0.323151 |
| ma_20_60_spread | qfq_rolling_market_state | 0.249660 |
| distance_to_20d_low | qfq_rolling_market_state | 0.245157 |
| ret_20d | qfq_rolling_market_state | 0.216920 |

Finding：

- 最稳定的信号集中在近期位置、波动/日内振幅、换手/流动性和中短期趋势状态上。`distance_to_20d_low` 与 `intraday_range_20d_mean` 在 grouped 和 purged CV 都排在前列。
- PIT history features 也进入前列，但带有 `history_depth_feature_pair` collinearity caveat。它们可能捕捉上市历史深度、可交易性成熟度或样本结构，不应在 16D 中被解释为独立经济因子。
- Top univariate spreads 主要来自 qfq rolling market state，而不是 PIT membership context；这降低了“只是 board/history context 在分类”的风险。

Insight：这个 feature shape 更像是在 episode 内识别“当前位置是否已经进入高风险回撤状态”或“仍具备 continuation survival 条件”，而不是预测新的 entry alpha。AFML 上应把它放在 holding/continuation policy preflight 中检验，而不是反向拿去做 entry search。

## 10. Decision Implication For 16D

16C ready 允许创建 16D，但 16D 的边界必须很窄：

- 只能继承 `up50pct / h20 / continuation_survival_h20_no_deep_drawdown`。
- 必须继续使用 non-overlap sampling unit 和 train-only preprocessing。
- 必须继承 16B 的 soft-overlap caveat 和 16C 的 known-failed context caveat。
- 必须把 neutral handling 明确写入 policy preflight，不能在 action layer 悄悄改变 denominator。
- 必须继续禁止 entry/exit/PnL/cost/deployment 直接授权；16D 只能问 policy preflight 是否值得进入后续 utility diagnostic。

Final insight：16C 给出的证据已经足够支持下一步 policy preflight，因为 t0-observable state 对 continuation survival 有稳定排序能力，并且不是完全由 known-failed morphology 解释。但这仍然只是“持有中状态是否有条件信息”的诊断，不是交易收益证明。16D 的任务应该是把这个 separability 转换成严格的 policy question：在不引入 entry lookahead、不改变 sample unit、不污染 neutral denominator 的前提下，这个 score 是否能定义一个可审计的 continuation/defense action rule。
