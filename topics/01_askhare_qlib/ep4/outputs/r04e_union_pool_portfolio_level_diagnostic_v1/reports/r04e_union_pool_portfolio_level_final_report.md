# R04e union pool portfolio-level diagnostic 最终报告

R04e uses R04c failed descriptive leads as a frozen union diagnostic.
R04e does not reinterpret any R04c pool as having passed validation.
R04e does not reinterpret R04d as a policy pass.
R04c final decision remains r04c_no_candidate_pool_passed_validation.
R04d final decision remains r04d_no_policy_passed_validation.
diagnostic only; no production entry rule is emitted; upstream pools were selected after prior OOS descriptive review.

本报告只解释当前 R04e 已生成的 artifacts，不改变 runner、config、validator 或任何上游结论。证据主要来自：

- `r04e_source_pool_reconciliation.csv`
- `r04e_union_event_overlap_audit.csv`
- `r04e_pseudo_diversification_audit.csv`
- `r04e_union_hold120_readiness.csv`
- `r04e_event_policy_replay_summary.csv`
- `r04e_portfolio_policy_summary.csv`
- `r04e_baseline_A_portfolio_comparison.csv`
- `r04e_family_contribution_decomposition.csv`
- `r04e_portfolio_monthly_summary.csv`
- `r04e_daily_candidate_count_audit.csv`
- `r04e_same_instrument_nearby_event_audit.csv`
- `r04e_matched_baseline_reconstruction_audit.csv`

## 1. 最终结论

| item | value |
|---|---|
| final_decision | `r04e_union_not_viable_validation` |
| selected_portfolio_policy_id | 空 |
| gate0_status | `gate0_stop_low_quality_union` |
| gate0_stop_category | `input_or_comparator_failure` |
| decision_reason | `gate0 input/comparator failure` |
| validation_status | `passed` |

核心判断：

1. R04e 没有改变 R04c / R04d 的失败结论。R04c 仍然是 `r04c_no_candidate_pool_passed_validation`，R04d 仍然是 `r04d_no_policy_passed_validation`。
2. 三个 source pool 的 exact event overlap 确实较低，validation 的 pairwise jaccard 为 7.89% 到 20.74%。
3. 但低 event overlap 没有转化为有效组合分散。Union 的 same-instrument 20d cluster share 在 validation 达到 74.11%，Gate 0 因 `pseudo_diversification_concentrated` 停止。
4. Union hold120 no-exit 在 validation 仍未转正：event-level net 为 -1.75%。虽然相对 matched baseline_A 有明显少亏，mean delta +5.51%，p10 delta +4.02%，loss<=-5 delta -13.86%，但绝对收益仍不合格。
5. Portfolio-level uncapped 口径没有把 relative improvement 转成正期望。最好的 primary validation 组合仍为负收益：active equal-weight hold120 no-exit period return -22.81%，family-balanced hold120 no-exit period return -24.16%。
6. Active cap sensitivity 可以显著降低损失，但最好的 cap20 组合仍为 -11.33%，只能作为容量 / 风险敏感性线索，不能救回 primary gate。

因此，R04e 的主要发现不是“union pool 通过”，而是：

```text
三个 R02 relative-improvement pools 有 event-level 左尾改善线索，
但在 validation 年份中，它们以相近 instrument / calendar cluster 的方式反复出现。
合并后提高了 active inventory 和 gross candidate pressure，
没有产生足够独立的收益来源来抵消长多组合层面的环境压力。
```

## 2. 数据重建与上游一致性

R04e 的 source membership 来自 R02 family action-time panel，而不是直接复用 R04c selected state。重建结果与 R04c 三个 descriptive leads 完全对齐：

| pool_id | family | R04e reconstructed | R04c count | overlap vs R04c | entry mismatch | status |
|---|---|---:|---:|---:|---:|---|
| `r02_precision_volume_money` | volume_money | 7,940 | 7,940 | 100.00% | 0 | passed |
| `r02_precision_range_breakout` | range_breakout | 6,558 | 6,558 | 100.00% | 0 | passed |
| `r02_precision_pullback_drawdown` | pullback_drawdown | 6,266 | 6,266 | 100.00% | 0 | passed |

Source pool 在各 split 的样本量：

