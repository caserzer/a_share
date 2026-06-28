# 16B Sequential Continuation Label Design Diagnostic Report

## 1. 单行裁决

`decision_state = 16B_continuation_label_ready_for_separability_diagnostic`；`next_allowed_requirement = requirement_16c_sequential_continuation_separability_diagnostic.md`。

16B 已完成 continuation label design diagnostic：base rate、effective sample、train/robustness stability、16A authorization、step materialization、qfq price source、known-failed projection evaluability 全部通过。当前只授权 16C 做 separability diagnostic；仍不授权 entry、exit、holding、收益、cost、模型训练或 deployment。

| item | value |
| --- | --- |
| primary_label_id | continuation_survival_h20_no_deep_drawdown |
| selected_threshold_id | up50pct |
| primary_horizon_sessions | 20 |
| decision_state | 16B_continuation_label_ready_for_separability_diagnostic |
| next_allowed_requirement | requirement_16c_sequential_continuation_separability_diagnostic.md |
| known_failed_overlap_gate | pass |
| known_failed_overlap_evaluability_gate | pass |
| known_failed_context_exposure_caveat | True |
| soft_overlap_partial_coverage_caveat | True |
| label_deployment_authorized | False |
| signal_search_authorized | False |
| model_training_authorized | False |
| entry_policy_authorized | False |
| separability_search_authorized | False |

## 2. What Changed In The Interpretation

本次修正后的关键口径是：15B `path_type` 是 episode/cluster 的 full-path descriptor，不是 h20 step-local morphology。把 15B cluster-level descriptor 投影到 16B h20 step，只能说明该 step 位于某个 known-failed episode context 中，不能说明该 h20 step 自身重新发现了 known-failed morphology。

因此，late-rescue 在 h20 step 上占比高只写入 `known_failed_context_exposure_caveat`，不再阻断 16C。真正可以 hard fail 的仍是 lineage/evaluability 问题：15B enum 不存在、projection column 缺失、hard projection coverage 不足、或 16A/price/step lineage 不可证明。

## 3. 16A Authorization And Step Lineage

16B 复验了 16A 的授权行：16A decision 为 `16A_sampling_geometry_ready_for_sequential_label_design`，`next_allowed_requirement` 指向本 16B requirement，sampling unit 为 `non_overlapping_time_blocked_sampling_geometry_step`。

| audit item | value |
| --- | ---: |
| 16A train nonoverlap_step_n_h20 | 20,871 |
| 16A train full_horizon_nonoverlap_step_n_h20 | 20,245 |
| 16A train partial_tail_step_n_h20 | 626 |
| 16A train anchor_overcount_ratio_h20 | 2.756169 |
| 16A train effective_sample_size_h20 | 20,245 |
| effective_to_anchor_ratio_abs_range | 0.131094 |
| all_16a_hard_gates_passed | True |

Input audit 通过：33 个 required artifact、2 个 optional appendix artifact、1 个 optional soft-overlap context artifact 均为 `pass`。qfq audit 覆盖 788 个 instrument、504,580 个 required labelable step；nonfinite close、nonpositive close、step bounds out of qfq 全部为 0。

## 4. Step Materialization

16B 沿用 16A 的 full-horizon non-overlap formula materialize step。所有 up50 split/horizon 的 `materialized_step_n` 都等于 16A expected labelable step，`step_count_delta_vs_16a = 0`，`duplicate_step_id_n = 0`，`bad_step_bounds_n = 0`，`partial_tail_materialized_n = 0`。

