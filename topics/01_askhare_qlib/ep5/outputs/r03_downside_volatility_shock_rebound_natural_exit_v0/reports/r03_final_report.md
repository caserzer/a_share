# EP5 R03 Final Report

## 1. 边界声明

R03 did not perform alpha search.
R03 did not tune ret5, realized_vol10, volatility rank, stabilization, money floor, horizon, or collapse.
R03 did not reuse R02 descriptive buckets as candidate rules.
R03 did not use big-winner labels for pass/fail.
R03 did not tune thresholds after validation.
R03 did not approve a production strategy.
R03 did not run a hedged or market-neutral backtest.
R03 did not let the audit-only downside baseline create a positive decision.

本报告只解释当前冻结 R03 公式在 PIT mcap500 mainboard universe、固定成本、固定 split、固定 H5/H10/H20 natural exit 下的可行性结果。所有结论来自当前输出目录：

`ep5/outputs/r03_downside_volatility_shock_rebound_natural_exit_v0/`

## 2. 最终结论

| item | value |
|:--|:--|
| final_decision | `r03_no_downside_rebound_support` |
| priority_rule | `rule_15_no_downside_rebound_support` |
| H10 quadrant | `absolute_false__relative_true` |
| robustness_confirmed | `False` |
| adjacent_horizon_status | `adjacent_horizon_not_evaluable` |
| allowed_next_requirement | pause R03 mainline or define a genuinely new exposure mainline |
| blocked_next_requirements | grid expansion; ret5/volatility rank/stabilization/money repair tuning |

严格结论是：R03 的 downside volatility shock rebound 主线没有获得本轮 local feasibility support。更精确地说，H10 validation 有一个相对收益线索，但它不是完整 pass：

- 样本严重不足：H10 validation 只有 65 个 complete event，远低于 300 的 sample gate，也低于 150 的 sample-limited lead 下限。
- absolute_positive 失败：均值略正，但 median、p10、loss rate 和 2022 年度均值不通过。
- relative_positive 通过：matched comparator delta 在 validation 上为正，而且年度 delta 都为正。
- baseline_lift_evaluable 失败：paired downside nonselected baseline 几乎不可评估，H10 validation 只有 1 个 comparable observation date。
- robustness 翻负：2024-2025 H10 mean net 为 -0.80%，mean matched delta 为 -0.43%。

因此，R03 不应被解读为“完全没有任何局部线索”，但更不能被解读为“找到了可继续推进的 rebound alpha”。当前最合理的解读是：这个 frozen exposure 在 validation 的少量样本里有 residual rebound 痕迹，但样本、absolute distribution、baseline coverage、robustness 四个关键约束都不足以支持继续。

## 3. Final Decision Priority Replay

`r03_final_decision_inputs.csv` 披露了 15 条 first-match rules。当前只有最后一条兜底规则命中：

| order | rule | would_match | selected | candidate_decision |
|--:|:--|:--:|:--:|:--|
| 1 | blocked data / execution contract | False | False | `r03_blocked_data_or_execution_contract` |
| 2 | downside shock rebound supported | False | False | `r03_downside_volatility_shock_rebound_supported_continue_research` |
| 3 | baseline not evaluable after H10 pass | False | False | `r03_baseline_not_evaluable_validation_lead` |
| 4 | downside beta / market rebound only | False | False | `r03_downside_beta_or_market_rebound_only_no_selection_pass` |
| 5 | unstable validation-only lead | False | False | `r03_unstable_validation_only_lead` |
| 6 | unstable horizon shape | False | False | `r03_unstable_horizon_shape_no_search_allowed` |
| 7 | adjacent horizon not evaluable | False | False | `r03_adjacent_horizon_not_evaluable_validation_lead` |
| 8 | relative rebound edge only | False | False | `r03_relative_rebound_edge_only_hedged_or_regime_audit_required` |
| 9 | relative-only baseline not evaluable | False | False | `r03_baseline_not_evaluable_validation_lead` |
| 10 | absolute-only baseline not evaluable | False | False | `r03_baseline_not_evaluable_validation_lead` |
| 11 | absolute-only beta / market rebound | False | False | `r03_downside_beta_or_market_rebound_only_no_selection_pass` |
| 12 | absolute rebound only with baseline lift | False | False | `r03_absolute_rebound_only_baseline_lift_no_relative_pass` |
| 13 | horizon-specific lead only | False | False | `r03_horizon_specific_lead_only_no_search_allowed` |
| 14 | sample-limited primary lead only | False | False | `r03_sample_limited_primary_lead_only` |
| 15 | no downside rebound support | True | True | `r03_no_downside_rebound_support` |

