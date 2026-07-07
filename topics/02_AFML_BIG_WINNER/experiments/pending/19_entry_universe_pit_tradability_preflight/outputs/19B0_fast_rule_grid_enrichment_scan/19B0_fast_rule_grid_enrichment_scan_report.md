# 19B0 快速规则网格右尾富集扫描报告

## 1. 结论

19B0 的最终状态是：

```text
decision_state = 19B0_baseline_materialization_blocked
blocking_reason = baseline_matching_quality_gate
next_allowed_requirement = none
selected_family_cell_pair_n = 0
```

这不是候选不足，也不是 label 锚点不可用。所有候选 family/cell 都能物化 baseline，
但 matched baseline 质量全部失败：

```text
baseline_materialization_gate: pass for 489 / 489 baseline-family-cell rows
baseline_matching_quality_gate: fail for 489 / 489 baseline-family-cell rows
```

因此本轮不能把任何 train lift 解释为可进入 19B robustness 的右尾水库证据。
所有 family 读数只能作为 train diagnostic / hypothesis。

## 2. 边界和标签

19B0 使用 `executable_next_open_anchored` 标签。EP07 既有的 `event_anchored`
ready-made label 只作为 diagnostic，不进入 primary metric 或 selection。

本轮只读取 train outcome：

```text
validation outcome read = false
robustness outcome used for selection = false
model / policy / backtest authorization = false
```

核心标签是从可成交入场价重建的 `forward_big_winner_120d`：

```text
entry anchor = next tradable day qfq open
winner threshold = max forward qfq high within 120d / entry_open - 1 >= 0.50
path completeness = horizon_complete_120d
```

## 3. Baseline 失败细节

19B0 使用三类 same-budget baseline：

| baseline family | rows | pass_n | unmatched median | max SMD median | decision-month delta median |
|---|---:|---:|---:|---:|---:|
| calendar_time_random_same_budget | 163 | 0 | 0.1287 | 1.0640 | 0.0233 |
| instrument_matched_random_same_budget | 163 | 0 | 0.0230 | 1.0918 | 0.0351 |
| liquidity_size_volatility_matched_same_budget | 163 | 0 | 0.2061 | 0.3917 | 0.0233 |

质量门失败分布：

| rule | threshold | fail_n / 489 | median | max |
|---|---:|---:|---:|---:|
| unmatched_candidate_rate | <= 0.05 | 328 | 0.1284 | 0.3266 |
| baseline_reuse_rate | <= 0.20 | 0 | 0.0017 | 0.0138 |
| max_standardized_mean_difference_after_matching | <= 0.10 | 489 | 0.9632 | 1.4680 |
| decision_month_coverage_delta | <= 0.02 | 431 | 0.0247 | 0.1053 |
| instrument_coverage_delta | <= 0.05 | 0 | 0.0023 | 0.0078 |

Interpretation:

- row count 不是问题：same-budget baseline 都能抽到。
- reuse 不是问题：baseline reuse rate 很低。
- instrument coverage 不是问题：instrument delta 远低于 0.05。
- 真正问题是 covariate balance，尤其 `max_SMD` 全部超过 0.10。
- LSV baseline 的 SMD 明显低于 calendar / instrument baseline，但 unmatched rate
  更高，说明当前候选的 common support 有压力。

## 4. Top Cell 和 Family 排序

按 conservative margin-adjusted score 排序，只有 B2 接近阈值，但仍未通过。

| rank | family | primary_n | p_candidate_50 | conservative_lift | conservative_adjusted | status |
|---:|---|---:|---:|---:|---:|---|
| 1 | B2_relative_strength_breakout | 5,927 | 22.473% | 1.1036 | 0.0036 | train diagnostic only |
| 14 | B5_recent_high_close_plus_amount_expansion | 8,592 | 18.878% | 1.0574 | -0.0426 | fail |
| 30 | B1_near_120d_high_plus_volume_expansion | 3,927 | 16.552% | 1.0350 | -0.0723 | fail |
| 53 | B6_low_drawdown_reclaim_or_ema_reclaim | 15,406 | 18.155% | 1.0029 | -0.0971 | fail |
| 60 | EP07_topn_multichannel_recommended_union | 5,116 | 16.634% | 0.9942 | -0.1058 | fail |
| 128 | B4_volatility_contraction_then_breakout | 11,772 | 12.504% | 0.7756 | -0.3244 | fail |

