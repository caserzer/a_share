# EP5 R02 最终报告：Simple RS20 Continuation V0

## 1. 结论摘要

R02 的最终结论是：

```text
final_decision = r02_no_simple_continuation_support
priority_rule  = rule_12_no_simple_continuation_support
H10 quadrant   = absolute_false__relative_false
```

这意味着：在当前 PIT universe、next-open execution、H5/H10/H20 固定持有、扣 110 bps round-trip cost、matched comparator 和同周 nonselected liquid baseline 的合同下，简单 RS20 continuation 暂时不能支持 EP5 继续沿这条 short-horizon exposure timing 主线推进。

核心判断不是"样本太少所以看不出来"。H10 validation 有 1184 个 complete events、96 个可判定 weekly observation dates，baseline 也可评估；但 H10 同时失败在 absolute return、matched relative return、date-weighted stability、baseline lift 四条线上。更直接地说：RS20 选出的股票不仅绝对收益为负，也没有稳定跑赢同周同口径 matched comparator，更没有跑赢同周 nonselected 高流动性 baseline。

允许的下一步是：

```text
pause EP5 7.1 short-horizon exposure timing
or select a new exposure mainline
```

明确禁止的下一步是：

```text
grid expansion; ret window / rank threshold / horizon tuning
```

## 2. 边界声明

R02 did not perform alpha search.
R02 did not tune ret20, ret5, rank_pct, ma20, money floor, horizon, or collapse.
R02 did not use big-winner labels for pass/fail.
R02 did not tune thresholds after validation.
R02 did not approve a production strategy.
R02 did not run a hedged or market-neutral backtest.
R02 did not let the audit-only weekly liquid universe baseline create a positive decision.

本报告只解释 R02 frozen contract 的 replay 结果，不修改公式、不补救参数、不从 validation 结果反推新阈值。

## 3. 运行与验证状态

| 项目 | 结果 |
|:--|:--|
| requirement_id | `ep5_r02_simple_rs20_continuation_v0` |
| output_root | `ep5/outputs/r02_simple_rs20_continuation_v0` |
| validation_status | `passed` |
| validator gates | 44 / 44 passed |
| primary events | 4734 |
| unique instruments | 475 |
| primary signal dates | 430 |
| primary execution rows | 14202 |
| primary complete execution rows | 12971 |
| baseline constituent rows | 257538 |
| baseline complete rows | 244030 |
| nonselected baseline complete rows | 231059 |

Validator 已确认：

- 只有一个 primary decision unit：`r02_simple_rs20_continuation_natural_exit_v0`；
- 7.2 baseline 只作为 date-aligned downgrade guard，不能创造 positive decision；
- `baseline_comparison_status(D,H)` 是穷举状态，且只有 `comparable` row 进入 baseline lift；
- final decision replay 与 §15 first-match priority 一致；
- right-tail / big-winner 字段没有进入 final decision。

## 4. H10 主判定

| metric | H10 validation |
|:--|--:|
| signal_event_count | 1277 |
| complete_event_count | 1184 |
| complete_event_share | 92.72% |
| decision_observation_date_count | 96 |
| min_year_decision_observation_date_count | 47 |
| mean_net_return | -1.54% |
| median_net_return | -2.48% |
| p10_net_return | -10.04% |
| loss_rate | 65.71% |
| mean_matched_delta_return | -0.20% |
| median_matched_delta_return | -0.71% |
| p10_matched_delta_return | -8.40% |
| matched_loss_rate_delta | -2.70% |
| date_weighted_mean_net_return | -1.66% |
| date_weighted_mean_matched_delta_return | -0.30% |
| fallback_comparator_share | 0.00% |
| sample_gate_pass | false |
| concentration_gate_pass | true |
| date_independence_gate | false |
| absolute_positive | false |
| relative_positive | false |

H10 的结论是 quadrant 4：absolute false / relative false。它不是 weak comparator 问题：fallback comparator share 是 0%，relative comparable share 是 100%。失败来自 RS20 primary 自身收益和 matched delta 都不够。

## 5. Gate 失败拆解

### 5.1 Sample gate