关键点：虽然 H10 是 `absolute_false__relative_true`，但 rule 8 没有触发，因为 rule 8 要求 sample gate、concentration gate、date independence、relative_positive、multi_comparator_relative_stable、baseline_lift_gate 同时成立；当前 sample gate、date independence、baseline_lift_gate 都不成立。

## 4. Signal Generation And Sample

R03 frozen signal 是：

```text
ret5 <= -5%
realized_vol10_rank_pct >= 80%
close_D > close_{D-1}
money_D >= money_ma20_prev_D
avg_money20 >= 50,000,000
weekly ISO last trading day signal
20 trading day same-instrument collapse
```

事件生成结果：

| metric | value |
|:--|--:|
| raw_formula_hit_count | 258 |
| post_collapse_event_count | 252 |
| dropped_duplicate_episode_member_count | 6 |
| blocked_formula_row_count | 0 |

Vol rank cross-section 与 weekly eligible signal 稀疏性：

| split | weekly dates | median cross-section | mean cross-section | zero eligible weeks | median eligible signals | mean eligible signals |
|:--|--:|--:|--:|--:|--:|--:|
| train | 231 | 155 | 172.43 | 152 | 0 | 0.56 |
| validation | 100 | 226 | 223.52 | 55 | 0 | 0.71 |
| robustness | 104 | 224 | 227.24 | 68 | 0 | 0.56 |

这个主线的问题首先是事件源过稀。Validation 100 个 weekly observation date 里，有 55 周没有任何 eligible signal。R03 不是因为 execution 大面积失败才没有样本，而是 frozen exposure 本身在 weekly cadence + 20d collapse 后只产生少量事件。

## 5. H10 Validation Gate Detail

### 5.1 样本与执行

| metric | H10 validation | gate |
|:--|--:|:--|
| signal_event_count | 68 | 需要足够事件源 |
| entry_executable_count | 67 | readout |
| complete_event_count | 65 | fail, 需要 >= 300 |
| complete_event_share | 95.59% | pass, 需要 >= 95% |
| decision_observation_date_count | 43 | pass, 需要 >= 40 |
| min_year_decision_observation_date_count | 15 | pass, 需要 >= 15 |
| sample_status | `blocked_insufficient_sample` | fail |
| sample_gate_pass | `False` | fail |

H10 validation 的 execution blocking 只有 split boundary：

| blocked_reason | blocked_count | signal_event_count | blocked_share |
|:--|--:|--:|--:|
| split_boundary | 3 | 68 | 4.41% |

结论：H10 的执行完整性本身没有结构性崩坏，主要问题是公式事件源太稀疏。H20 validation 额外有 not_universe_member 2 个、split_boundary 5 个，complete share 只有 89.71%，但 H20 只是 adjacent horizon audit，不能救回 H10。

### 5.2 Absolute Positive

| metric | H10 validation | gate result |
|:--|--:|:--|
| mean_net_return | +0.11% | pass, > 0 |
| median_net_return | -1.03% | fail, < -0.25% |
| p10_net_return | -12.07% | fail, < -8.00% |
| loss_rate | 55.38% | fail, > 55.00% |
| 2022 mean_net_return | -0.37% | fail, < -0.25% |
| 2023 mean_net_return | +1.27% | pass |
| absolute_positive | `False` | fail |

这里不是均值完全没有反弹，而是分布质量不够：median 为负，左尾过深，loss rate 刚好越过阈值，且 2022 年度均值未通过。也就是说，R03 H10 的 absolute failure 是“少数/局部收益无法覆盖更广泛亏损分布”，不是单纯 mean 没有起来。

