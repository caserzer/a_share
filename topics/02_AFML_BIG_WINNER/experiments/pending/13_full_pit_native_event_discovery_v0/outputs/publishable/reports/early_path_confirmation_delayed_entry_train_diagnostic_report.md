# 13F Early-Path Confirmation Delayed-Entry Train Diagnostic Report

## 1. 单行裁决

`decision_state = 13F_stop_no_delayed_utility_improvement`，`delayed_entry_capacity_readout = delayed_entry_no_utility_signal`。

13F 的主问题是：在 selected event `repair_range_participation_core_30` 触发后，先观察 early path，再延迟入场，能否在 train-fold 内改善 after-cost same-event utility。当前答案是否定的。主对照 `k=3 / horizon_mode_from_entry / arm_model_delayed` 的 fold-mean same-event utility 为 `0.002523`，低于 t0 baseline 的 `0.007136`，delta vs t0 为 `-0.004613`，只有 `2/5` 个 fold 为正；同时 `mean - std = -0.006069`，未通过硬经济 gate。

所有授权字段保持关闭：

| field | value |
|:--|:--|
| next_allowed_requirement | `none` |
| sequence_mining_authorized | `False` |
| meta_labeling_authorized | `False` |
| bet_sizing_authorized | `False` |
| confirmatory_status | `False` |
| validation_used_in_13f | `False` |
| robustness_used_in_13f | `False` |

13F 不推翻 13C/13E。13C/13E 否决的是 t0 winner entry / nonlinear winner capacity；13F 只检查一个更晚的 lifecycle 问题：event 发生后用 early path 做 confirmation，再 delayed entry 是否更好。结果显示：延迟确认没有把 event lift 转化成可用 entry utility。

## 2. 数据边界与审计

13F 使用 13C `morphology_residual_panel` 中 train split 且 selected-state membership 为真的事件，共 `6,232` 个 event。上游 13C/13E lineage、row-level rebuild、PIT early-path、delayed-entry executability、purged CV、exact-t1 uniqueness 均通过。

| gate | status |
|:--|:--|
| input_gate_status | `pass` |
| upstream_lineage_gate_status | `pass` |
| row_level_rebuild_gate_status | `pass` |
| early_path_pit_gate_status | `pass` |
| delayed_entry_executability_gate_status | `pass` |
| purged_cv_integrity_gate_status | `pass` |
| sample_uniqueness_gate_status | `pass_with_exact_t1` |
| search_accounting_status | `diagnostic_train_only_not_confirmatory` |

搜索空间显式记账为 `5 k values x 2 horizon modes x 3 arms = 30`。预注册主对照固定为 `k=3 / horizon_mode_from_entry / arm_model_delayed`；其余 29 个组合只作 sensitivity readout，不能升级 decision。

## 3. PIT Early Path 与 Delayed Entry

Early-path reconstruction 对全部 k 都可评价，且 label window 与 early-path window 不重叠；barrier 使用 t0-reference volatility，look-ahead column count 为 0。

| early_path_k | row_count | early_path_evaluable_n | label_window_disjoint_status | barrier_uses_t0_volatility_status | lookahead_column_count | early_path_pit_gate_status |
|---:|---:|---:|:--|:--|---:|:--|
| 2 | 6,232 | 6,232 | pass | pass | 0 | pass |
| 3 | 6,232 | 6,232 | pass | pass | 0 | pass |
| 5 | 6,232 | 6,232 | pass | pass | 0 | pass |
| 8 | 6,232 | 6,232 | pass | pass | 0 | pass |
| 13 | 6,232 | 6,232 | pass | pass | 0 | pass |

Delayed entry 的 PIT executability 不是主要失败来源。随着 k 增大，not-executable 和 missing label horizon 会增加，但比例仍低于 0.10 上限。