| split | h | source_episode_cluster_n | materialized_step_n | expected_from_16a | step_delta | partial_tail_materialized_n | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 5 | 667 | 81,906 | 81,906 | 0 | 0 | pass |
| train | 8 | 667 | 51,062 | 51,062 | 0 | 0 | pass |
| train | 13 | 660 | 31,281 | 31,281 | 0 | 0 | pass |
| train | 15 | 659 | 27,078 | 27,078 | 0 | 0 | pass |
| train | 20 | 652 | 20,245 | 20,245 | 0 | 0 | pass |
| robustness | 5 | 209 | 10,280 | 10,280 | 0 | 0 | pass |
| robustness | 8 | 208 | 6,385 | 6,385 | 0 | 0 | pass |
| robustness | 13 | 206 | 3,881 | 3,881 | 0 | 0 | pass |
| robustness | 15 | 206 | 3,354 | 3,354 | 0 | 0 | pass |
| robustness | 20 | 204 | 2,496 | 2,496 | 0 | 0 | pass |
| validation | 5 | 45 | 2,729 | 2,729 | 0 | 0 | pass |
| validation | 8 | 45 | 1,698 | 1,698 | 0 | 0 | pass |
| validation | 13 | 45 | 1,036 | 1,036 | 0 | 0 | pass |
| validation | 15 | 45 | 895 | 895 | 0 | 0 | pass |
| validation | 20 | 41 | 664 | 664 | 0 | 0 | pass |

Finding：16B 的 label population 是 16A 几何口径的严格 materialization，不包含 partial tail，也没有重新引入 anchor-level denominator。

## 5. Primary Label Rule

Primary label：`continuation_survival_h20_no_deep_drawdown`。

| label class | predicate |
| --- | --- |
| positive | `max_drawdown_from_step_start > -0.10 and step_end_price_ratio_minus_one_for_label_rule >= 0` |
| negative | `max_drawdown_from_step_start <= -0.10` |
| neutral | `not continuation_positive and not continuation_negative` |
| tail usage | excluded_from_labelable_population |
| price field | qfq_close |

解释：一个 h20 step 如果在 20-session 内没有经历超过 10% 的 close-to-close drawdown，且 step 末端不低于起点，则为 positive。若 drawdown 触及或超过 -10%，归 negative。末端下跌但未触发 -10% drawdown 的 step 归 neutral。

## 6. Primary Base Rate And Support

| split | labelable_step_n | positive_step_n | negative_step_n | neutral_step_n | positive_rate | negative_rate | neutral_rate | positive_effective_sample_size | negative_effective_sample_size | episode_cluster_n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 20,245 | 10,078 | 4,884 | 5,283 | 0.497802 | 0.241245 | 0.260953 | 10,078 | 4,884 | 652 |
| robustness | 2,496 | 1,346 | 526 | 624 | 0.539263 | 0.210737 | 0.250000 | 1,346 | 526 | 204 |
| validation | 664 | 325 | 180 | 159 | 0.489458 | 0.271084 | 0.239458 | 325 | 180 | 41 |

Support gate 通过：train positive effective sample = 10,078，negative effective sample = 4,884；robustness negative effective sample = 526，高于 50 的 robustness floor。train 与 robustness 的 positive rate 差为 0.0415，negative rate 差为 0.0305，低于 0.15 的 stability 阈值。

Insight：这个 label 不是 class-degenerate 目标。它在 train/robustness 上有足够样本、正负类都不稀疏，并且 validation stress split 也能评估。

## 7. Horizon Sensitivity