### 5.3 Relative Positive

| metric | H10 validation | gate result |
|:--|--:|:--|
| relative_comparable_event_share | 100.00% | pass |
| blocked_insufficient_comparator_count / complete_event_count | 0.00% | pass |
| fallback_comparator_share | 0.00% | pass |
| mean_matched_delta_return | +1.56% | pass |
| median_matched_delta_return | +0.83% | pass |
| p10_matched_delta_return | -11.97% | fail |
| matched_loss_rate_delta | -4.62% | pass |
| 2022 mean_matched_delta_return | +1.18% | pass |
| 2023 mean_matched_delta_return | +2.46% | pass |
| relative_positive | `True` | pass |

Relative gate 的通过是这次最有信息量的地方：matched comparator、same-day universe、industry-only、liquidity-only、SH000300 delta 在 H10 validation 都是正的，`multi_comparator_relative_stable = True`。这说明在 2022-2023 validation 中，这批 downside shock rebound 事件确实比匹配股票少亏或修复更好。

但这个 relative lead 不能升级为 positive decision，因为它同时缺少 sample gate、absolute_positive、baseline_lift_gate 和 robustness confirmation。

### 5.4 Date Independence

| metric | H10 validation | gate result |
|:--|--:|:--|
| decision_observation_date_count | 43 | pass |
| min_year_decision_observation_date_count | 15 | pass |
| top1_observation_date_event_share | 6.15% | pass |
| top5_observation_date_event_share | 24.62% | pass |
| date_weighted_mean_net_return | +0.03% | pass, but weak |
| date_weighted_mean_matched_delta_return | +1.74% | pass |
| positive_observation_date_share_net | 44.19% | fail, < 50% |
| positive_observation_date_share_matched_delta | 58.14% | pass |
| 2022 date_weighted_mean_net_return | -0.93% | fail |
| 2023 date_weighted_mean_net_return | +1.83% | pass |
| date_independence_gate | `False` | fail |

Date-level view confirms the same pattern：relative/date-weighted delta 较强，但 long-only net date consistency 不够。2022 年的绝对收益 drag 是关键。

## 6. Horizon Shape

Validation split across horizons：

| horizon | complete events | complete share | sample status | mean net | mean matched delta | abs | rel | date gate | baseline lift | horizon pass | adjacent status |
|:--|--:|--:|:--|--:|--:|:--:|:--:|:--:|:--:|:--:|:--|
| H5 | 67 | 98.53% | `blocked_insufficient_sample` | -0.85% | +0.05% | False | False | False | False | False | adjacent_horizon_not_evaluable |
| H10 | 65 | 95.59% | `blocked_insufficient_sample` | +0.11% | +1.56% | False | True | False | False | False | not_applicable |
| H20 | 61 | 89.71% | `blocked_insufficient_sample` | -0.28% | +1.00% | False | True | False | False | False | adjacent_horizon_not_evaluable |

H5 没有提供确认，H20 也没有给出可用的 positive shape。H20 的 relative delta 为正，但 complete share 只有 89.71%，且 absolute 仍为负。由于 H5/H20 complete_event_count 都低于 150，adjacent horizon 被标为 not evaluable，而不是 clean confirmation。

## 7. Paired Downside Baseline

R03 的 baseline 不是 broad market baseline，而是同周、同为 downside shock + high-vol 条件、但未满足 stabilization/money repair 的 nonselected downside basket。这个设计能回答“primary 是否真的强于同类 downside basket”，但当前最大问题是 baseline 本身太稀疏。

H10 validation baseline status：

| status | date_count |
|:--|--:|
| comparable | 1 |
| blocked_insufficient_baseline_constituents | 42 |
| not_applicable_no_primary_complete_event | 2 |

H10 validation baseline constituent count distribution：

| metric | value |
|:--|--:|
| date rows | 45 |
| comparable rows | 1 |
| min | 0 |
| p10 | 0.40 |
| median | 7 |
| mean | 8.80 |
| max | 33 |
| comparable threshold per `(D,H)` | 30 |

Official baseline lift gate：

