# EP5 R04 最终报告：GTJA191 短周期残差等权合成可行性 V0

## 1. 最终结论

R04 在修订后的 small-universe contract 下已经从“数据契约阻断”变成“可评价后的不支持”。

| item | value |
|:--|:--|
| final_decision | `r04_no_gtja191_residual_composite_support` |
| priority_rule | `rule_18` |
| H10 quadrant | `absolute_false__relative_false` |
| validator | `passed`, 19 / 19 gates |
| primary conclusion | GTJA191 train-only direction 等权合成没有给出可报告的 H10 long-only alpha 或 residual selection support |

这次不是因为 `eligible_count < 300` 被阻断。R04 已明确接受 small-universe 统计代价，并在 validation / robustness 上生成了 selected events、execution events、matched comparator、nonselected baseline 和 horizon summaries。

关键 H10 validation 事实：

| metric | value |
|:--|--:|
| signal_event_count | 4,511 |
| complete_event_count | 4,271 |
| complete_event_share | 94.68% |
| decision_observation_date_count | 96 |
| sample_status | `pass` |
| mean_net_return | -1.3210% |
| median_net_return | -1.8517% |
| p10_net_return | -10.1073% |
| loss_rate | 61.20% |
| mean_matched_delta_return | 0.1332% |
| median_matched_delta_return | -0.4001% |
| p10_matched_delta_return | -7.7316% |
| matched_loss_rate_delta | -9.0845% |
| mean_baseline_lift | 0.0614% |
| median_baseline_lift | -0.1028% |

H10 样本门、date-independence、active-overlap、baseline evaluability 都足够进入评价，但收益形态没有通过：

| gate | value | interpretation |
|:--|:--:|:--|
| sample_gate_pass | true | 样本量与日期覆盖足够 |
| active_overlap_gate | true | H10 独立 active-entry clusters 足够 |
| date_independence_gate | true | 日期覆盖与日期集中度通过 |
| absolute_positive | false | 绝对收益形态失败 |
| relative_positive | false | matched residual 形态失败 |
| baseline_lift_gate | false | baseline lift 中位数和年度稳定性不足 |
| robustness_confirmed | false | robustness H10 没有确认 |
| adjacent_horizon_clean | false | adjacent horizon 未形成干净支持 |

因此，最终 `rule_18` 是合理结论：没有任何高优先级规则能支持 residual composite 继续研究、relative-only 研究、absolute-only 解释或 horizon-specific lead。

## 2. 实验边界

本轮仍保留 R04 的硬边界：

- R04 did not perform validation-driven factor selection.
- R04 did not use IC weighting, t-stat weighting, model weighting, dynamic weighting, or top-fraction tuning.
- R04 used train-only direction signs, equal weights across nonzero-direction available factors, and fixed top 20% selection.
- R04 did not use big-winner or right-tail readouts as pass/fail gates.

本轮修订只改变数据契约和统计评价口径：

| revised item | value |
|:--|--:|
| `min_eligible_cross_section_count` | 175 |
| `selected_top_fraction` | 0.20 |
| `min_selected_count_per_signal_date` | 35 |
| `min_nonselected_count_per_signal_date` | 140 |
| `min_complete_nonselected_baseline_count_per_date_horizon` | 120 |
| sample complete share floor | 0.90 |
| active-overlap median / p90 floor | 0.90 / 0.97 |
| active-overlap effective independent event floor | 1,000 |

这使得 `eligible_count < 300` 不再自动触发 data contract block。但它没有放松收益通过门：absolute、relative、baseline、robustness、adjacent horizon 仍然必须按固定规则评价。

## 3. 输入数据与字段覆盖

输入数据通过审计：

| item | value |
|:--|--:|
| daily feature rows | 1,101,821 |
| instruments | 539 |
| min date | 2017-07-04 |
| max date | 2026-04-30 |
| status | `passed` |

字段覆盖：

| field | row_count | non_null_count | status |
|:--|--:|--:|:--|
| open | 1,101,821 | 1,092,439 | `present` |
| high | 1,101,821 | 1,092,439 | `present` |
| low | 1,101,821 | 1,092,439 | `present` |
| close | 1,101,821 | 1,092,439 | `present` |
| volume | 1,101,821 | 1,092,439 | `present` |
| money | 1,101,821 | 1,092,439 | `present` |
| vwap | 1,101,821 | 1,092,439 | `present` |
| index_open | 1,101,821 | 1,101,821 | `present` |
| index_close | 1,101,821 | 1,101,821 | `present` |