| split | pool_id | event_count | replay_complete_count | pseudo status |
|---|---|---:|---:|---|
| train | `r02_precision_volume_money` | 3,664 | 2,969 | sufficient |
| train | `r02_precision_range_breakout` | 3,047 | 2,440 | sufficient |
| train | `r02_precision_pullback_drawdown` | 2,863 | 2,309 | sufficient |
| validation | `r02_precision_volume_money` | 2,074 | 1,573 | sufficient |
| validation | `r02_precision_range_breakout` | 1,797 | 1,337 | sufficient |
| validation | `r02_precision_pullback_drawdown` | 1,660 | 1,284 | sufficient |
| robustness | `r02_precision_volume_money` | 2,200 | 1,558 | sufficient |
| robustness | `r02_precision_range_breakout` | 1,707 | 1,240 | sufficient |
| robustness | `r02_precision_pullback_drawdown` | 1,739 | 1,278 | sufficient |

解读：

- 三个单池各自的 denominator 没有明显问题。
- R04e 的失败不是由 source 重建错误、R04c reconciliation failure 或 matched comparator 不足导致。
- 问题出现在 union 后的组合结构：source pools individually sufficient，但 union 的 event clustering 明显恶化。

## 3. Event overlap：低 jaccard 不是充分分散

Validation pairwise overlap：

| source_pool_id_a | source_pool_id_b | count_a | count_b | intersection | union_count | jaccard | overlap vs a | overlap vs b | same instrument vs a | same entry-date vs a | status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `r02_precision_volume_money` | `r02_precision_range_breakout` | 2,074 | 1,797 | 665 | 3,206 | 20.74% | 32.06% | 37.01% | 99.00% | 87.03% | low_overlap |
| `r02_precision_volume_money` | `r02_precision_pullback_drawdown` | 2,074 | 1,660 | 273 | 3,461 | 7.89% | 13.16% | 16.45% | 98.67% | 84.79% | low_overlap |
| `r02_precision_range_breakout` | `r02_precision_pullback_drawdown` | 1,797 | 1,660 | 348 | 3,109 | 11.19% | 19.37% | 20.96% | 99.33% | 87.15% | low_overlap |

表面上 jaccard 很低，说明三个 family 的 exact event_key 并不是简单重复命名。但 same-instrument 和 same-entry-date overlap 很高，说明它们可能是在同一批股票、同一批市场窗口附近发出不同 family 的信号。

这解释了 R04e 的关键矛盾：

```text
exact event overlap low
不等于
portfolio risk factor overlap low
```

我的判断是：R04e 不是被“重复事件”击败，而是被“相近股票 + 相近日期 + 长持有期造成的 active inventory 堆叠”击败。

## 4. Union pseudo-diversification audit

Union pool 的分散性读数：

| split | event_count | replay_complete | top1 year | top1 month | top1 instrument | top5 instrument | top1 industry | top3 industry | daily p90 | daily p95 | daily p99 | same-instrument 20d cluster | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train | 7,367 | 5,977 | 31.37% | 3.57% | 0.68% | 3.27% | 11.82% | 29.92% | 17.0 | 23.0 | 37.65 | 71.74% | concentrated |
| validation | 4,387 | 3,323 | 51.38% | 6.50% | 0.59% | 2.87% | 9.85% | 26.81% | 21.0 | 29.2 | 39.76 | 74.11% | concentrated |
| robustness | 4,475 | 3,252 | 50.61% | 7.13% | 0.56% | 2.77% | 10.28% | 27.69% | 19.0 | 28.0 | 37.68 | 71.40% | concentrated |

单看 top1 instrument / top5 instrument / top1 industry，union 并不集中：

- validation top1 instrument 只有 0.59%。
- validation top5 instrument 只有 2.87%。
- validation top1 industry 只有 9.85%。

但 same-instrument 20d cluster share 达到 74.11%，这才是 Gate 0 stop 的核心。它说明很多 union events 不是静态地集中在一只股票上，而是在相同股票上反复、近距离触发。长持有期下，这会转化为 active positions 的堆叠。

Validation same-instrument nearby audit 进一步确认：

- validation union events: 4,387。
- clustered_20d rows: 3,301。
- clustered share: 75.25%。
- same_instrument_nearby_union_event_count median: 2。
- max nearby union events in 20d: 5。

结论：union 看起来不是 instrument concentration，但它是 time-local repeated exposure concentration。

## 5. Matched baseline reconstruction