| metric | H10 validation |
|:--|--:|
| baseline_lift_evaluable | `False` |
| baseline_comparable_observation_date_count | 1 |
| required comparable observation dates | 40 |
| min_year_baseline_comparable_observation_date_count | 1 |
| required min year comparable dates | 15 |
| baseline_lift_gate | `False` |

那 1 个 comparable date 的 selection lift 为 +10.44%，但它没有统计解释力，不能变成 positive evidence。更宽的 broad liquid baseline 在 H10 validation 的 date-weighted mean 为 -1.45%，说明这类周里市场整体确实偏弱；但 R03 final decision 不能由 broad baseline 创造 pass。

结论：baseline 部分不是“primary 没有跑赢 baseline”，而是“paired downside baseline 基本不可评估”。这支持一个工程/需求层 insight：R03 的 paired baseline 设计经济上更严格，但在当前 universe + weekly cadence 下过稀。根据 R03 合同，这不能在 E03 里通过调阈值补救，只能作为未来重新定义 exposure/baseline 的依据。

## 8. Robustness 2024-2025

H10 robustness：

| metric | value |
|:--|--:|
| signal_event_count | 58 |
| complete_event_count | 57 |
| complete_event_share | 98.28% |
| decision_observation_date_count | 35 |
| sample_status | `blocked_insufficient_sample` |
| mean_net_return | -0.80% |
| median_net_return | -3.18% |
| p10_net_return | -10.20% |
| loss_rate | 59.65% |
| mean_matched_delta_return | -0.43% |
| baseline_lift_evaluable | `False` |
| robustness_confirmed | `False` |

Year-level robustness：

| year | complete events | mean net | mean matched delta | date-weighted net | date-weighted delta |
|--:|--:|--:|--:|--:|--:|
| 2024 | 31 | -2.70% | -1.92% | -3.78% | -2.47% |
| 2025 | 26 | +1.47% | +1.34% | +0.86% | +0.83% |

Robustness 不是“变弱但仍可接受”，而是 2024 明显翻负、2025 修复，整体 H10 robustness mean net 和 matched delta 都为负。它不能确认 validation 的 relative lead。

## 9. Regime / Beta / Liquidity Readout

H10 validation by market_state：

| market_state | events | share | mean net | mean matched delta | loss rate |
|:--|--:|--:|--:|--:|--:|
| risk_off | 49 | 75.38% | -0.15% | +1.53% | 55.10% |
| risk_on | 10 | 15.38% | +2.06% | +2.88% | 60.00% |
| mixed | 6 | 9.23% | -1.02% | -0.42% | 50.00% |

H10 validation by beta_bucket：

| beta_bucket | events | share | mean net | mean matched delta | loss rate |
|:--|--:|--:|--:|--:|--:|
| high_beta | 29 | 44.62% | -0.13% | +0.41% | 58.62% |
| mid_beta | 22 | 33.85% | -1.49% | +0.50% | 59.09% |
| low_beta | 14 | 21.54% | +3.12% | +5.60% | 42.86% |

H10 validation by liquidity_quintile：

| liquidity | events | share | mean net | mean matched delta | loss rate |
|:--|--:|--:|--:|--:|--:|
| q5 | 25 | 38.46% | -1.27% | -0.53% | 68.00% |
| q4 | 21 | 32.31% | -1.96% | +0.63% | 57.14% |
| q3 | 14 | 21.54% | +2.46% | +4.07% | 42.86% |
| q2 | 4 | 6.15% | +6.85% | +6.81% | 25.00% |
| q1 | 1 | 1.54% | +18.26% | +17.04% | 0.00% |

Insight：

- Validation 的主要样本在 risk_off，占 75.38%。这与 R03 的经济假设一致：downside shock 在弱市场中更常见。
- risk_off 里 absolute net 仍略负，但 matched delta 为正。这说明它更像“相对少亏/相对修复”而不是可直接 long-only 的 alpha。
- low_beta 与较低 liquidity bucket 的表现更好，但样本很小，不能抽成新规则。R03 明确禁止把 decomposition bucket 升级成 validation 后规则。

## 10. Shock-State Decomposition