H10 validation 的 complete_event_count 是 1184，event-row 数量本身足够；decision_observation_date_count 是 96，date 数量也足够。sample gate 失败的主因是 execution completeness：

| blocked_reason | blocked_count | share of signal events |
|:--|--:|--:|
| not_universe_member | 63 | 4.93% |
| split_boundary | 29 | 2.27% |
| missing_exit_open | 1 | 0.08% |
| total blocked | 93 | 7.28% |

`complete_event_share = 92.72%`，低于 R02 要求的 95%。这值得作为数据 / execution completeness 背景记录，但不是本次 no-support 的唯一原因；即使不看 sample gate，absolute、relative、date_independence、baseline_lift 都没有通过。

### 5.2 Absolute gate

H10 absolute return 明确失败：

- mean_net_return = -1.54%，要求 > 0；
- median_net_return = -2.48%，低于 -0.25% floor；
- p10_net_return = -10.04%，低于 -8.00% floor；
- loss_rate = 65.71%，高于 55% 上限；
- 2022 和 2023 年度均值都为负。

这说明 RS20 continuation 在 validation 期不是"少数极端亏损拖累"，而是中心分布、左尾和胜率一起偏弱。

### 5.3 Relative gate

H10 matched comparator 也没有支持：

- mean_matched_delta_return = -0.20%；
- median_matched_delta_return = -0.71%；
- p10_matched_delta_return = -8.40%；
- 2022 mean matched delta = -0.31%；
- 2023 mean matched delta = -0.09%；
- fallback_comparator_share = 0.00%。

matched_loss_rate_delta = -2.70% 是少数正向项，表示 RS20 的亏损率相对 comparator 略低；但 §12.4 需要 mean matched delta > 0 且年度稳定，当前没有满足。因此不能读成 relative edge。

### 5.4 Date independence gate

date-level 结果同样失败：

| metric | H10 validation |
|:--|--:|
| decision_observation_date_count | 96 |
| min_year_decision_observation_date_count | 47 |
| date_weighted_mean_net_return | -1.66% |
| date_weighted_mean_matched_delta_return | -0.30% |
| positive_observation_date_share_net | 28.13% |
| positive_observation_date_share_matched_delta | 42.71% |
| top1_observation_date_event_share | 2.62% |
| top5_observation_date_event_share | 10.30% |

这点很关键：concentration 并不差，top observation dates 没有主导事件数；失败是跨 weekly dates 的广泛负收益，而不是少数日期污染。

### 5.5 Baseline lift gate

7.2 baseline 可评估，但不支持 stock-selection lift：

| metric | H10 validation |
|:--|--:|
| baseline_lift_evaluable | true |
| baseline_lift_gate | false |
| baseline_comparable_observation_date_count | 96 |
| min_year_baseline_comparable_observation_date_count | 47 |
| mean baseline executable constituent count | 208.81 |
| min baseline executable constituent count | 189 |
| primary date-weighted mean | -1.66% |
| nonselected baseline date-weighted mean | -1.35% |
| selection_lift_vs_baseline_mean | -0.31% |
| selection_lift_vs_baseline_median | -0.40% |
| selection_lift_vs_baseline_p10 | -3.73% |
| selection_lift_loss_rate_delta | +4.17% |

解释：同周 nonselected 高流动性 universe 本身也在 validation 期亏损，但 RS20 selected basket 亏得更多。R02 的 7.2 baseline 正是为了防止把高流动性宇宙 beta 或同期市场暴露误读成 stock-selection edge；这里 baseline 明确没有给 7.1 加分，反而解释掉了继续推进的可能性。

## 6. 年度稳定性

H10 validation 的年度拆解：

| year | signal events | complete events | complete share | mean net | median net | p10 net | loss rate | mean matched delta | date-weighted net | date-weighted matched delta | baseline lift mean |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 2022 | 629 | 589 | 93.64% | -1.44% | -1.96% | -11.53% | 61.46% | -0.31% | -1.71% | -0.41% | -0.37% |
| 2023 | 648 | 595 | 91.82% | -1.64% | -2.71% | -8.22% | 69.92% | -0.09% | -1.62% | -0.19% | -0.25% |