Matched baseline_A 在 union collapse 之后重新构建，且三个 split 都 sufficient：

| split | status | unique baseline events | ESS | matched pool events | main fallback read |
|---|---|---:|---:|---:|---|
| train | sufficient | 6,646 | 3,033.42 | 7,367 | 91.37% matched at split+year+quarter+market+industry |
| validation | sufficient | 3,450 | 2,164.96 | 4,387 | 83.41% matched at split+year+quarter+market+industry |
| robustness | sufficient | 2,846 | 1,465.28 | 4,475 | 85.18% matched at split+year+quarter+market+industry |

Validation 仍有 15.18% fallback 到 split+year，但 ESS=2,164.96，远高于 300 的 requirement threshold。因此，R04e 的 stop 不能解释为 matched comparator 不足。它是 union 自身质量和 absolute validation net 的问题。

## 6. Gate 0 hold120 no-exit readiness

| split | events | replay_complete | net mean | matched baseline net | mean delta | p10 delta | loss<=-5 delta | +50 rate | matched ESS | pseudo status | readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| train | 7,367 | 5,977 | +3.51% | +5.26% | -1.76% | +2.01% | -2.08% | 14.09% | 3,110.74 | concentrated | readout_only |
| validation | 4,387 | 3,323 | -1.75% | -7.26% | +5.51% | +4.02% | -13.86% | 6.26% | 2,195.12 | concentrated | stop |
| robustness | 4,475 | 3,252 | +8.38% | +10.80% | -2.42% | +2.22% | -3.39% | 9.69% | 1,474.03 | concentrated | readout_only |

Validation stop reason:

```text
pseudo_diversification_concentrated|absolute_validation_net_too_weak
```

这张表是 R04e 最重要的证据：

- Validation 相对 baseline_A 明显少亏，尤其是 loss<=-5 delta = -13.86%。
- 但 validation net 仍是 -1.75%，没有转正。
- Gate 0 不是因为样本数不足：validation replay_complete_count=3,323，超过 conditional_go 的 2,000 和 strong_go 的 2,500。
- Gate 0 也不是因为 matched comparator 不足：ESS=2,195.12。
- Gate 0 的硬伤是 pseudo concentration 与 absolute net failure 同时出现。

我的解读：

```text
R04e union 有“风险减损”特征，但没有“收益生成”特征。
它更像一个较差环境下的相对防守候选池，而不是能独立转正的 long-only alpha pool。
```

## 7. Event-level policy replay：短持有改善均值，但牺牲右尾

Validation event-level union 中，按 net_return_mean 排名前列的 policy：

| policy_id | complete | net mean | p10 | loss<=-5 | +50 rate | +50 retention vs hold120 | mean delta vs matched | p10 delta | loss delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `hold_20d__fixed_stop__stop_loss_pct_m0p05` | 4,207 | -0.65% | -7.65% | 45.50% | 0.33% | 5.51% | +0.30% | +0.36% | -7.30% |
| `hold_20d__break_even_after_gain__activation_gain_pct_0p08` | 4,191 | -0.83% | -12.76% | 31.54% | 0.33% | 5.51% | +0.52% | +1.37% | -6.06% |
| `hold_20d__break_even_after_gain__activation_gain_pct_0p10` | 4,191 | -0.86% | -12.86% | 32.19% | 0.33% | 5.51% | +0.52% | +1.51% | -6.25% |
| `hold_20d__fixed_stop__stop_loss_pct_m0p08` | 4,198 | -0.86% | -10.23% | 39.52% | 0.33% | 5.51% | +0.51% | +0.52% | -8.04% |
| `hold_20d__no_exit__none` | 4,189 | -0.87% | -12.98% | 33.04% | 0.33% | 5.51% | +0.51% | +1.58% | -6.53% |
| `hold_120d__break_even_after_gain__activation_gain_pct_0p08` | 3,430 | -1.19% | -20.86% | 30.29% | 5.25% | 70.87% | +4.22% | +5.85% | -9.30% |
| `hold_120d__break_even_after_gain__activation_gain_pct_0p10` | 3,394 | -1.37% | -22.34% | 33.41% | 5.45% | 72.83% | +4.47% | +5.66% | -9.35% |

发现：