H10 validation by ret5 bucket：

| ret5 bucket | events | share | mean net | mean matched delta |
|:--|--:|--:|--:|--:|
| -10% < ret5 <= -5% | 49 | 75.38% | -0.76% | +0.91% |
| -15% < ret5 <= -10% | 12 | 18.46% | +1.36% | +1.44% |
| ret5 <= -15% | 4 | 6.15% | +7.12% | +9.81% |

H10 validation by realized_vol10 rank bucket：

| vol rank bucket | events | share | mean net | mean matched delta |
|:--|--:|--:|--:|--:|
| 80-85 | 13 | 20.00% | -2.14% | -0.78% |
| 85-90 | 9 | 13.85% | +5.97% | +4.81% |
| 90-95 | 14 | 21.54% | -1.82% | +0.96% |
| 95-100 | 29 | 44.62% | +0.24% | +1.88% |

H10 validation by stabilization bucket：

| stabilization bucket | events | share | mean net | mean matched delta |
|:--|--:|--:|--:|--:|
| 0-1% | 13 | 20.00% | +2.15% | +2.85% |
| 1-3% | 27 | 41.54% | +0.63% | +1.68% |
| >3% | 25 | 38.46% | -1.51% | +0.75% |

H10 validation by money repair bucket：

| money repair bucket | events | share | mean net | mean matched delta |
|:--|--:|--:|--:|--:|
| 1.0-1.5x | 42 | 64.62% | +0.80% | +2.76% |
| 1.5-3.0x | 23 | 35.38% | -1.14% | -0.65% |

These are descriptive readouts only. The apparent improvement in deeper ret5 shock or moderate money repair is based on small bins and is not a permitted R03 follow-up rule. The non-monotonic behavior is a warning against turning this into a threshold search.

## 11. Right-Tail Diagnostic

Right-tail is read-only and cannot rescue R03. Official split-level readout should focus on `complete_same_split_120d`.

Validation same-split 120d right-tail：

| status | event_count |
|:--|--:|
| hit_plus20_only | 14 |
| hit_plus50 | 9 |
| no_hit_complete | 30 |
| total complete_same_split_120d | 53 |

Derived readout：

| metric | value |
|:--|--:|
| +20% or +50% hit share | 43.40% |
| +50% hit share | 16.98% |
| no-hit share | 56.60% |

Right-tail 存在，但它不改变短周期 H10 的 pass/fail。R03 的短周期 natural exit 没有通过 sample、absolute、baseline、robustness gates，因此不能因为 120d 后有部分大幅反弹就说 R03 passed。这个结果和 EP5 的基本原则一致：right-tail existence 不等于短周期 positive expectancy。

## 12. Findings

1. R03 主线的首要问题是事件源稀疏。Validation H10 complete_event_count 只有 65，连 sample-limited lead 的 150 下限都不到。这个失败发生在公式层，不是主要由 execution blocking 导致。

2. H10 validation 的 relative residual 是真实的局部线索。mean matched delta +1.56%，2022/2023 年度 matched delta 都为正，fallback comparator share 为 0%，multi-comparator relative stable 为 true。

3. 这个 relative lead 不是 long-only alpha。H10 mean net 只有 +0.11%，median -1.03%，p10 -12.07%，loss rate 55.38%，2022 年度 mean net -0.37%。绝对收益分布没有过 gate。

4. Baseline 设计经济上正确但统计上过稀。Paired downside nonselected baseline 的 H10 validation median constituent count 只有 7，只有 1 个 comparable date。当前不能回答“primary 是否稳定跑赢同类 downside basket”。

5. Robustness 不确认 validation。2024-2025 H10 mean net -0.80%，mean matched delta -0.43%，2024 单年更明显为负。这个翻转使 validation 的 relative lead 更像 regime/context-specific readout。

6. Decomposition 暗示结果可能依赖 beta/liquidity/regime。Low beta 和 q3/q2/q1 bucket 看起来好，但样本太小，且 R03 明确禁止 bucket rescue。

7. H5/H20 没有提供可用形状确认。H5 relative_positive false；H20 relative_positive true 但 sample、execution share、absolute、baseline 均不合格。Adjacent horizons 不可评估。