| split | h | labelable_step_n | positive_step_n | negative_step_n | neutral_step_n | positive_rate | negative_rate | neutral_rate | episode_cluster_n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 5 | 81,906 | 42,108 | 3,239 | 36,559 | 0.514102 | 0.039545 | 0.446353 | 667 |
| train | 8 | 51,062 | 26,435 | 4,302 | 20,325 | 0.517704 | 0.084251 | 0.398046 | 667 |
| train | 13 | 31,281 | 15,895 | 4,935 | 10,451 | 0.508136 | 0.157763 | 0.334101 | 660 |
| train | 15 | 27,078 | 13,754 | 4,725 | 8,599 | 0.507940 | 0.174496 | 0.317564 | 659 |
| train | 20 | 20,245 | 10,078 | 4,884 | 5,283 | 0.497802 | 0.241245 | 0.260953 | 652 |
| robustness | 5 | 10,280 | 5,340 | 343 | 4,597 | 0.519455 | 0.033366 | 0.447179 | 209 |
| robustness | 8 | 6,385 | 3,402 | 458 | 2,525 | 0.532811 | 0.071731 | 0.395458 | 208 |
| robustness | 13 | 3,881 | 2,072 | 570 | 1,239 | 0.533883 | 0.146869 | 0.319248 | 206 |
| robustness | 15 | 3,354 | 1,805 | 542 | 1,007 | 0.538163 | 0.161598 | 0.300239 | 206 |
| robustness | 20 | 2,496 | 1,346 | 526 | 624 | 0.539263 | 0.210737 | 0.250000 | 204 |
| validation | 5 | 2,729 | 1,343 | 112 | 1,274 | 0.492122 | 0.041041 | 0.466838 | 45 |
| validation | 8 | 1,698 | 844 | 155 | 699 | 0.497055 | 0.091284 | 0.411661 | 45 |
| validation | 13 | 1,036 | 519 | 184 | 333 | 0.500965 | 0.177606 | 0.321429 | 45 |
| validation | 15 | 895 | 429 | 177 | 289 | 0.479330 | 0.197765 | 0.322905 | 45 |
| validation | 20 | 664 | 325 | 180 | 159 | 0.489458 | 0.271084 | 0.239458 | 41 |

Finding：positive rate 在 5 到 20 sessions 上基本稳定，train 在 0.4978 到 0.5177 之间，robustness 在 0.5195 到 0.5393 之间，validation 在 0.4793 到 0.5010 之间。negative rate 随 horizon 上升，这是规则本身的机械结果：窗口越长，越容易触发 -10% drawdown。

## 8. Threshold Sensitivity At H20

| threshold_id | split | labelable_step_n | positive_step_n | negative_step_n | neutral_step_n | positive_rate | negative_rate | neutral_rate | episode_cluster_n |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| up50pct | train | 20,245 | 10,078 | 4,884 | 5,283 | 0.497802 | 0.241245 | 0.260953 | 652 |
| up100pct | train | 13,774 | 6,977 | 3,444 | 3,353 | 0.506534 | 0.250036 | 0.243430 | 378 |
| up150pct | train | 8,597 | 4,459 | 2,146 | 1,992 | 0.518669 | 0.249622 | 0.231709 | 233 |
| up50pct | robustness | 2,496 | 1,346 | 526 | 624 | 0.539263 | 0.210737 | 0.250000 | 204 |
| up100pct | robustness | 1,355 | 737 | 326 | 292 | 0.543911 | 0.240590 | 0.215498 | 87 |
| up150pct | robustness | 906 | 525 | 205 | 176 | 0.579470 | 0.226269 | 0.194260 | 54 |
| up50pct | validation | 664 | 325 | 180 | 159 | 0.489458 | 0.271084 | 0.239458 | 41 |
| up100pct | validation | 129 | 66 | 41 | 22 | 0.511628 | 0.317829 | 0.170543 | 8 |
| up150pct | validation | 82 | 42 | 28 | 12 | 0.512195 | 0.341463 | 0.146341 | 5 |

Insight：提高 threshold 不会破坏 label base rate，train positive rate 在三档 threshold 中保持在 0.4978 到 0.5187。validation 在 up100/up150 的 cluster/step 数很小，只能作为 stress caveat，不应驱动 primary decision。

## 9. Known-failed Episode-context Exposure

hard taxonomy projection coverage 全部为 1.0，因此 15B context projection 可评估。15C2 soft coverage 不足只写入 `soft_overlap_partial_coverage_caveat`，不阻断 primary decision。