两年方向一致偏弱。2022 左尾更重，2023 胜率更差；但两年都没有提供 absolute pass、relative pass 或 baseline lift pass。

Robustness H10：

| year | complete events | complete share | mean net | median net | p10 net | loss rate | mean matched delta | date-weighted net | date-weighted matched delta | baseline lift mean |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 2024 | 589 | 95.93% | -1.16% | -2.07% | -9.09% | 64.18% | -0.34% | -0.44% | -0.29% | -0.21% |
| 2025 | 581 | 89.38% | +0.40% | -0.75% | -7.76% | 54.22% | +0.52% | +0.46% | +0.41% | +0.55% |

Robustness 里 2025 明显改善，但 2024 仍负，且 complete share / date gate / distribution floor 没有形成 confirmation。按 R02 合同，robustness 只能确认 validation，不能救回 validation failure；因此 2025 的改善只能作为背景线索，不能升级成 continue。

## 7. H5 / H20 形状

| horizon | validation mean net | validation mean matched delta | date-weighted net | date-weighted matched delta | baseline lift mean | absolute | relative | strongly_negative |
|:--|--:|--:|--:|--:|--:|:--:|:--:|:--:|
| H5 | -1.55% | -0.40% | -1.66% | -0.43% | -0.48% | false | false | true |
| H10 | -1.54% | -0.20% | -1.66% | -0.30% | -0.31% | false | false | false |
| H20 | -1.65% | +0.07% | -2.02% | -0.21% | -0.26% | false | false | false |

H5 明确 strongly negative。H20 的 event-level mean matched delta 略正，但 absolute return、date-weighted matched delta、baseline lift 都为负，且 p10_net_return = -13.09%。所以不存在 horizon-specific lead，不能把 H20 作为替代主线。

## 8. Multi-comparator 与市场解释

H10 validation 的多 comparator readout：

| comparator readout | mean delta |
|:--|--:|
| matched primary comparator | -0.20% |
| same-day universe | -0.24% |
| industry-only | -0.25% |
| liquidity-only | -0.20% |
| SH000300 | +0.26% |

这组结果的含义很清楚：RS20 没有跑赢本地同周股票横截面 comparator，但相对 SH000300 为正。SH000300 正向不能支持 stock-selection edge，因为 R02 明确要求它只能作为 beta / market context，不得单独支撑 relative-only。当前更合理的解释是：A 股大盘指数在部分区间更弱，RS20 basket 相对指数好一点，但在可交易股票横截面内没有 selection lift。

## 9. Concentration 与分解

H10 validation concentration gate 通过：

| metric | value |
|:--|--:|
| top1_instrument_event_share | 0.84% |
| top5_instrument_event_share | 3.72% |
| top1_industry_event_share | 8.11% |
| top1_entry_date_event_share | 2.62% |
| top1_observation_date_event_share | 2.62% |
| top5_observation_date_event_share | 10.30% |
| top1_observation_date_profit_contribution_share | 5.05% |

失败不是因为单一股票、行业或日期过度集中。

市场状态上，H10 validation 的主要事件落在 risk_off：

| market_state | complete events | mean net | mean matched delta |
|:--|--:|--:|--:|
| risk_off | 716 | -1.97% | -0.46% |
| risk_on | 239 | -1.84% | -0.14% |
| mixed | 229 | +0.09% | +0.57% |

mixed 状态有一点正向，但样本只是描述性 readout，R02 禁止 regime subset selection。risk_on 本身也没有救回来，说明这不是简单的"只要开 risk_on 就行"。

beta bucket 上：

| beta_bucket | complete events | mean net | mean matched delta |
|:--|--:|--:|--:|
| low_beta | 405 | -2.07% | -0.47% |
| mid_beta | 405 | -0.85% | +0.33% |
| high_beta | 374 | -1.72% | -0.47% |

mid_beta 相对更好，但仍是 absolute negative，不能被拿来做 validation 后 subset。

RS bucket 上，最高 rank bucket 有改善但不够稳：