输入层没有构成当前失败原因。

## 4. 因子库与方向学习

GTJA191 registry：

| status | count |
|:--|--:|
| included | 125 |
| excluded_formula_implementation_failed | 65 |
| excluded_insufficient_cross_section_coverage | 1 |
| total | 191 |

`alpha055`、`alpha137`、`alpha182` 的布尔/数值映射失败已修复，三者均进入 included：

| factor | status |
|:--|:--|
| alpha055 | `included` |
| alpha137 | `included` |
| alpha182 | `included` |

排除原因：

| reason | count |
|:--|--:|
| unsupported_or_slow_v0_construct | 65 |
| insufficient_train_factor_coverage_date_count | 1 |

方向学习：

| direction_i | count |
|--:|--:|
| -1 | 66 |
| 0 | 1 |
| 1 | 58 |

| metric | value |
|:--|--:|
| direction-active factors | 124 |
| valid train RankIC date median | 224 |
| valid train RankIC date p10 | 223 |
| mean_train_rankIC median | -0.001813 |
| mean_train_rankIC p10 | -0.020135 |
| mean_train_rankIC p90 | 0.030564 |
| mean_train_rankIC min | -0.061084 |
| mean_train_rankIC max | 0.056518 |

最强绝对 RankIC 因子：

| factor_id | valid train dates | mean_train_rankIC | direction |
|:--|--:|--:|--:|
| alpha013 | 224 | -0.061084 | -1 |
| alpha007 | 224 | 0.056518 | 1 |
| alpha124 | 222 | -0.055982 | -1 |
| alpha100 | 224 | -0.054661 | -1 |
| alpha097 | 224 | -0.053201 | -1 |
| alpha081 | 224 | -0.048786 | -1 |
| alpha114 | 224 | 0.047375 | 1 |
| alpha153 | 224 | 0.037010 | 1 |
| alpha173 | 224 | 0.036794 | 1 |
| alpha126 | 224 | 0.036300 | 1 |
| alpha093 | 224 | 0.035866 | 1 |
| alpha010 | 223 | 0.035684 | 1 |

因子库和方向学习均不是失败原因。失败发生在 validation/robustness 收益与 residual 形态。

## 5. Selection 与 small-universe 覆盖

score audit 共有 430 个 weekly score dates：

| selection_status | count |
|:--|--:|
| `selected` | 289 |
| `blocked_insufficient_eligible_cross_section` | 141 |

按 split 汇总：

| split | dates | selected_dates | eligible_min | eligible_median | eligible_max | selected_count_median | nonselected_count_median |
|:--|--:|--:|--:|--:|--:|--:|--:|
| train | 227 | 86 | 110 | 157 | 269 | 0 | 0 |
| validation | 99 | 99 | 203 | 226 | 252 | 46 | 180 |
| robustness | 104 | 104 | 179 | 224 | 275 | 45 | 179 |

关键变化是：validation 和 robustness 在 revised floor 下全部可以形成 top-20% selected events。train 早期仍有 141 个日期因 eligible floor 不足被阻断，但这不影响 validation/robustness 结论。

selected event panel：

| split | rows | dates | instruments | selected_count_median | selected_count_min | selected_count_max |
|:--|--:|--:|--:|--:|--:|--:|
| train | 3,962 | 86 | 274 | 46 | 35 | 54 |
| validation | 4,511 | 99 | 234 | 46 | 41 | 51 |
| robustness | 4,764 | 104 | 269 | 45 | 36 | 55 |

需要注意一个审计风险：按 selected weeks 复算，validation top 单票 `SH600436` 被选中 69/99 周，约 69.7%。这说明 weekly dense ranking 会反复选择部分高分股票。当前 summary 的 `concentration_gate` 仍为 true，但 selected-week recurrence 的审计口径需要在后续实现中更严格对齐 requirement。这个风险不改变当前 final decision，因为当前已经是不支持结论；它只说明如果未来出现正收益，必须先修正/复核这一集中度口径。

## 6. Split x Horizon Gate Summary

核心 gate 汇总：