8. 如果要继续研究，不应扩 R03 grid。更合理的下一步是暂停这条 exact mainline，或者另写一个真正不同的 exposure mainline；如果仍关心 rebound，必须先重新设计事件源和 baseline 可评估性，而不是在本 requirement 内调阈值。

## 13. Answers To R03 Reporting Questions

1. R03 final decision 是 `r03_no_downside_rebound_support`，命中 `rule_15_no_downside_rebound_support`。所有 would-have-matched rules 已在 `r03_final_decision_inputs.csv` 披露；除 rule 15 外均为 false。

2. H10 primary quadrant 是 `absolute_false__relative_true`。Absolute 失败来自 median、p10、loss rate、2022 年度 mean；relative 通过来自 mean/median matched delta、年度 matched delta、loss-rate delta 和 comparator coverage。

3. H10 validation 的 event count 不达标：complete_event_count = 65，complete share = 95.59%，decision observation dates = 43，min year decision dates = 15。Complete share 和 date count 够，但 event count 远低于 300。

4. 主要 H10 validation execution blocking reason 是 split_boundary，3/68，占 4.41%。H10 没有 not_universe_member 问题；H20 validation 有 2 个 not_universe_member 和 5 个 split_boundary。

5. H10 absolute gate：mean +0.11%，median -1.03%，p10 -12.07%，loss rate 55.38%；2022 mean -0.37%，2023 mean +1.27%。结果为 false。

6. H10 relative gate：mean matched delta +1.56%，median +0.83%，p10 -11.97%，matched loss-rate delta -4.62%，fallback share 0%；2022 delta +1.18%，2023 delta +2.46%。结果为 true。

7. Date independence 不通过。Date-weighted net +0.03% 但很弱，positive net date share 44.19% 低于 50%，2022 date-weighted net -0.93%。Date-weighted matched delta +1.74% 支持 relative readout，但不支持 long-only pass。

8. Downside baseline 不可评估。H10 validation baseline comparable dates 只有 1，要求 40；paired baseline executable constituent median 只有 7，mean 8.80。

9. Broad liquid baseline 显示同周整体环境偏弱。H10 validation broad liquid baseline date-weighted mean 为 -1.45%，但 broad baseline 只用于解释市场整体反弹，不能创造 positive decision。

10. H5/H20 没有提供 adjacent horizon 形状确认。H5/H20 都是 sample insufficient，且 adjacent status 为 not evaluable。

11. Robustness 是翻转，不是确认。H10 robustness mean net -0.80%，mean matched delta -0.43%，baseline not evaluable，robustness_confirmed false。

12. 失败主要来自 sample insufficiency、absolute distribution failure、baseline not evaluable、robustness failure。Relative comparator 质量本身不弱，validation fallback share 为 0。

13. Regime/beta/liquidity decomposition 显示 relative lead 可能受 risk_off、low_beta、liquidity bucket 影响。它是解释性线索，不是 stock-selection pass。

14. Shock-state decomposition 有描述性差异，但没有单调稳定结构。ret5 更深、vol rank 85-90、money repair 1.0-1.5x 看起来较好，但样本小，不得升级为新规则。

15. Right-tail readout 仅作为 post-entry diagnostic。Validation same-split 120d 中 +20% or +50% hit share 为 43.40%，+50% hit share 为 16.98%，不能救回短周期 failure。

16. 下一步允许暂停 R03 mainline 或定义真正新的 exposure mainline。禁止在 R03 内扩 ret5、realized_vol10、vol rank、stabilization、money repair、horizon grid 来救回。

## 14. Validator

| item | value |
|:--|:--|
| validation_status | `passed` |
| passed gates | 70 / 70 |
| failed gates | 0 |
| validation manifest | `ep5/outputs/r03_downside_volatility_shock_rebound_natural_exit_v0/manifests/r03_validation.json` |

Validator passed means artifacts, schema, frozen constants, replay, final decision priority, and report boundary statements match the R03 contract. It does not mean the exposure passed economically. The economic final decision remains `r03_no_downside_rebound_support`.