| bucket | complete events | mean net | median net | mean matched delta |
|:--|--:|--:|--:|--:|
| rank 0.80-0.85 | 387 | -1.99% | -2.50% | -0.66% |
| rank 0.85-0.90 | 341 | -1.57% | -2.45% | -0.07% |
| rank 0.90-0.95 | 280 | -1.65% | -2.42% | -0.41% |
| rank 0.95-1.00 | 176 | -0.35% | -2.54% | +0.90% |

ret20 > 40% 的小桶表现最好：20 events，mean net +4.74%，mean matched delta +4.71%。但这是极小描述性桶，且 R02 明确禁止用 validation 后 bucket selection 变成新规则。它只能说明"极端强势段可能有不同形状"，不能改变 R02 结论。

## 10. Right-tail / big-winner readout

Right-tail 只读，不参与判定。Validation 的 complete_same_split_120d readout：

| status | event_count | share |
|:--|--:|--:|
| hit_plus50 | 53 | 5.63% |
| hit_plus20_only | 225 | 23.89% |
| no_hit_complete | 664 | 70.49% |

另有 cross-split read-only rows：hit_plus50 10，hit_plus20_only 55，no_hit_complete 210。

这说明 RS20 后续确实偶尔有右尾，但右尾频率不足以抵消 H10 主判定里的负均值、负中位数、负 baseline lift 和高亏损率。按 EP5 的讨论边界，big winner 只能是 post-entry diagnostic，不能作为 entry objective 或 pass/fail 证据。

## 11. 对 R02 十二个问题的直接回答

1. `r02_simple_rs20_continuation_natural_exit_v0` 在 H10 进入 `absolute_false__relative_false`。
2. 结果不是 absolute edge，不是 relative edge，也不是可推进的 beta exposure；最终落在 no simple continuation support。
3. Validation 2022 / 2023 都为负，方向一致偏弱，不是单一年份偶发。
4. Robustness 2025 有改善，但 2024 仍弱，且 robustness 不能救回 validation failure；因此不能升级为 validation-only lead 或 continue。
5. Matched comparator fallback 不高，fallback share = 0%；relative failure 不是 comparator 质量问题。
6. 收益不是由少数 instrument、industry、entry date 或 observation date 主导；concentration gate 通过。
7. event-row 结论不是少数 weekly observation dates 驱动；date-weighted return 同样为负。
8. H5 / H20 不支持 H10；H5 strongly negative，H20 没有形成可用 horizon-specific lead。
9. Big-winner readout 只是 post-entry diagnostic，未用于 pass/fail。
10. 7.1 vs 7.2 baseline 可评估；差额显示 RS20 没有 stock-selection lift，反而跑输同周 nonselected liquid baseline。
11. Relative-only 没有触发；多 comparator 不稳定，唯一偏正的是相对 SH000300，这不能支撑 hedged / relative audit。
12. 下一份 requirement 若继续 EP5，应该重新选择 exposure 主线或暂停；不得扩 RS20 grid、不得改 ret20 / rank_pct / horizon 来救本次结果。

## 12. 我的判断

R02 给出的信号比 R01 更硬：这不是一个"复杂规则没调好"的问题。R02 把机制降到很简单的 weekly RS20 continuation，且 baseline 可评估、comparator 质量干净、concentration 干净；在这种情况下仍然得到 H10 absolute false / relative false，说明当前 EP5 这条 short-horizon long-only exposure timing 主线没有局部可行性支持。

唯一值得保留的线索是：robustness 2025、mixed market state、rank 0.95-1.00 和 ret20 > 40% 小桶出现过局部改善。但这些都属于 descriptive readout，不允许在 R02 内被抽出来变成新规则。若要继续，应该写一份新的 requirement，重新定义一个经济问题，而不是把 R02 的失败桶拿来调参。

我的建议是：R02 后不要做 `ret20 window / rank threshold / horizon` 的局部 grid expansion。更合理的路线是暂停 EP5 7.1 short-horizon exposure timing，回到 discussion 层决定是否换一条 exposure 主线；如果要研究 2025 改善，也应作为 regime-attribution discussion，不应直接写成可交易策略搜索。