| split | horizon | complete events | complete share | decision dates | sample | active overlap | date independent | abs | rel | baseline | horizon_pass |
|:--|:--|--:|--:|--:|:--|:--:|:--:|:--:|:--:|:--:|:--:|
| train | H5 | 3,788 | 95.61% | 84 | pass | true | true | false | true | true | false |
| train | H10 | 3,699 | 93.36% | 83 | pass | true | true | false | false | true | false |
| train | H20 | 3,540 | 89.35% | 81 | blocked_execution_completeness | false | true | false | false | true | false |
| validation | H5 | 4,356 | 96.56% | 97 | pass | true | true | false | false | false | false |
| validation | H10 | 4,271 | 94.68% | 96 | pass | true | true | false | false | false | false |
| validation | H20 | 4,134 | 91.64% | 94 | pass | true | true | false | false | false | false |
| robustness | H5 | 4,571 | 95.95% | 102 | pass | true | false | false | true | true | false |
| robustness | H10 | 4,484 | 94.12% | 101 | pass | true | false | false | false | false | false |
| robustness | H20 | 4,344 | 91.18% | 99 | pass | true | true | false | false | false | false |

读法：

- validation 三个 horizon 都有足够样本和日期覆盖。
- validation H5/H10/H20 的 absolute 全部失败。
- validation H5/H10/H20 的 relative 全部失败。
- validation baseline lift gate 全部失败。
- robustness 也没有给出 H10 支持。
- H5/H20 没有产生 horizon-specific lead。

## 7. H10 Validation 细节

H10 validation 是 primary decision path：

| metric | value |
|:--|--:|
| mean_net_return | -1.3210% |
| median_net_return | -1.8517% |
| p10_net_return | -10.1073% |
| loss_rate | 61.20% |
| mean_matched_delta_return | 0.1332% |
| median_matched_delta_return | -0.4001% |
| p10_matched_delta_return | -7.7316% |
| matched_loss_rate_delta | -9.0845% |
| fallback_comparator_share | 0.1639% |
| multi_comparator_relative_status | `unstable` |

H10 的 residual mean 是正的，但 distribution 没过：

- `median_matched_delta_return = -0.4001%`，不支持稳定 residual edge。
- `p10_matched_delta_return = -7.7316%`，虽高于 -8% floor，但尾部仍弱。
- `matched_loss_rate_delta = -9.0845%` 看起来有改善，但不足以抵消 median delta 为负和绝对收益显著为负。
- `relative_positive = false`，所以不能报告为 residual alpha。

按年拆开：

| year | complete_event_count | decision_dates | mean_net_return | mean_matched_delta_return |
|--:|--:|--:|--:|--:|
| 2022 | 2,192 | 49 | -0.9677% | 0.6295% |
| 2023 | 2,079 | 47 | -1.6936% | -0.3900% |

2022 有正 residual mean，但 2023 转负；这解释了为什么不能把 H10 的微弱 positive mean matched delta 当成稳定 residual edge。

## 8. Baseline Lift

baseline comparison 可评价，但不通过 gate。

| split | horizon | comparable dates | selected count median | baseline count median | mean selected | mean baseline | mean lift | median lift |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| validation | H5 | 97 | 45 | 178 | -1.1977% | -1.2131% | 0.0154% | -0.2061% |
| validation | H10 | 96 | 45 | 177 | -1.3139% | -1.3753% | 0.0614% | -0.1028% |
| validation | H20 | 94 | 44 | 175 | -1.7207% | -1.7738% | 0.0530% | -0.1764% |
| robustness | H5 | 102 | 44 | 176 | -0.5909% | -0.6792% | 0.0883% | 0.0307% |
| robustness | H10 | 101 | 44 | 175 | -0.1891% | -0.1468% | -0.0422% | -0.2644% |
| robustness | H20 | 99 | 44 | 174 | 0.5777% | 0.7251% | -0.1475% | -0.3512% |

validation H10 年度 baseline lift：

| year | rows | mean_lift | median_lift | mean_selected | mean_baseline |
|--:|--:|--:|--:|--:|--:|
| 2022 | 49 | 0.5353% | 0.2194% | -0.9230% | -1.4582% |
| 2023 | 47 | -0.4325% | -0.5562% | -1.7214% | -1.2889% |