| k | horizon_mode | evaluable_n | not_executable_n | forward_shifted_entry_n | missing_label_horizon_n | not_executable_fraction | gate |
|---:|:--|---:|---:|---:|---:|---:|:--|
| 2 | calendar_t0 | 6,205 | 27 | 39 | 27 | 0.004332 | pass |
| 2 | from_entry | 6,205 | 27 | 39 | 27 | 0.004332 | pass |
| 3 | calendar_t0 | 6,196 | 36 | 36 | 36 | 0.005777 | pass |
| 3 | from_entry | 6,196 | 36 | 36 | 36 | 0.005777 | pass |
| 5 | calendar_t0 | 6,175 | 57 | 36 | 57 | 0.009146 | pass |
| 5 | from_entry | 6,175 | 57 | 36 | 57 | 0.009146 | pass |
| 8 | calendar_t0 | 6,153 | 79 | 37 | 79 | 0.012677 | pass |
| 8 | from_entry | 6,153 | 79 | 37 | 79 | 0.012677 | pass |
| 13 | calendar_t0 | 6,118 | 114 | 45 | 114 | 0.018293 | pass |
| 13 | from_entry | 6,118 | 114 | 45 | 114 | 0.018293 | pass |

Insight：13F 失败不是因为 delayed entry 无法成交或 PIT path 不可审计，而是因为 delayed arm 在同一 event 分母下没有超过 t0 baseline。换句话说，数据工程 gate 允许继续读数，但经济 gate 不允许推进。

## 4. 主对照 Gate Replay

主对照使用 50bps after-cost utility，全部 event 等权；delayed arm 未进场、not-executable、missed-upper 样本计 0 持仓收益，保留在同一分母。selected-entry utility 和 median utility 只作诊断，不替代主 gate。

| arm | fold_mean_utility_per_event_mean_50bps | fold_std | mean_minus_std | selected_entry_utility | median_utility | winner_rate | fast_fail_rate | selected_fraction | missed_upper_fraction | delta_vs_t0 | delta_vs_gate | positive_folds | status |
|:--|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--|
| t0_baseline | 0.007136 | 0.014067 | -0.006931 | 0.007136 | -0.011753 | 0.300483 | 0.058776 | 1.000000 | 0.040382 | 0.000000 | 0.004049 | 0 | no_improvement_vs_t0 |
| gate_delayed | 0.003087 | 0.010604 | -0.007517 | 0.003104 | -0.005000 | 0.274669 | 0.139019 | 0.960145 | 0.040382 | -0.004049 | 0.000000 | 1 | no_improvement_vs_t0 |
| model_delayed | 0.002523 | 0.008592 | -0.006069 | 0.005042 | 0.000000 | 0.304579 | 0.176150 | 0.500132 | 0.040382 | -0.004613 | -0.000565 | 2 | no_improvement_vs_t0 |

硬 gate 要求 `mean > 0`、`delta_vs_t0 > 0`、`mean - std > 0`、`positive_folds >= 3/5`。`arm_model_delayed` 虽然 mean 为正，但 `delta_vs_t0 < 0`、`mean - std < 0`、positive folds 只有 2/5，因此不能形成 delayed-entry utility signal。`arm_gate_delayed` 同样低于 t0，说明“单纯等几天剔除早期下轨”也不够。

## 5. Fold-Level 细节

主对照下，t0 baseline 在 fold 0/2/4 表现强，delayed arm 反而削弱了这些 fold 的收益；fold 1/3 的 t0 baseline 本身为负，delayed model 在 same-event 分母下有局部改善，但不足以抵消正收益 fold 中错过 winner 的损失。