- 短持有 / tight stop 能把 event mean 拉近 0，但仍未转正。
- 短持有 policy 的 +50 retention 只有 5.51%，不满足 portfolio strong/conditional gate 所需的 right-tail retention。
- 120d break-even policy 保留右尾更好，retention 约 70.87% 到 72.83%，但 event mean 仍为负。
- 因此 event-level 出现典型 tradeoff：要么少亏但丢右尾，要么保留右尾但仍不能转正。

Right-tail validation gates use `policy_max_gain50_retention_rate_vs_hold120_no_exit`, not raw `max_gain50_rate`.

## 8. Primary portfolio validation：组合层没有转正

Primary validation 只看 uncapped portfolios。按 period_compounded_return 排名前列：

| portfolio_id | policy_id | period return | daily mean | monthly p10 | monthly p10 delta | max drawdown | max drawdown delta | worst 20d | worst 20d delta | active p95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `active_equal_weight_uncapped` | `hold_120d__no_exit__none` | -22.81% | -0.05% | -6.26% | +0.32% | 22.09% | -8.29% | -11.18% | +0.94% | 1,192.0 |
| `active_equal_weight_uncapped` | `hold_120d__break_even_after_gain__activation_gain_pct_0p15` | -23.29% | -0.05% | -6.08% | +0.35% | 21.87% | -8.12% | -11.05% | +1.01% | 1,115.7 |
| `active_equal_weight_uncapped` | `hold_120d__break_even_after_gain__activation_gain_pct_0p10` | -23.44% | -0.05% | -5.97% | +0.45% | 21.87% | -7.59% | -10.99% | +1.14% | 1,021.9 |
| `active_equal_weight_uncapped` | `hold_120d__break_even_after_gain__activation_gain_pct_0p08` | -23.47% | -0.05% | -6.41% | -0.06% | 21.91% | -7.37% | -10.93% | +1.20% | 961.7 |
| `family_balanced_active_equal_weight_uncapped` | `hold_120d__no_exit__none` | -24.16% | -0.05% | -6.46% | +0.12% | 22.95% | -7.44% | -11.34% | +0.78% | 1,192.0 |
| `family_balanced_active_equal_weight_uncapped` | `hold_120d__break_even_after_gain__activation_gain_pct_0p15` | -25.03% | -0.05% | -6.28% | +0.15% | 23.12% | -6.87% | -11.12% | +0.93% | 1,115.7 |
| `family_balanced_active_equal_weight_uncapped` | `hold_120d__break_even_after_gain__activation_gain_pct_0p10` | -25.20% | -0.05% | -6.39% | +0.03% | 22.77% | -6.69% | -10.94% | +1.19% | 1,021.9 |
| `active_equal_weight_uncapped` | `hold_20d__break_even_after_gain__activation_gain_pct_0p15` | -25.57% | -0.06% | -6.03% | +0.17% | 22.03% | -2.30% | -10.41% | +1.07% | 286.7 |

结论：

- active_equal_weight_uncapped 比 family_balanced 略好，但两者都显著为负。
- long-hold no-exit 是 primary portfolio 中最不差的方案，这说明 right-tail retention 仍然重要。
- 组合层左尾相对 baseline_A 有改善，max_drawdown_delta 和 worst_20d_delta 多数为正向，但这只是“少亏”，不是“转正”。
- active_count_p95 对 uncapped 组合极高。hold120 no-exit 的 active_count_p95=1,192，远高于 validation primary gate 的 80。这说明 union 把事件流转成了巨大的 active inventory，而不是一个可解释的低拥挤组合。

## 9. Active cap sensitivity：能减少损失，但不能改变结论

Validation active-cap sensitivity 最好的一组结果：

| portfolio_id | policy_id | cap | period return | daily mean | monthly p10 | monthly p10 delta | max drawdown | max drawdown delta | active p95 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `family_balanced_active_equal_weight_cap20` | `hold_20d__break_even_after_gain__activation_gain_pct_0p15` | cap20 | -11.33% | -0.02% | -7.40% | +0.99% | 20.00% | -13.46% | 20 |
| `family_balanced_active_equal_weight_cap20` | `hold_20d__no_exit__none` | cap20 | -11.56% | -0.02% | -7.40% | +0.99% | 20.03% | -13.01% | 20 |
| `family_balanced_active_equal_weight_cap20` | `hold_20d__break_even_after_gain__activation_gain_pct_0p10` | cap20 | -12.10% | -0.02% | -7.40% | +0.77% | 20.00% | -13.94% | 20 |
| `family_balanced_active_equal_weight_cap20` | `hold_120d__no_exit__none` | cap20 | -13.76% | -0.02% | -6.71% | +0.93% | 23.09% | -14.52% | 20 |
| `active_equal_weight_cap20` | `hold_60d__no_exit__none` | cap20 | -16.12% | -0.03% | -5.89% | +1.48% | 21.59% | -11.14% | 20 |