当前 `+50 / 120d` label 的经验结构更偏向：

```text
relative strength
high recent return
high cross-sectional rank
high volatility / range
positive trend continuation
```

不偏向：

```text
generic volume expansion
generic near high
low volatility contraction
wide repair/reclaim state
broad union candidate set
```

## 5. B2 为什么最接近

B2 best cell:

```text
stock_vs_market_20d_min = 0.15
return_60d_rank_pct_min = 0.80
close_to_ema60_min = 0.00
market_regime_filter = all
```

全 baseline eligible universe 中，`+50 / 120d` 明显偏好相对强势和横截面强势：

```text
stock_vs_market_return_20d highest quintile +50 rate ~= 19.8%
return_60d_cross_section_rank_pct highest quintile +50 rate ~= 20.8%
close_to_ema60 highest quintile +50 rate ~= 20.2%
```

B2 正好直接使用这些变量，因此自然最接近。但 B2 的 lift 目前不能归因，因为
候选和 baseline 在 matching features 上仍严重不平衡，尤其 `match_return20`：

| baseline | candidate match_return20 mean | baseline match_return20 mean | SMD |
|---|---:|---:|---:|
| calendar-time | 28.47% | 2.39% | 1.188 |
| instrument-matched | 28.47% | 3.45% | 1.101 |
| LSV matched | 28.47% | 18.78% | 0.451 |

Conclusion:

B2 是下一轮最值得继续修的方向，但当前证据是“相对强势暴露有 train diagnostic”，
不是“B2 已经是稳健右尾水库”。修复 baseline 前，B2 的 tail lift 可能只是近期强动量
暴露没有被 baseline 充分中和。

## 6. 其他 Family 失败原因

### 6.1 B5 Recent High Close + Amount Expansion

B5 的 p50 为 18.878%，明显高于整体 base rate，但 matched lift 太薄：

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 18.878% | 15.933% | 1.1848 | 0.0848 |
| instrument-matched | 18.878% | 17.854% | 1.0574 | -0.0426 |
| LSV matched | 18.878% | 17.772% | 1.0622 | -0.0378 |

`return_10d_min` 越高，p50 越高；`close_position` 更高没有明显增益；amount
threshold 过高也没有明显改善。B5 应保留为 secondary trend-continuation family，
下一轮重点强化 `return_10d`、相对强度和 60d 横截面 rank，而不是继续提高 amount。

### 6.2 B1 Near 120d High + Volume Expansion

B1 best cell 的 p50 只有 16.552%，接近整体 baseline eligible pool 的 16.09%。
calendar baseline 下有轻微 lift，但 instrument / LSV baseline 后基本被吃掉：

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 16.552% | 14.719% | 1.1246 | 0.0088 |
| instrument-matched | 16.552% | 15.992% | 1.0350 | -0.0723 |
| LSV matched | 16.552% | 15.508% | 1.0673 | -0.0451 |

当前 B1 更像普通强势/放量状态，不像真实突破机制。修复方向应从
“near high + volume” 改成 “relative-strength breakout confirmation”：

```text
actual 120d high breakout
close in upper daily range
breakout hold / reclaim
relative strength confirmation
volume as confirmation only
```

### 6.3 B6 Low Drawdown Reclaim / EMA Reclaim

B6 的 p50 为 18.155%，但 instrument matched 后几乎无 lift：

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 18.155% | 16.435% | 1.1047 | 0.0047 |
| instrument-matched | 18.155% | 18.103% | 1.0029 | -0.0971 |
| LSV matched | 18.155% | 17.837% | 1.0178 | -0.0822 |