| split | known_failed_family | positive_step_n | failed_family_positive_step_n | failed_family_positive_share | all_step_failed_family_share | share_delta | hard_projection_coverage | soft_overlap_coverage | overlap_status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | choppy_reversal_winner | 10,078 | 110 | 0.010915 | 0.012052 | -0.001137 | 1.0000 | 0.5000 | pass |
| train | late_rescue_winner | 10,078 | 5,066 | 0.502679 | 0.524623 | -0.021944 | 1.0000 | 0.5000 | episode_context_exposure_caveat |
| train | jump_repricing_winner | 10,078 | 58 | 0.005755 | 0.005582 | 0.000173 | 1.0000 | 0.5000 | pass |
| train | unclassified_mixed_path | 10,078 | 2,180 | 0.216313 | 0.221388 | -0.005075 | 1.0000 | 0.5000 | pass |
| robustness | choppy_reversal_winner | 1,346 | 0 | 0.000000 | 0.000000 | 0.000000 | 1.0000 | 0.5000 | pass |
| robustness | late_rescue_winner | 1,346 | 214 | 0.158990 | 0.169471 | -0.010482 | 1.0000 | 0.5000 | pass |
| robustness | jump_repricing_winner | 1,346 | 68 | 0.050520 | 0.053686 | -0.003166 | 1.0000 | 0.5000 | pass |
| robustness | unclassified_mixed_path | 1,346 | 391 | 0.290490 | 0.306891 | -0.016401 | 1.0000 | 0.5000 | pass |
| validation | choppy_reversal_winner | 325 | 0 | 0.000000 | 0.000000 | 0.000000 | 1.0000 | 0.9091 | pass |
| validation | late_rescue_winner | 325 | 222 | 0.683077 | 0.736446 | -0.053369 | 1.0000 | 0.9091 | episode_context_exposure_caveat |
| validation | jump_repricing_winner | 325 | 11 | 0.033846 | 0.022590 | 0.011256 | 1.0000 | 0.9091 | pass |
| validation | unclassified_mixed_path | 325 | 47 | 0.144615 | 0.143072 | 0.001543 | 1.0000 | 0.9091 | pass |

Finding：late-rescue 在 train positive step 中占 50.27%，但 all-step baseline 更高，为 52.46%；validation positive step 中占 68.31%，all-step baseline 为 73.64%。这不是 positive label 相对 baseline 的 enrichment，而是 h20 step population 对长 late-rescue episode context 的 duration-weighted exposure。

AFML interpretation：这应该作为 context caveat 进入 16C，而不是在 16B 阶段阻断。16C 如果继续做 separability，需要报告 morphology-conditioned performance，或者至少把 late-rescue context 作为分层 audit；但 16B 不再声称 step-local rediscovered known-failed morphology。

## 10. Late-rescue Exposure Across Horizon

| split | h | positive_step_n | late_rescue_positive_step_n | late_rescue_positive_share | all_step_late_rescue_share | share_delta | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 5 | 42,108 | 21,504 | 0.510687 | 0.521525 | -0.010838 | episode_context_exposure_caveat |
| train | 8 | 26,435 | 13,360 | 0.505391 | 0.522169 | -0.016779 | episode_context_exposure_caveat |
| train | 13 | 15,895 | 8,024 | 0.504813 | 0.523577 | -0.018764 | episode_context_exposure_caveat |
| train | 15 | 13,754 | 6,905 | 0.502036 | 0.523635 | -0.021600 | episode_context_exposure_caveat |
| train | 20 | 10,078 | 5,066 | 0.502679 | 0.524623 | -0.021944 | episode_context_exposure_caveat |
| robustness | 5 | 5,340 | 837 | 0.156742 | 0.167412 | -0.010671 | pass |
| robustness | 8 | 3,402 | 526 | 0.154615 | 0.167894 | -0.013279 | pass |
| robustness | 13 | 2,072 | 312 | 0.150579 | 0.168771 | -0.018192 | pass |
| robustness | 15 | 1,805 | 282 | 0.156233 | 0.168754 | -0.012521 | pass |
| robustness | 20 | 1,346 | 214 | 0.158990 | 0.169471 | -0.010482 | pass |
| validation | 5 | 1,343 | 936 | 0.696947 | 0.723342 | -0.026395 | episode_context_exposure_caveat |
| validation | 8 | 844 | 579 | 0.686019 | 0.725559 | -0.039541 | episode_context_exposure_caveat |
| validation | 13 | 519 | 344 | 0.662813 | 0.727799 | -0.064986 | episode_context_exposure_caveat |
| validation | 15 | 429 | 291 | 0.678322 | 0.730726 | -0.052405 | episode_context_exposure_caveat |
| validation | 20 | 325 | 222 | 0.683077 | 0.736446 | -0.053369 | episode_context_exposure_caveat |