解读：

- cap20 把 best period return 从 uncapped 的 -22.81% 改善到 -11.33%，风险压力明显下降。
- 但 cap20 后仍没有任何 portfolio period return 转正。
- active cap 的改善说明拥挤和 active inventory 是真实问题；但按 requirement，它只能是 capacity / concentration sensitivity，不能作为 primary gate 通过依据。
- 如果后续继续研究，应该研究 cash sleeve / exposure sleeve，而不是把 active cap 当成 entry selection。

## 10. Family contribution：没有单一 family 能独立解释收益

Validation hold120 no-exit 的 family contribution：

| portfolio_id | family | active weight share | event_count | contribution sum | loss-day share | positive-day share | +50 events | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `active_equal_weight_uncapped` | range_breakout | 30.05% | 1,797 | -8.46% | 7.81% | 6.33% | 103 | additive_source_family |
| `active_equal_weight_uncapped` | volume_money | 37.21% | 2,074 | -8.83% | 9.36% | 7.74% | 112 | additive_source_family |
| `active_equal_weight_uncapped` | pullback_drawdown | 32.74% | 1,660 | -5.74% | 8.47% | 7.27% | 104 | additive_source_family |
| `active_equal_weight_uncapped` | multi_family_collapsed | 22.25% | 1,002 | -5.73% | NA | NA | 56 | non_additive_diagnostic_subset |
| `family_balanced_active_equal_weight_uncapped` | range_breakout | 33.33% | 1,797 | -9.26% | 8.62% | 7.03% | 103 | additive_source_family |
| `family_balanced_active_equal_weight_uncapped` | volume_money | 33.33% | 2,074 | -7.94% | 8.30% | 6.88% | 112 | additive_source_family |
| `family_balanced_active_equal_weight_uncapped` | pullback_drawdown | 33.33% | 1,660 | -7.57% | 8.66% | 7.26% | 104 | additive_source_family |
| `family_balanced_active_equal_weight_uncapped` | multi_family_collapsed | 38.08% | 1,002 | -11.53% | NA | NA | 56 | non_additive_diagnostic_subset |

观察：

- active_equal_weight 下，pullback_drawdown 贡献最不差，但仍为 -5.74%。
- volume_money 和 range_breakout 都贡献负收益，volume_money 的 loss-day share 最高。
- family-balanced 并没有改善整体结果，反而使 multi-family collapsed 子集的负贡献更明显。
- multi-family collapsed events 不是高置信正向事件。它们在 family-balanced 下权重占比更高，贡献更差。

这削弱了一个常见假设：

```text
多个 family 同时命中可能代表更强信号。
```

当前 R04e 数据不支持这个解释。multi-family collapsed 更像是同一拥挤环境里的重复确认，而不是独立 alpha 的叠加。

## 11. Calendar stress 与 active inventory

Primary portfolios 的最差 validation 月份集中在 2022-01 和 2023-12：

| portfolio_id | policy_id | month | monthly return | active day share | active_count_mean | turnover_event_count |
|---|---|---|---:|---:|---:|---:|
| `family_balanced_active_equal_weight_uncapped` | `hold_60d__fixed_stop__stop_loss_pct_m0p05` | 2023-12 | -16.85% | 100.00% | 55.57 | 18 |
| `active_equal_weight_uncapped` | `hold_60d__fixed_stop__stop_loss_pct_m0p05` | 2023-12 | -15.72% | 100.00% | 55.57 | 18 |
| `family_balanced_active_equal_weight_uncapped` | `hold_60d__fixed_stop__stop_loss_pct_m0p08` | 2023-12 | -15.51% | 100.00% | 78.90 | 9 |
| `family_balanced_active_equal_weight_uncapped` | `hold_20d__fixed_stop__stop_loss_pct_m0p10` | 2022-01 | -12.99% | 100.00% | 61.00 | 126 |
| `family_balanced_active_equal_weight_uncapped` | `hold_120d__fixed_stop__stop_loss_pct_m0p10` | 2022-01 | -12.93% | 100.00% | 60.68 | 125 |
| `active_equal_weight_uncapped` | `hold_20d__fixed_stop__stop_loss_pct_m0p10` | 2022-01 | -12.89% | 100.00% | 61.00 | 126 |