| fold | arm | event_n | evaluable_n | selected_n | selected_fraction | winner_rate | fast_fail_rate | utility_per_event_50bps | selected_entry_utility_50bps | missed_upper_n | early_lower_n |
|---:|:--|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | t0_baseline | 2,091 | 2,091 | 2,091 | 1.000000 | 0.359637 | 0.043042 | 0.014657 | 0.014657 | 81 | 49 |
| 0 | gate_delayed | 2,091 | 2,080 | 2,031 | 0.971306 | 0.330871 | 0.129985 | 0.010822 | 0.011142 | 81 | 49 |
| 0 | model_delayed | 2,091 | 2,080 | 1,046 | 0.500239 | 0.392925 | 0.130019 | 0.010788 | 0.021565 | 81 | 49 |
| 1 | t0_baseline | 1,656 | 1,656 | 1,656 | 1.000000 | 0.207126 | 0.068237 | -0.010764 | -0.010764 | 24 | 74 |
| 1 | gate_delayed | 1,656 | 1,653 | 1,579 | 0.953502 | 0.196327 | 0.134262 | -0.011765 | -0.012339 | 24 | 74 |
| 1 | model_delayed | 1,656 | 1,653 | 828 | 0.500000 | 0.182367 | 0.159420 | -0.008829 | -0.017657 | 24 | 74 |
| 2 | t0_baseline | 1,195 | 1,195 | 1,195 | 1.000000 | 0.373222 | 0.050209 | 0.018892 | 0.018892 | 94 | 30 |
| 2 | gate_delayed | 1,195 | 1,182 | 1,153 | 0.964854 | 0.302689 | 0.188205 | 0.006773 | 0.007019 | 94 | 30 |
| 2 | model_delayed | 1,195 | 1,182 | 598 | 0.500418 | 0.337793 | 0.257525 | 0.004234 | 0.008460 | 94 | 30 |
| 3 | t0_baseline | 504 | 504 | 504 | 1.000000 | 0.202381 | 0.085317 | -0.005286 | -0.005286 | 9 | 26 |
| 3 | gate_delayed | 504 | 497 | 472 | 0.936508 | 0.211864 | 0.135593 | -0.003854 | -0.004116 | 9 | 26 |
| 3 | model_delayed | 504 | 497 | 252 | 0.500000 | 0.210317 | 0.178571 | -0.003655 | -0.007309 | 9 | 26 |
| 4 | t0_baseline | 786 | 786 | 786 | 1.000000 | 0.360051 | 0.047074 | 0.018181 | 0.018181 | 41 | 18 |
| 4 | gate_delayed | 786 | 784 | 766 | 0.974555 | 0.331593 | 0.107050 | 0.013461 | 0.013812 | 41 | 18 |
| 4 | model_delayed | 786 | 784 | 393 | 0.500000 | 0.399491 | 0.155216 | 0.010075 | 0.020150 | 41 | 18 |

两个细节很重要：

1. `model_delayed` 在 fold 0/4 的 selected-entry utility 很高（0.021565 / 0.020150），但 same-event utility 仍低于 t0 baseline，因为它只选择约一半事件，未选事件计 0。
2. `model_delayed` 的 winner_rate 在 fold 0/4 高于 t0，但 fast_fail_rate 也显著高于 t0。early path 确认并没有稳定地压低失败侧，反而常把持仓集中到更高波动的 continuation 子集。

## 6. Sensitivity：不同 k 与 horizon 的读数

所有非主对照组合都不能改变 decision。读数上看，较长 k 的 model arm 有时优于 gate arm，但仍没有优于 t0 baseline；并且 k 越长，missed-upper 的机会成本越明显。

| k | best_model_utility | best_delta_vs_t0 | best_delta_vs_gate | missed_upper_fraction | not_executable_n | not_executable_fraction | shifted_n | max_evaluable_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 0.002247 | -0.004889 | -0.001817 | 0.021499 | 27 | 0.004332 | 39 | 6,205 |
| 3 | 0.002523 | -0.004613 | -0.000466 | 0.040382 | 36 | 0.005777 | 36 | 6,196 |
| 5 | 0.002359 | -0.004777 | 0.001280 | 0.084033 | 57 | 0.009146 | 36 | 6,175 |
| 8 | -0.000536 | -0.007672 | 0.001600 | 0.146587 | 79 | 0.012677 | 37 | 6,153 |
| 13 | -0.002562 | -0.009698 | 0.003652 | 0.230275 | 114 | 0.018293 | 45 | 6,118 |

Model arm sensitivity 明细：