该结论依赖未通过 SMD 的 matched baseline，因此只能作为 hypothesis。更稳妥的下一步是
把 B6 降级为 regime / participation filter，优先测试它是否能改善 B2/B5，而不是作为
独立 primary family 扩网格。

### 6.4 B4 Volatility Contraction Then Breakout

B4 的方向与当前 `+50 / 120d` 标签结构相反：

```text
atr_20_pct_rank:
    low quintile +50 rate ~= 7.9%
    high quintile +50 rate ~= 23.6%

intraday_range_pct:
    low quintile +50 rate ~= 9.9%
    high quintile +50 rate ~= 20.7%
```

B4 当前选 low ATR / low intraday range，等于主动避开 +50 标签偏好的高波动区域。
这是 baseline-independent descriptive evidence，足以支持把当前 B4 下线或改写为：

```text
prior compression
current expansion / breakout trigger
amount expansion
close breakout / close in high range
```

### 6.5 EP07 TopN Multichannel Union

EP07 union 的 p50 为 16.634%，只略高于整体 base rate。它可能更像 recall reservoir，
不是 precision family：

| baseline | p_candidate_50 | p_matched_50 | lift | adjusted |
|---|---:|---:|---:|---:|
| calendar-time | 16.634% | 16.732% | 0.9942 | -0.1058 |
| instrument-matched | 16.634% | 15.715% | 1.0585 | -0.0415 |
| LSV matched | 16.634% | 16.380% | 1.0155 | -0.0845 |

下一轮不应把 EP07 union 整体提升为 primary precision family。需要按 source/channel
拆分，分别评估 denominator、p50、matched lift、false-positive burden 和 left-tail burden。

## 7. Estimand 和 Matching 注意事项

19A 冻结的 `primary_tail_lift_50` 当前不是跨 family 完全统一的 estimand。默认
matching 已控制部分 amount / recent return，而这些变量对 B1/B5 是规则信号的一部分。
因此 B1/B5 的 primary readout 更接近：

```text
residual lift after controlling part of the family signal exposure
```

而对其他 family，同名指标更接近：

```text
total lift versus the frozen matched baseline
```

下一轮 requirement 必须在 outcome readout 前冻结 family-specific signal/control map：

```text
signal primitives = exactly the feature_fields in the frozen predicate_formula
19A already-controlled covariates not in predicate_formula remain controlled confounders
signal matching is attribution-only, not primary baseline
```

特别地，B2 的 signal 是 `stock_vs_market_20d`、`return_60d_rank` 和
`close_to_ema60`；raw `return_20d` 对 B2 仍应作为 confounder 受控。

## 8. 下一步

不建议盲目扩大全部网格。下一步应增加的是有约束的搜索空间：

```text
1. baseline repair search:
   per-feature SMD, coarser bucket, caliper / nearest-neighbor, common support audit

2. B2 attribution ablation:
   stock_vs_market_20d only
   return_60d_rank only
   stock_vs_market_20d + return_60d_rank
   with / without close_to_ema60
   with / without market regime

3. B5 sharpening:
   higher return_10d_min, relative strength, return_60d rank

4. B1 rewrite:
   actual breakout, close-in-range, hold/reclaim, relative strength

5. B4 replacement:
   volatility spring instead of low-vol primary entry

6. EP07 channel split:
   source/channel-level precision readout

7. B6 interaction:
   regime/filter interaction for B2/B5 before standalone expansion
```

新增 primary-claim family/cell 必须进入 primary all-tried accounting；B2 attribution
ablation 等 attribution-only cells 应单独计量，不混入 primary correction。

推荐下一份 requirement：

```text
requirement_19b0_1_baseline_repair_and_family_ablation_scan.md
```

## 9. Authorization

19B0 不授权模型、entry/exit/holding policy、回测、生产信号或交易。进入 19B 的资格
不是 support claim；本轮也没有任何 family/cell 获得该资格。