Daily candidate count 本身不是极端爆炸：

- validation days: 457。
- daily candidate count mean: 9.60。
- p50: 7。
- p90: 21。
- p95: 29.20。
- p99: 39.76。
- max: 66。

Validation top daily candidate dates：

| entry_execution_date | daily_count | volume_money | range_breakout | pullback_drawdown |
|---|---:|---:|---:|---:|
| 2023-12-29 | 66 | 55 | 47 | 12 |
| 2022-11-14 | 52 | 47 | 18 | 5 |
| 2023-09-05 | 47 | 10 | 27 | 22 |
| 2022-11-08 | 42 | 5 | 21 | 31 |
| 2023-07-31 | 42 | 10 | 11 | 30 |

但 portfolio active_count 很高，是因为长持有期把日度候选流累积成库存：

- hold120 no-exit uncapped active_count_p95 = 1,192。
- hold120 break-even 0.10 active_count_p95 = 1,021.9。
- hold20 组合 active_count_p95 也在 280 左右，仍高于 primary gate 80。

所以问题不是某一天发出 500 个信号，而是信号在同一批股票和相邻时间反复出现，持仓周期又足够长，最后变成高度拥挤的 long-only inventory。

## 12. Findings

### Finding 1: R04e 的 source pools 不是 membership 问题

Source reconstruction 与 R04c 100% 对齐，entry mismatch 为 0。R04e 失败不是实现误差，也不是 R02/R04c membership 定义不一致。

### Finding 2: Exact event overlap 低，但风险暴露 overlap 高

Validation jaccard 最高只有 20.74%，但 same-instrument overlap vs A 接近 99%，same-entry-date overlap vs A 超过 84%。这说明三个 family 不是重复 event_key，却高度共享股票池和交易窗口。

### Finding 3: Union 的主问题是 time-local repeated exposure

Union top1 instrument 只有 0.59%，看起来不集中；但 same-instrument 20d cluster share 为 74.11%。这类集中不会被普通 top instrument share 捕捉，必须看 nearby event audit。

### Finding 4: 相对 baseline_A 的左尾改善是真实的

Validation hold120 no-exit:

- net delta vs matched baseline_A: +5.51%。
- p10 delta: +4.02%。
- loss<=-5 delta: -13.86%。

这说明 union 不是完全无信息。它确实规避了一部分更差的 baseline_A 事件。

### Finding 5: 但这种信息没有转成正期望

同一 validation hold120 no-exit 的绝对 net mean = -1.75%。Primary portfolios 的 period return 全部为负。R04e 的信息更像“从很差中筛出没那么差”，而不是“筛出正收益”。

### Finding 6: Portfolio aggregation 没有创造新 alpha

如果 union 的主要价值来自组合层分散，family-balanced 应该至少接近 active_equal_weight，或者降低 drawdown 的同时保留收益。但 validation 中 family-balanced 的 best primary return 为 -24.16%，弱于 active_equal_weight 的 -22.81%。这说明 portfolio aggregation 没有提供足够的独立收益来源。

### Finding 7: Active cap 是有效的风险刹车，但不是充分条件

cap20 最好结果 -11.33%，比 uncapped -22.81% 少亏很多；但仍然没有转正。因此 active cap 证明“拥挤是问题”，不证明“cap 后策略可用”。

### Finding 8: Multi-family collapsed 不是高置信正向子集

Multi-family collapsed 在 validation hold120 no-exit 下并没有显示正贡献，family-balanced 下负贡献更重。这说明“多个 family 同时命中”在当前数据里更可能是同一市场状态下的重复信号，而不是更强 alpha。

## 13. Insights / guesses

### Insight 1: R04e 更像 adverse-regime insurance，而不是 alpha construction

R04e 的强项是相对 baseline_A 少亏，特别是左尾少亏；弱项是绝对收益无法转正。这个形态更像一个 adverse-regime 下的 defensive filter，而不是一个 long-only entry pool。