| k | horizon_mode | model_utility | fold_std | delta_vs_t0 | delta_vs_gate | positive_folds | missed_upper_fraction | selected_fraction | status |
|---:|:--|---:|---:|---:|---:|---:|---:|---:|:--|
| 2 | calendar_t0 | 0.001539 | 0.007895 | -0.005597 | -0.001817 | 1 | 0.021499 | 0.500132 | no_improvement_vs_t0 |
| 2 | from_entry | 0.002247 | 0.008059 | -0.004889 | -0.002096 | 2 | 0.021499 | 0.500132 | no_improvement_vs_t0 |
| 3 | calendar_t0 | 0.001635 | 0.007430 | -0.005501 | -0.000466 | 2 | 0.040382 | 0.500132 | no_improvement_vs_t0 |
| 3 | from_entry | 0.002523 | 0.008592 | -0.004613 | -0.000565 | 2 | 0.040382 | 0.500132 | no_improvement_vs_t0 |
| 5 | calendar_t0 | 0.001973 | 0.005480 | -0.005163 | 0.001280 | 2 | 0.084033 | 0.500132 | no_improvement_vs_t0_and_gate |
| 5 | from_entry | 0.002359 | 0.006716 | -0.004777 | 0.000700 | 2 | 0.084033 | 0.500132 | no_improvement_vs_t0_and_gate |
| 8 | calendar_t0 | -0.000850 | 0.003202 | -0.007986 | 0.001600 | 1 | 0.146587 | 0.500132 | no_improvement_vs_t0_and_gate |
| 8 | from_entry | -0.000536 | 0.004557 | -0.007672 | 0.001386 | 1 | 0.146587 | 0.500132 | no_improvement_vs_t0_and_gate |
| 13 | calendar_t0 | -0.004021 | 0.002984 | -0.011157 | 0.003019 | 2 | 0.230275 | 0.500132 | no_improvement_vs_t0_and_gate |
| 13 | from_entry | -0.002562 | 0.002766 | -0.009698 | 0.003652 | 2 | 0.230275 | 0.500132 | no_improvement_vs_t0_and_gate |

Insight：更长的 early path 会让模型相对 gate 看起来更好（例如 k=13/from_entry 的 delta_vs_gate = 0.003652），但这只是“在更差的延迟门控基准上少输一点”。相对于 t0 baseline，所有 model 组合都是负 delta。k 增长还把 missed_upper_fraction 从 `0.021499` 推高到 `0.230275`，说明延迟确认正在系统性错过一部分早涨 winner。

## 7. Missed-Winner 会计

主对照 `k=3/from_entry` 下，early path 内触上轨的 missed-upper 共 `249` 个事件（fold 分布为 81 / 24 / 94 / 9 / 41），fold-mean missed_upper_fraction 为 `0.040382`。这部分没有被剔除出分母；delayed arm 对未持仓样本计 0，并单独记录 opportunity cost。

| fold | arm | event_n | missed_upper_n | early_lower_n | missed_upper_fraction | missed_upper_opportunity_cost | same_event_delta_vs_t0 | selected_entry_delta_vs_t0 | offset_gate |
|---:|:--|---:|---:|---:|---:|---:|---:|---:|:--|
| 0 | t0_baseline | 2,091 | 81 | 49 | 0.038737 | 0.000000 | 0.000000 | 0.000000 | fail |
| 0 | gate_delayed | 2,091 | 81 | 49 | 0.038737 | 0.002544 | -0.003834 | -0.003514 | fail |
| 0 | model_delayed | 2,091 | 81 | 49 | 0.038737 | 0.002942 | -0.003869 | 0.006908 | fail |
| 1 | t0_baseline | 1,656 | 24 | 74 | 0.014493 | 0.000000 | 0.000000 | 0.000000 | fail |
| 1 | gate_delayed | 1,656 | 24 | 74 | 0.014493 | 0.002221 | -0.001001 | -0.001574 | fail |
| 1 | model_delayed | 1,656 | 24 | 74 | 0.014493 | 0.002221 | 0.001936 | -0.006893 | pass |
| 2 | t0_baseline | 1,195 | 94 | 30 | 0.078661 | 0.000000 | 0.000000 | 0.000000 | fail |
| 2 | gate_delayed | 1,195 | 94 | 30 | 0.078661 | 0.009804 | -0.012120 | -0.011873 | fail |
| 2 | model_delayed | 1,195 | 94 | 30 | 0.078661 | 0.009804 | -0.014659 | -0.010432 | fail |
| 3 | t0_baseline | 504 | 9 | 26 | 0.017857 | 0.000000 | 0.000000 | 0.000000 | fail |
| 3 | gate_delayed | 504 | 9 | 26 | 0.017857 | 0.002445 | 0.001431 | 0.001170 | pass |
| 3 | model_delayed | 504 | 9 | 26 | 0.017857 | 0.002445 | 0.001631 | -0.002023 | pass |
| 4 | t0_baseline | 786 | 41 | 18 | 0.052163 | 0.000000 | 0.000000 | 0.000000 | fail |
| 4 | gate_delayed | 786 | 41 | 18 | 0.052163 | 0.004483 | -0.004720 | -0.004369 | fail |
| 4 | model_delayed | 786 | 41 | 18 | 0.052163 | 0.004533 | -0.008106 | 0.001969 | fail |