baseline insight：2022 的 selected 相对 nonselected 有 lift，但 2023 反转。整体 mean lift 小幅为正，median lift 为负，年度稳定性失败。因此 baseline_lift_gate 为 false。

## 9. Score Bucket 与 Right Tail

validation H10 score bucket：

| score bucket | count | mean net |
|:--|--:|--:|
| (0.0355, 0.0741] | 722 | -1.2847% |
| (0.0741, 0.0899] | 804 | -1.6221% |
| (0.0899, 0.108] | 843 | -1.3065% |
| (0.108, 0.133] | 938 | -1.9795% |
| (0.133, 0.242] | 964 | -0.4692% |

最高 score bucket 的 validation H10 表现相对最好，但仍为负。这个形态说明 GTJA191 composite 对横截面排序可能有一点信息，但 top bucket 不能形成正收益，也没有形成稳定 relative pass。

right-tail readout：

| split | horizon | count | mean | max |
|:--|:--|--:|--:|--:|
| validation | H5 | 4,356 | -1.2044% | 29.3855% |
| validation | H10 | 4,271 | -1.3210% | 42.2414% |
| validation | H20 | 4,134 | -1.7501% | 85.1137% |
| robustness | H5 | 4,571 | -0.6089% | 46.0519% |
| robustness | H10 | 4,484 | -0.2380% | 49.8823% |
| robustness | H20 | 4,344 | 0.5247% | 72.0376% |

right-tail 存在，但不构成 pass。尤其 validation H20 有 85% 单事件最大收益，但整体 mean 仍为 -1.7501%，说明右尾不能覆盖整体分布劣势。

## 10. Market / Beta Decomposition

validation H10 decomposition：

| market_state | beta_bucket | count | mean net |
|:--|:--|--:|--:|
| risk_off | high_beta | 1,102 | -1.8093% |
| risk_off | low_beta | 555 | -1.5054% |
| mixed | mid_beta | 280 | -1.4363% |
| risk_off | mid_beta | 966 | -1.1493% |
| risk_on | high_beta | 263 | -1.1342% |
| mixed | low_beta | 207 | -1.1043% |
| mixed | high_beta | 304 | -1.0633% |
| risk_on | low_beta | 298 | -0.8291% |
| risk_on | mid_beta | 296 | -0.6864% |

所有 validation H10 market/beta 子桶均为负。risk_on mid/low beta 相对少亏，但没有一个子桶能支撑“某个 regime 下明确可用”的结论。

## 11. Execution 与 Comparator 质量

H10 validation execution blocks：

| blocked_reason | blocked_count |
|:--|--:|
| not_universe_member | 115 |
| split_boundary | 124 |
| missing_open | 1 |

H10 validation fallback comparator share 仅 0.1639%，说明 matched comparator 基本可用，不是当前失败原因。

active overlap：

| horizon | audited dates | median overlap | p90 overlap | max effective clusters |
|:--|--:|--:|--:|--:|
| H5 | 289 | 51.02% | 64.14% | 6,840 |
| H10 | 289 | 66.67% | 79.55% | 4,590 |
| H20 | 289 | 83.72% | 93.36% | 2,440 |

H20 overlap 高，但仍在 revised small-universe gate 内。它说明 dense weekly ranking 在长一点的持有期下会自然堆叠同一批股票，因此 future positive result 必须非常谨慎地解释独立性。

## 12. Final Decision Replay

| rule | would_match | selected | candidate decision |
|:--|:--:|:--:|:--|
| rule_01 | false | false | `r04_blocked_data_or_execution_contract` |
| rule_02 | false | false | `r04_factor_library_not_implementable_blocked` |
| rule_03 | false | false | `r04_factor_direction_learning_not_viable_blocked` |
| rule_04 | false | false | `r04_gtja191_residual_composite_supported_continue_research` |
| rule_06-10 | false | false | relative / comparator / baseline lead rules |
| rule_11-12 | false | false | absolute-only rules |
| rule_13-17 | false | false | unstable / adjacent / sample-limited rules |
| rule_18 | true | true | `r04_no_gtja191_residual_composite_support` |

为什么不是 contract block：validation 和 robustness 都能形成 selected events，required artifacts 也齐全。

为什么不是 factor block：125 个 factors included，超过 120；124 个 active directions，超过 80。

