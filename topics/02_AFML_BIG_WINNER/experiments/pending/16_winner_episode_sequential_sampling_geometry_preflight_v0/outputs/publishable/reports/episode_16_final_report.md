# Episode 16 Final Report: Sequential Continuation Line Closure

## 0. Closure Decision

本报告正式关闭 Episode 16：

```text
episode_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
closure_state = EP16_closed_no_next_requirement
closure_date = 2026-06-29
next_allowed_requirement = none
continuation_as_action_mainline_closed = true
payoff_aligned_label_redo_authorized = false
16F_chained_action_transition_freeze_authorized = false
16B2_payoff_aligned_label_redesign_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

Episode 16 的最终判断是：sequential continuation 这条研究线证明了“持有中 survival / drawdown risk 有可分性”，但没有证明“该可分性可以转化为正的单步 utility”，也没有证明“把 target 改成 payoff severity 后，在现有 t0 feature contract 下具备可确认的 OOS payoff rank separability”。因此不写 16F，不写 16B2，不继续 A/B/C 修补路径；后续应回到 topic-level research direction，而不是在 Episode 16 内继续追加 phase。

## 1. Research Question

Episode 16 从 Episode 15 的失败中切换问题定义。Episode 15 已证明：winner morphology 不是可在 t0 稳定预测的离散形态，anchor 也不是独立样本单元。Episode 16 因此不再问“t0 能不能预测整段 winner path”，而是问：

```text
如果只在持有过程中一段一段判断是否继续参与，
能否先用 non-overlap sequential sampling 建立有效样本，
再用 continuation label / score / policy / utility 形成可审计的 continuation-as-action 链？
```

这条链的逻辑要求很强：采样几何必须成立，label 必须非平凡，t0 状态必须能区分 survival，policy 必须能捕获 negative，utility 必须在 cost 后为正，最后才可能进入 chained simulation。Episode 16 走完整条链后，最终停在 utility 和 payoff separability 两个层面。

## 2. Phase Decision Ledger

| Phase | Decision | Next allowed | Status for Ep16 closure |
| --- | --- | --- | --- |
| 16A Sampling Geometry | `16A_sampling_geometry_ready_for_sequential_label_design` | 16B | 采样地基可用，但必须用 non-overlap / episode-cluster discipline，不能再用 anchor 当独立样本。 |
| 16B Label Design | `16B_continuation_label_ready_for_separability_diagnostic` | 16C | `up50pct` / h20 survival label 有非平凡 base rate，可进入 separability。 |
| 16C Separability | `16C_sequential_continuation_separability_ready_for_policy_preflight` | 16D | 16C frozen t0 feature 对 survival label 有 OOS separability，但不授权部署。 |
| 16D Policy Preflight | `16D_policy_preflight_ready_for_utility_diagnostic` | 16E | bottom-30% continuation score 能富集 negative，可进入单步 utility。 |
| 16E Utility Diagnostic | `16E_utility_diagnostic_not_supported` | none | drawdown avoidance 成立，但 net return utility 失败，不授权 16F。 |
| 16E-postmortem | `16E_postmortem_mainline_closed_no_path_supported` | none | A/B/C 三条在 survival score 上修补的路径全部关闭。 |
| 16X Payoff Precheck | `16X_payoff_precheck_not_supported` | none | payoff-aligned label redesign 起点也不授权；Ep16 正式关闭。 |

## 3. 16A - Sampling Geometry Was Necessary And Correct

16A 的贡献是把 Episode 16 从一开始就限制在正确的统计单元上。`up50pct` / h20 primary geometry 显示 anchor 严重高估独立样本量：

| split | anchor_n | episode_cluster_n | full_horizon_nonoverlap_step_n | effective_to_anchor_ratio | anchor_overcount_weighted |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 57,524 | 667 | 20,245 | 0.351940 | 2.756169 |
| robustness | 11,302 | 218 | 2,496 | 0.220846 | 4.175102 |
| validation | 1,083 | 45 | 664 | 0.613112 | 1.529661 |

16A 的结论不是“样本很多”，而是“只有在 non-overlap time-blocked sampling geometry 下才可继续”。这一步正确地阻止了后续用 raw anchor count 夸大功效。

## 4. 16B - Continuation Label Was Non-trivial

16B 选择的 primary label 是：

```text
primary_label_id = continuation_survival_h20_no_deep_drawdown
selected_threshold_id = up50pct
primary_horizon_sessions = 20
```

该 label 在三个 split 都不是退化标签，且 neutral rows 占比稳定，必须在后续作为独立人群处理：

| split | labelable_step_n | positive_n | negative_n | neutral_n | positive_rate | negative_rate | neutral_rate | episode_cluster_n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 20,245 | 10,078 | 4,884 | 5,283 | 0.497802 | 0.241245 | 0.260953 | 652 |
| robustness | 2,496 | 1,346 | 526 | 624 | 0.539263 | 0.210737 | 0.250000 | 204 |
| validation | 664 | 325 | 180 | 159 | 0.489458 | 0.271084 | 0.239458 | 41 |

这一步通过是合理的：continuation survival label 有足够正负样本，也没有把 neutral 偷换成 positive 或 negative。但 16B 只证明 label form 可用于 separability，不证明这个 label 的 action utility。

## 5. 16C - Survival Separability Was Real

16C 在 16B 的 frozen label universe 上训练 `ridge_logistic_bar_state_v1`，使用 27 个 primary features。主要结果：

| split | binary_step_n | positive_n | negative_n | episode_cluster_n | ROC-AUC | average_precision | PR lift | rank_ic_spearman |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 14,962 | 10,078 | 4,884 | 652 | 0.680264 | 0.800662 | 0.127089 | 0.292809 |
| robustness | 1,872 | 1,346 | 526 | 204 | 0.672220 | 0.818200 | 0.099183 | 0.268154 |
| validation | 505 | 325 | 180 | 40 | 0.610632 | 0.712213 | 0.068648 | 0.183553 |

16C 的结论也成立：t0 observable state 对“下一 h20 是否 survival / no deep drawdown”有 OOS separability。这个结论后来没有被推翻；被推翻的是“survival separability 足以产生正 utility”的假设。

## 6. 16D - Policy Could Enrich Negative Cases, But With Visible Tradeoff

16D 把 16C score 冻结为 bottom-30% defend-vs-continue diagnostic policy：

```text
primary_policy_id = defense_bottom_30pct_continuation_score_v1
threshold_value = 0.457071
candidate_action = defend_next_h20 vs continue_next_h20
```

Policy preflight 的核心 tradeoff：

| split | defense_rate | defended_negative_n / negative_n | negative_capture_rate | defended_positive_n / positive_n | positive_sacrifice_rate | defense_precision | precision_lift | leakage_rate |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| train | 0.300027 | 2,299 / 4,884 | 0.470721 | 2,190 / 10,078 | 0.217305 | 0.512141 | +0.185714 | 0.529279 |
| robustness | 0.212073 | 196 / 526 | 0.372624 | 201 / 1,346 | 0.149331 | 0.493703 | +0.212720 | 0.627376 |
| validation | 0.312871 | 81 / 180 | 0.450000 | 77 / 325 | 0.236923 | 0.512658 | +0.156223 | 0.550000 |

16D 是 Episode 16 最容易被误读的一步。它的确证明了 score 能富集 negative：robustness defense precision `49.37%`，相对 binary negative base rate `28.10%` 有 `+21.27pp` lift。但它同时暴露了两个后续必须付账的问题：

1. robustness 仍有 `62.74%` negative 被 continue，residual leakage 很高；
2. robustness 有 `201` 个 positive 被 defend，positive sacrifice 不可忽略。

因此 16D 只能授权 16E utility diagnostic，不能授权任何 trading action。

## 7. 16E - Utility Failed Despite Drawdown Avoidance

16E 第一次把 diagnostic action 放入 return / drawdown / cost 口径。Primary semantics 是：

```text
primary_action_semantics_id = full_avoidance_cash_h20_close_to_close_v1
primary_round_trip_defense_cost_bps = 50
```

主裁决：

```text
decision_state = 16E_utility_diagnostic_not_supported
utility_interpretation = drawdown_reduction_only_return_not_supported
next_allowed_requirement = none
```

50bps primary readout：

| split | labelable_step_n | defended_step_n | full_denominator_sum_incremental_return | full_denominator_mean_incremental_return | defended_positive_incremental_sum | defended_negative_incremental_sum | defended_neutral_incremental_sum | defended_negative_drawdown_avoided_mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 20,245 | 5,584 | -46.892550 | -0.002316 | -331.207522 | +242.167136 | +42.147836 | 0.166858 |
| robustness | 2,496 | 486 | -13.800725 | -0.005529 | -32.499665 | +15.693211 | +3.005729 | 0.164024 |
| validation | 664 | 183 | -3.858970 | -0.005812 | -13.214871 | +8.321611 | +1.034291 | 0.158338 |

16E 的失败不是因为 drawdown 没有被规避。Robustness defended negative 的 mean drawdown avoided 为 `0.164024`，drawdown avoidance gate 通过。失败来自 return utility：robustness 中 defended positive 的 opportunity cost `-32.499665`，明显大于 defended negative 带来的 `+15.693211`，neutral 只补回 `+3.005729`，全分母 net utility 仍为 `-13.800725`。

Continued negative leakage 进一步压低 utility：

| split | continued_negative_n | continued_negative_return_sum | continued_negative_mean_return | residual_loss_abs | defended_negative_avoided_loss_abs | residual_loss_share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 2,585 | -265.689063 | -0.102781 | 279.257036 | 277.321853 | 1.006978 |
| robustness | 330 | -32.159819 | -0.097454 | 33.661775 | 20.513371 | 1.640967 |
| validation | 99 | -10.740722 | -0.108492 | 11.137834 | 9.365627 | 1.189225 |

16E 因此不授权 16F。继续写 chained simulation 只会把一个单步负 utility action 复杂化。

## 8. 16E-postmortem - Root Cause Was Target / Utility Directionality Mismatch

16E-postmortem 的作用是解释 16E 为什么失败，并检查 survival score 上是否存在可修补路径。最终裁决：

```text
decision_state = 16E_postmortem_mainline_closed_no_path_supported
next_allowed_requirement = none
continuation_as_action_mainline_closed = true
selected_path_id = none
directionality_gate = fail
path_a_supported = false
path_b_supported = false
path_c_supported = false
```

Score decile readout 是整个 Episode 16 的根因证据：

| split | monotonicity_spearman | monotone_increasing_flag | non_monotone_flag | interpretation |
| --- | ---: | ---: | ---: | --- |
| train | 0.903030 | 1 | 0 | train 上 survival score 与 mean continue return 大体同向。 |
| robustness | 0.030303 | 0 | 1 | robustness 上 survival score 与 realized payoff magnitude 解耦。 |

Robustness decile 形态：

| decile | base_rate_positive | mean_continue_return_h20 | mean_continue_max_drawdown |
| ---: | ---: | ---: | ---: |
| 1 | 0.425926 | 0.015835 | -0.103641 |
| 2 | 0.593750 | 0.028537 | -0.078375 |
| 3 | 0.700508 | 0.051686 | -0.064148 |
| 4 | 0.704301 | 0.045478 | -0.062881 |
| 5 | 0.747312 | 0.056383 | -0.054770 |
| 6 | 0.758427 | 0.029904 | -0.053461 |
| 7 | 0.815029 | 0.032479 | -0.048119 |
| 8 | 0.815217 | 0.029869 | -0.046965 |
| 9 | 0.829670 | 0.026453 | -0.041956 |
| 10 | 0.870787 | 0.032262 | -0.036095 |

这张表说明 score 在 robustness 上仍能区分 survival probability：positive base rate 从 D1 的 `42.59%` 升到 D10 的 `87.08%`。但 realized return 在 D5 达到 `5.64%` 后回落，D10 只有 `3.23%`。分类概率和收益幅度不是同一个目标。对 AFML 来说，这意味着 survival score 可以是 risk state / participation filter 的候选证据，但不能直接作为 payoff-maximizing continuation action。

Postmortem 同时排除了三条修补路径：

| Candidate path | Required idea | Result |
| --- | --- | --- |
| A: utility-weighted objective | 在现有 survival score 上改 objective / weighting | directionality gate fail，不能授权。 |
| B: overlay risk budget | 把 signal 当 risk-budget overlay | directionality gate fail，且 partial exposure feasibility hint false。 |
| C: participation filter | 把 continuation score 降级成 meta filter | directionality gate fail，当前 readout 不支持。 |

Thick-tail mismatch 为 true，说明 defended positives 还偏向 high-upside positive；robustness defended-positive upside mean ratio 为 `1.312713`，q75 ratio 为 `1.396627`。这强化了 utility 失败：错防的不是普通 positive，而是更厚尾的 positive。

## 9. 16X - Payoff Target Redesign Was Also Not Supported

16X 是在 postmortem 关闭 survival-score 修补路径后，做的唯一 restart precheck。它只问一个问题：如果 target 直接换成 realized h20 payoff severity，现有 16C frozen t0 feature contract 是否有足够 OOS payoff rank separability？

Hard gates 均通过：

| gate | status | evidence |
| --- | --- | --- |
| upstream_postmortem_authorization_gate | pass | 16E-postmortem 已关闭主线。 |
| feature_contract_gate | pass | expected 27 features，actual 27；forbidden feature used = 0。 |
| payoff_target_lineage_gate | pass | payoff base 来自 `step_end_price_ratio_minus_one_for_label_rule`，不重算价格。 |
| power_gate | pass | train 14,962 rows / 652 clusters；robustness 1,872 rows / 204 clusters。 |
| search_accounting_gate | pass | no 16C refit，no validation selection，no robustness tuning。 |

但 payoff separability gate 失败：

| metric | observed | required | status |
| --- | ---: | ---: | --- |
| robustness payoff rank IC | 0.051877 | >= 0.060000 | fail |
| payoff decile monotonicity Spearman | 0.163636 | >= 0.600000 | fail |
| payoff - survival rank IC margin | -0.000723 | > +0.030000 | fail |
| train CV payoff rank IC median | 0.176200 | >= 0.060000 | pass |
| robustness cluster-bootstrap CI excludes zero | [0.007706, 0.097324] | low > 0 | pass |

Rank IC 对比：

| split | survival_probe_rank_ic | payoff_probe_rank_ic | payoff_minus_survival |
| --- | ---: | ---: | ---: |
| train | 0.157138 | 0.186701 | +0.029563 |
| robustness | 0.052600 | 0.051877 | -0.000723 |
| validation | 0.084679 | 0.075871 | -0.008808 |

16X 的结论需要精确表述：payoff target 不是完全没有弱信号，bootstrap CI 排除了 0；但信号太弱、不单调、且没有超过 survival probe。也就是说，“把 label 改成 payoff severity”并没有在当前 t0 feature contract 下形成可确认的 OOS payoff ranking edge。因此不授权 16B2。

## 10. Final Findings

**Finding 1 - Sequential sampling discipline 是成功的。**

16A 正确证明了 anchor 不能作为独立样本。后续所有 phase 都继承 non-overlap / episode-cluster discipline，这避免了 Episode 15 中 anchor overcount 导致的功效幻觉。

**Finding 2 - Survival / drawdown-risk separability 是真实但不够的。**

16C 和 16D 没有失败。16C 的 robustness ROC-AUC `0.672220`，16D 的 robustness defense precision lift `+21.27pp`，说明持有中状态确实包含 survival / negative-risk 信息。但 AFML 决策需要的是 payoff / utility ordering，而不是 survival 0/1 classification 本身。

**Finding 3 - Utility 失败来自 payoff target mismatch，不是简单成本过高。**

16E 在 drawdown avoided 上表现稳定，robustness defended-negative drawdown avoided mean `0.164024`。但错防 positive 的损失更大：robustness defended-positive incremental `-32.499665`，defended-negative incremental `+15.693211`。即使不把问题归咎于成本，gross opportunity cost 也已经压过 avoided loss。

**Finding 4 - Survival score 在 OOS 上不具备 payoff directionality。**

Robustness 上 base_rate_positive 随 score 上升，但 mean continue return 不随 score 上升。这个事实关闭了“在现有 survival score 上调 threshold / 加 overlay / 降级 filter”的主线。

**Finding 5 - Payoff-aligned target redesign 没有通过最小功效预检。**

16X 已经给了 payoff target 一次公平机会：同一 16C feature contract、固定低容量 probe、robustness confirmatory split、cluster-bootstrap。结果 payoff rank IC `0.051877` 低于 floor，decile monotonicity `0.163636`，且不优于 survival probe。这关闭了在 Episode 16 内启动 16B2 重链的理由。

**Finding 6 - Episode 16 的可保留资产是诊断纪律，不是可交易 continuation action。**

可保留的资产包括：non-overlap sequential sampling geometry、neutral rows 独立处理、survival-score risk readout、six-cell utility reconciliation、postmortem directionality gate、payoff precheck gate。不可保留为生产信号的是 defend_next_h20 action、bottom-30% threshold、survival score continuation policy、payoff probe score。

## 11. Closure Rules Going Forward

Episode 16 关闭后，以下事项在本 episode 内不应继续生成 requirement：

1. 不写 `requirement_16f_chained_action_transition_freeze.md`。
2. 不写 `requirement_16b2_payoff_aligned_continuation_label_design_diagnostic.md`。
3. 不重启 postmortem A/B/C 路径。
4. 不把 `defense_bottom_30pct_continuation_score_v1` 解释成 entry / exit / holding policy。
5. 不把 16C / 16D survival score 当 production signal。
6. 不在当前 16C t0 feature contract 上继续调 threshold、cost tier、delay stress 或 utility accounting 来寻求授权。

后续若继续研究，应作为新的 topic-level direction，而不是 Episode 16 continuation：

| Possible direction | Why outside Ep16 |
| --- | --- |
| Entry alpha / earlier payoff state | 当前 bottleneck 是 payoff magnitude OOS separability，不是 continuation action accounting。 |
| New t0 payoff-state representation | 16X 说明现有 16C feature contract 不足以 rank payoff severity。 |
| Non-action risk state readout | Survival score 可作为风险状态诊断，但不能直接部署为 continuation action。 |
| New episode framing outside winner-continuation | Episode 15/16 共同说明 morphology / continuation 两条 path 都不能直接产出 action chain。 |

## 12. Source Artifact Index

本 final report 汇总以下 publishable reports / manifests / tables；它不替代各 phase 自己的 manifest。

| Phase | Report | Manifest | Key decision table |
| --- | --- | --- | --- |
| 16A | `sequential_sampling_geometry_preflight_report.md` | `16A_sequential_sampling_geometry_preflight_manifest.json` | `sampling_geometry_decision.csv` |
| 16B | `sequential_continuation_label_design_diagnostic_report.md` | `16B_sequential_continuation_label_design_diagnostic_manifest.json` | `sequential_continuation_label_decision.csv` |
| 16C | `sequential_continuation_separability_diagnostic_report.md` | `16C_sequential_continuation_separability_diagnostic_manifest.json` | `sequential_continuation_separability_decision.csv` |
| 16D | `sequential_continuation_policy_preflight_report.md` | `16D_sequential_continuation_policy_preflight_manifest.json` | `sequential_continuation_policy_preflight_decision.csv` |
| 16E | `sequential_continuation_utility_diagnostic_report.md` | `16E_sequential_continuation_utility_diagnostic_manifest.json` | `sequential_continuation_utility_decision.csv` |
| 16E-postmortem | `continuation_utility_failure_postmortem_report.md` | `16E_postmortem_continuation_utility_failure_decomposition_manifest.json` | `continuation_utility_failure_postmortem_decision.csv` |
| 16X | `payoff_aligned_continuation_label_power_precheck_report.md` | `16X_payoff_aligned_continuation_label_power_precheck_manifest.json` | `payoff_aligned_label_power_precheck_decision.csv` |

## 13. Final Statement

Episode 16 is closed.

它证明了一个重要但负面的研究结论：在当前 Big Winner local proxy、当前 episode sampling discipline、当前 16C frozen t0 feature contract 下，sequential continuation survival score 可以识别一部分 drawdown / negative-risk state，但不能形成正的 continuation-as-action utility；进一步把 target 改成 realized payoff severity 也没有通过 robustness payoff separability precheck。

因此，Episode 16 不再产生后续 implementation requirement。任何后续研究必须从新的 topic-level hypothesis 开始，并把 Episode 16 的关闭证据作为前置约束。