### Insight 2: Validation years 可能对 EP4 long-only candidate-pool 范式特别不友好

Validation 的组合层结果连续为负，而 robustness event-level hold120 no-exit 又转正到 +8.38%。但 R04e lifecycle 明确 robustness 只读，不能救回 validation。这提示：split / regime 是关键解释变量，不能用 robustness 反向证明 validation pass。

### Insight 3: 后续不应优先做 R04d v2

R04d 已经证明单池 simple risk-budget 不能完成转正。R04e 又证明 union pool 也没有通过组合层分散转正。继续扩大单池 exit 参数，大概率只是在同一个负期望环境里做局部风险形状优化。

### Insight 4: 如果继续，问题应切到 exposure sleeve / cash sleeve

当前证据更支持下一个问题：

```text
是否需要 market-state cash sleeve、portfolio exposure throttle、
或 short / hedge sleeve，才能让这些 relative-improvement leads 在 adverse validation regime 中不被长多库存拖死？
```

这不是 entry rule promotion，也不是 R04c pool pass。它是 portfolio construction 层面的新问题。

## 14. 需求必答问题逐项回答

| question | answer |
|---|---|
| R04e 是否改变 R04c/R04d 的失败结论？ | 否。R04c 和 R04d 的失败结论保持不变。 |
| 三个 source pools 的 pairwise event overlap 是多少？ | validation jaccard 为 20.74%、7.89%、11.19%，均为 low_overlap。 |
| Union 是否真的分散？ | event_key 层面低 overlap，但 same-instrument 20d cluster 74.11%，因此是伪分散。 |
| Union hold120 no-exit validation net 是否转正？ | 否，validation net mean = -1.75%。 |
| Gate 0 是 strong_go、conditional_go 还是 stop？ | stop，`gate0_stop_low_quality_union`，category=`input_or_comparator_failure`。 |
| active_equal_weight 与 family_balanced 哪个更好？ | active_equal_weight 较好，但仍为负；best primary -22.81%，family-balanced best -24.16%。 |
| 改善来自 event-level alpha 还是 portfolio aggregation？ | 主要是 event-level 相对少亏，不是 portfolio aggregation 创造正收益。 |
| 相对 baseline_A 的 monthly p10、max drawdown、worst 20d 是否改善？ | 部分改善。best active_equal_weight monthly p10 delta +0.32%，max drawdown delta -8.29%，worst 20d delta +0.94%，但 period return 仍 -22.81%。 |
| 哪个 source family 贡献收益，哪个贡献左尾风险？ | 三个 family 在 validation hold120 no-exit 下都是负贡献；pullback_drawdown 最不差，volume_money loss-day share 较高。 |
| daily candidate count 是否过高？ | 日度候选 p99=39.76、max=66，不是最核心问题；核心是长持有导致 active_count_p95 达到 1,192。 |
| active cap 是否改变结论？ | 否。cap20 最好 -11.33%，只说明容量敏感性，不改变 primary validation 失败。 |
| validation 仍失败是否支持 long_only_validation_ceiling_suspected？ | 方向上支持“长多库存/环境压力”这一解释，但按 R04e gate precedence，最终状态是 `r04e_union_not_viable_validation`，不是 `r04e_long_only_validation_ceiling_suspected`。 |
| 后续进入 R04f 还是停止？ | 不建议 R04d v2；若继续，应进入 portfolio sleeve / market-state cash sleeve / exposure throttle 方向，否则可以停止 EP4 long-only pool 线。 |

## 15. Bottom line

R04e 的结论很清楚：

```text
Union pool 确实保留了 R04c/R02 中的 relative-improvement 信息，
但这些信息在 validation 里只表现为少亏和左尾改善。
它没有形成 absolute positive event pool，
也没有在 portfolio-level equal-weight / family-balanced 聚合后转成正收益。
```

因此，R04e 不应被解释为“找到 union candidate pool”。更合理的解释是：

```text
EP4 当前这条 long-only candidate-pool 线，
已经从单池、相对改善池、union pool、简单 portfolio aggregation 四个角度证明：
validation split 的主要问题不是缺少一个更细的 source family 阈值，
而是 exposure / regime / inventory 层面的结构性问题。
```

若后续继续，应该把问题改写成 portfolio construction / market-state cash sleeve，而不是继续做 entry-family 或 exit-policy 的局部搜索。