为什么不是 relative-only lead：validation H10 `relative_positive = false`，median matched delta 为负，2023 year mean delta 为负。

为什么不是 baseline lead：baseline mean lift 小幅为正但 median lift 为负，且 2023 年反转。

为什么不是 horizon-specific lead：H5/H20 validation 也都没有通过 absolute/relative。

## 13. Findings

### Finding 1：small-universe 修订后，R04 已经可评价

之前 R04 停在 `eligible_count < 300`。本轮 revised floor 后，validation 99/99 dates 和 robustness 104/104 dates 都能形成 selected top 20%。所以最终失败不再是数据规模阻断，而是收益和 residual 分布不支持。

### Finding 2：GTJA191 等权合成存在一点排序线索，但不够稳定

H10 validation mean matched delta 为 +0.1332%，最高 score bucket 的亏损也最小。但 median matched delta 为 -0.4001%，2023 年 mean matched delta 为 -0.3900%，baseline lift 也在 2023 年反转。这种形态更像弱排序噪声或 regime-specific drift，不足以作为 residual edge。

### Finding 3：绝对收益明确失败

validation H5/H10/H20 mean net 全部为负，H10 mean -1.3210%，median -1.8517%，loss rate 61.20%。即便 relative mean 有一点正值，也不能覆盖 long-only 亏损形态。

### Finding 4：right tail 不能救结论

validation H20 最大单事件收益达到 85.1137%，但 H20 mean 仍为 -1.7501%。R04 的 right-tail readout 再次说明：big winner 存在不等于可交易 expectancy 存在。

### Finding 5：集中度口径需要后续修正

按 selected event panel 复算，validation top 单票选中周占比约 69.7%。当前 summary 的 concentration gate 仍为 true，说明实现口径更接近 event share，而不是 requirement 文义里的 selected-week share。由于最终结论是不支持，这个问题不会制造 false positive；但如果下一版出现 positive lead，必须先修正这个 audit/gate 口径。

## 14. Insight

这次 R04 的价值在于把问题从“数据契约不可评价”推进到了“可评价但不支持”。

更具体地说，GTJA191 train-only direction equal-weight composite 在当前 EP5 PIT universe 上能产生稳定的 weekly ranking、足够多的事件、足够低的 comparator fallback，也能在部分 bucket 和年份里看到一些弱 residual signal。但这些信号没有跨年份、跨 horizon、跨 baseline 稳定下来。H10 的核心组合是：

- sample 足够；
- absolute 失败；
- relative 失败；
- baseline 失败；
- robustness 不确认；
- adjacent horizons 不提供替代 lead。

因此，不建议继续在 R04 内调 top fraction、调权重或挑因子。这样做会直接把 R04 变成 validation-driven search。若要继续探索，比较干净的方向只有两个：

1. 新建 hedged / market-relative requirement，专门研究弱 residual mean 是否能在严格中性化后保留。
2. 新建 exposure / regime diagnostic requirement，解释为什么 risk_on/risk_off、beta bucket、年份切换会让 weak ranking signal 失效。

当前 R04 本身应收敛为：`r04_no_gtja191_residual_composite_support`。

## 15. Artifact Index

| artifact | purpose |
|:--|:--|
| `audit/r04_gtja191_factor_registry.csv` | GTJA191 factor implementation registry |
| `audit/r04_factor_direction_audit.csv` | train-only direction learning |
| `audit/r04_score_cross_section_audit.csv` | weekly eligibility / selected count audit |
| `events/r04_selected_event_panel.csv` | selected top-20% event panel |
| `events/r04_execution_event_panel.csv` | executable selected events |
| `events/r04_matched_comparator_panel.csv` | matched comparator panel |
| `audit/r04_baseline_comparison_audit.csv` | nonselected baseline lift |
| `metrics/r04_split_horizon_summary.csv` | split x horizon gates |
| `metrics/r04_score_bucket_readout.csv` | score bucket readout |
| `metrics/r04_right_tail_readout.csv` | read-only right-tail stats |
| `metrics/r04_decomposition_summary.csv` | market / beta decomposition |
| `decision/r04_final_decision_replay.csv` | first-match rule replay |
| `manifests/r04_validation.json` | validator manifest |

本报告只基于已生成 artifacts 重写解释层，没有改动代码或重新定义实验结果。