Insight：train 和 validation 的 h20 step population 长期暴露在 late-rescue episode context 中；robustness 则不是。这个 split composition 差异需要 16C 分层评估。它不否定 16B label design，但提醒后续 separability 不能只看 aggregate AUC/precision。

## 11. Late-rescue Threshold Sensitivity At H20

| threshold_id | split | positive_step_n | late_rescue_positive_step_n | late_rescue_positive_share | all_step_late_rescue_share | share_delta | status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| up50pct | train | 10,078 | 5,066 | 0.502679 | 0.524623 | -0.021944 | episode_context_exposure_caveat |
| up100pct | train | 6,977 | 3,770 | 0.540347 | 0.571729 | -0.031382 | episode_context_exposure_caveat |
| up150pct | train | 4,459 | 2,282 | 0.511774 | 0.552635 | -0.040861 | episode_context_exposure_caveat |
| up50pct | robustness | 1,346 | 214 | 0.158990 | 0.169471 | -0.010482 | pass |
| up100pct | robustness | 737 | 107 | 0.145183 | 0.158672 | -0.013488 | pass |
| up150pct | robustness | 525 | 49 | 0.093333 | 0.103753 | -0.010419 | pass |
| up50pct | validation | 325 | 222 | 0.683077 | 0.736446 | -0.053369 | episode_context_exposure_caveat |
| up100pct | validation | 66 | 46 | 0.696970 | 0.775194 | -0.078224 | episode_context_exposure_caveat |
| up150pct | validation | 42 | 29 | 0.690476 | 0.768293 | -0.077816 | episode_context_exposure_caveat |

Finding：提高 winner threshold 没有消除 train/validation 的 late-rescue context exposure。因为这个 exposure 来自 episode duration/shape composition，而不是 up50 阈值单点选择。

## 12. Decision Rationale

16B ready 的理由：

1. 16A 授权可证明，sampling unit、primary horizon、split/stress 口径全部复验通过。
2. Step materialization 与 16A full-horizon step count 完全一致，partial tail 没有进入 labelable population。
3. qfq price source 与 price path completeness 全部通过。
4. Primary base rate 非退化，train/robustness stable，negative sample 不稀疏。
5. 15B hard taxonomy projection 可评估，coverage = 1.0；高 late-rescue exposure 已降级为 context caveat，而非 hard morphology fail。

剩余 caveat：

1. `known_failed_context_exposure_caveat = True`：train/validation h20 step population 对 late-rescue episode context 暴露较高。
2. `soft_overlap_partial_coverage_caveat = True`：15C2 soft membership coverage 不足，只能 appendix/readout 使用。
3. validation 是 stress split，h20 只有 664 个 step、41 个 cluster，不参与 primary stability gate。

## 13. Next Boundary

16B 只允许进入 `requirement_16c_sequential_continuation_separability_diagnostic.md`。16C 应复用 16A/16B 的 non-overlap full-horizon step population，并至少分层报告：

1. train/robustness/validation split performance；
2. late-rescue context vs non-late-rescue context；
3. threshold sensitivity；
4. no deployment / no entry / no model-training authorization leakage。

16B 本身仍不授权 entry、exit、holding、cost、portfolio、model training、separability search execution 或 label deployment。