Insight：selected-entry utility 的局部改善不能直接转成仓位放大逻辑。fold 0 和 fold 4 的 model selected-entry delta 为正，但 same-event delta 仍显著为负；这说明模型可以挑出一些“看起来更顺”的 delayed entries，但它放弃的同分母事件中包含足够多的 t0 winner，导致组合层面净损失。

## 8. Sample Uniqueness / Overlap

13F 使用 13F max observable event span 重算 exact-t1 uniqueness，而不是只用 t0 first-touch span。所有 fold 均为 `pass_with_exact_t1`。

| fold | event_n | purged_rows_n | embargoed_rows_n | effective_train_event_n | train_mean_uniqueness | train_p10_uniqueness | train_mean_concurrency | train_p95_concurrency | test_mean_uniqueness | test_mean_concurrency |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2,091 | 84 | 85 | 3,972 | 0.345265 | 0.138858 | 4.630244 | 10.0 | 0.318657 | 5.081908 |
| 1 | 1,656 | 299 | 642 | 3,635 | 0.331039 | 0.126912 | 4.944367 | 11.0 | 0.340012 | 4.651746 |
| 2 | 1,195 | 171 | 167 | 4,699 | 0.331183 | 0.132799 | 4.833208 | 11.0 | 0.342708 | 4.748905 |
| 3 | 504 | 115 | 362 | 5,251 | 0.332340 | 0.130445 | 4.859496 | 11.0 | 0.460395 | 3.316412 |
| 4 | 786 | 18 | 61 | 5,367 | 0.331268 | 0.130399 | 4.857050 | 11.0 | 0.346783 | 4.603817 |

Overlap 风险被审计到位，但不是本次失败原因。train mean uniqueness 稳定在 `0.331-0.345`，p95 concurrency 为 `10-11`，说明样本重叠存在但已在 purged/embargoed fold 与 fold-local uniqueness weight 中显式处理。

## 9. Findings

1. **延迟确认没有形成 entry edge。** 主 model arm 的 same-event utility 虽为正，但低于 t0 baseline；这意味着 early-path confirmation 不能直接把 event lift 转为可交易 entry utility。
2. **模型读数更像 participation filter，而不是 alpha。** model arm 约选择 50% 事件，selected-entry utility 在部分 fold 看起来更好，但全分母 utility 下降。AFML 口径下，不能只看被选中的成交子集。
3. **更长等待会放大 missed-winner 成本。** k 从 2 到 13 时，missed_upper_fraction 从 `0.021499` 升到 `0.230275`。等待越久，越容易把早涨 winner 排除在持仓之外。
4. **PIT/executability 不是瓶颈。** k=3 主口径 not-executable 只有 `36/6232 = 0.005777`；即使严格按 PIT executable open 处理，结论仍是经济性失败。
5. **fold 异质性支持 stop，而不是推进。** delayed model 在 fold 1/3 有局部 same-event 改善，但在 fold 0/2/4 显著落后 t0。正负 fold 不稳定，且没有通过 mean-minus-std gate。
6. **13C/13E 的方向没有被 13F 反驳。** 13C/13E 已显示 t0 winner entry / nonlinear winner model 不具备可靠 utility；13F 进一步说明“等 early path 确认后再入场”也没有修复 utility 问题。

## 10. Insight 与后续边界

当前证据不支持把这个 event 用作 meta-labeling 后的加仓/减仓开关。原因不是 event 完全没有 lift，而是 lift 在进入交易口径后被三个因素消耗：同分母未进场样本计 0、早涨 winner 被延迟错过、fold 间表现不稳定。AFML 上应把它归类为“有形态信息但未通过 utility gate 的 diagnostic signal”，而不是 winner-entry alpha。

如果未来还要研究，应该先换问题定义，而不是在 13F 上继续调 k 或调模型。更合理的方向是把 event 当作风险预算的候选条件之前，另开独立 confirmatory requirement，并在未触碰的 OOS 上验证“风险预算调整”本身的 utility；13F 当前结果不授权这个推进，也不授权 sequence mining、meta-labeling、bet sizing、holding/exit/profit-protection policy。

最终解释：13F 的 negative 是 **no delayed utility improvement**，不是 PIT failure、not-executable failure、CV integrity failure 或 uniqueness failure。
