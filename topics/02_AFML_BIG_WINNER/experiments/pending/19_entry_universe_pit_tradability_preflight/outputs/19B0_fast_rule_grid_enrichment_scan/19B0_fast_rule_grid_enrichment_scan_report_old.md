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

Post-review contract note:

- 按修订后的双轨口径，`baseline_matching_quality_gate = fail` 只阻断
  residual-alpha 归因，不自动否定 positive beta/exposure 右尾水库诊断。
- 本报告未按修订后的 `positive_exposure_margin_50` 公式重跑；未来若启用
  positive-beta track，必须同时披露 broad baseline-eligible base rate、0.02 绝对概率点
  margin、相对基率 margin 和最终采用的 margin。
- 即使 positive-beta track 在 19B 证明 exposure persistence，只要没有另行取得
  matched-baseline residual pass，EP19 最多只能输出
  `19_entry_universe_enrichment_only_diagnostic`，不得授权 EP20 或 entry policy preflight。
- positive-beta 晋升不代表独立 alpha 或筛选力，只代表存在暴露型右尾水库。

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

### 3.1 Universe 和 Denominator 明细

19B0 的失败不是由 entry anchor、可成交性、120d path completeness 或候选 denominator
造成。train universe 到 baseline eligible 的主要损耗来自 matching feature availability 和
baseline eligible 过滤。

| stage | rows | instruments | months | matching fields available | filtered out |
|---|---:|---:|---:|---:|---:|
| raw_train_universe | 607,536 | 1,407 | 60 | 88.09% | 0 |
| entry_anchor_available | 607,536 | 1,407 | 60 | 88.09% | 0 |
| entry_fill_feasible | 607,536 | 1,407 | 60 | 88.09% | 0 |
| path_complete_120d | 607,536 | 1,407 | 60 | 88.09% | 0 |
| matching_fields_available | 535,171 | 1,103 | 57 | 100.00% | 72,365 |
| baseline_eligible | 433,131 | 1,010 | 49 | 100.00% | 102,040 |

Interpretation:

- `entry_anchor_available`、`entry_fill_feasible` 和 `path_complete_120d` 没有损耗；
  说明 19B0 的 executable-entry 标签重建链路可用。
- 从 607,536 到 535,171 的 72,365 行损耗来自 matching feature availability；这会让
  后续 baseline repair 必须先保护 common support，而不是只调规则阈值。
- baseline eligible 进一步降到 433,131 行、1,010 只股票、49 个 decision month；
  该规模足够支持 same-budget 抽样，因此不是 sample-size block。

### 3.2 Grid 物化明细

| family | declared cells | materialized cells | missing cells | missing feature count |
|---|---:|---:|---:|---:|
| B1_near_120d_high_plus_volume_expansion | 36 | 36 | 0 | 0 |
| B2_relative_strength_breakout | 36 | 36 | 0 | 0 |
| B4_volatility_contraction_then_breakout | 36 | 36 | 0 | 0 |
| B5_recent_high_close_plus_amount_expansion | 36 | 36 | 0 | 0 |
| B6_low_drawdown_reclaim_or_ema_reclaim | 36 | 18 | 18 | 18 |
| EP07_topn_multichannel_recommended_union | 1 | 1 | 0 | 0 |

Interpretation:

- B1/B2/B4/B5 和 EP07 均完整物化；B6 只有一半网格可用，失败来自依赖特征缺失。
- B6 未物化的 18 个 cell 均是 `early_no_false_repair_10d_required=true` 分支，
  denominator audit 的 blocking reason 为
  `early_no_false_repair_10d_requires_ep07_direct_only`。
- materialization 是 `before_label_readout`，所以 family/cell registry 没有 label leakage。
- denominator audit 覆盖 181 个 declared cells；实际进入 metric / baseline readout 的是
  163 个 materialized cells（489 个 baseline-family-cell rows）。19B0 的 fail-closed
  结论不是“没有可测试规则”，而是“进入 readout 的 cell 全部无法通过 matched baseline
  quality gate”。

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

按 family 分解，B6 和 EP07 的 SMD 相对较低，但仍全部超过 0.10；B1/B2/B5 的
SMD 更高，说明最有 alpha 感的强势/趋势规则也最容易把 baseline 推出 covariate balance。

| family | rows | pass_n | unmatched median | unmatched max | SMD median | SMD min | SMD max | month delta median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B6_low_drawdown_reclaim_or_ema_reclaim | 54 | 0 | 0.1271 | 0.2189 | 0.5888 | 0.1771 | 0.7842 | 0.0222 |
| EP07_topn_multichannel_recommended_union | 3 | 0 | 0.0004 | 0.0266 | 0.7042 | 0.2495 | 0.7785 | 0.0023 |
| B4_volatility_contraction_then_breakout | 108 | 0 | 0.1722 | 0.2615 | 0.9532 | 0.2528 | 1.3011 | 0.0234 |
| B2_relative_strength_breakout | 108 | 0 | 0.1350 | 0.3266 | 0.9904 | 0.2366 | 1.2433 | 0.0302 |
| B5_recent_high_close_plus_amount_expansion | 108 | 0 | 0.0944 | 0.2086 | 1.0246 | 0.3278 | 1.2366 | 0.0216 |
| B1_near_120d_high_plus_volume_expansion | 108 | 0 | 0.1322 | 0.2337 | 1.0328 | 0.2847 | 1.4680 | 0.0355 |

更细的 baseline 视角：

| baseline family | rows | pass_n | unmatched median | unmatched max | reuse max | SMD median | SMD min | SMD max | month delta max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| calendar_time_random_same_budget | 163 | 0 | 0.1287 | 0.2423 | 0.0095 | 1.0640 | 0.4956 | 1.3966 | 0.0438 |
| instrument_matched_random_same_budget | 163 | 0 | 0.0230 | 0.0542 | 0.0043 | 1.0918 | 0.5196 | 1.4680 | 0.1053 |
| liquidity_size_volatility_matched_same_budget | 163 | 0 | 0.2061 | 0.3266 | 0.0138 | 0.3917 | 0.1771 | 0.7973 | 0.0438 |

Insight:

- `instrument_matched` 能压低 unmatched，但 SMD 最差且 month delta 最坏，说明只按股票匹配
  不能中和候选的状态暴露。
- `LSV` 能显著压低 SMD，但 unmatched 明显升高，说明更接近正确方向，但 common support
  变窄。
- 没有任何 arm 触发 baseline reuse 问题；下一轮不应优先修 reuse，应优先修
  `max_SMD` 与 `unmatched_candidate_rate` 的联合可满足性。

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

### 4.1 Top 15 Cell 明细

Top 15 中 14 个来自 B2，唯一非 B2 是 B5 rank 14。这说明本轮 train diagnostic
几乎是由相对强势/横截面强势轴主导，而不是由近高点、放量、低波压缩或 EP07 union 主导。

| rank | family | candidate_n | p50 | conservative lift | adjusted | key parameters |
|---:|---|---:|---:|---:|---:|---|
| 1 | B2 | 5,927 | 22.473% | 1.1036 | 0.0036 | stock_vs_market_20d>=0.15; rank60>=0.80; close_to_ema60>=0.00; all |
| 2 | B2 | 5,923 | 22.489% | 1.1026 | 0.0026 | stock_vs_market_20d>=0.15; rank60>=0.80; close_to_ema60>=0.02; all |
| 3 | B2 | 5,058 | 22.262% | 1.0975 | -0.0025 | stock_vs_market_20d>=0.10; rank60>=0.90; close_to_ema60>=0.00; all |
| 4 | B2 | 7,018 | 21.659% | 1.0943 | -0.0057 | stock_vs_market_20d>=0.15; rank60>=0.70; close_to_ema60>=0.00; all |
| 5 | B2 | 4,061 | 22.901% | 1.0864 | -0.0136 | stock_vs_market_20d>=0.15; rank60>=0.90; close_to_ema60>=0.00; all |
| 6 | B2 | 6,088 | 21.583% | 1.0797 | -0.0203 | stock_vs_market_20d>=0.05; rank60>=0.90; close_to_ema60>=0.00; all |
| 7 | B2 | 10,142 | 20.223% | 1.0795 | -0.0205 | stock_vs_market_20d>=0.05; rank60>=0.80; close_to_ema60>=0.00; all |
| 8 | B2 | 7,897 | 21.109% | 1.0783 | -0.0217 | stock_vs_market_20d>=0.10; rank60>=0.80; close_to_ema60>=0.02; all |
| 9 | B2 | 5,047 | 22.251% | 1.0767 | -0.0233 | stock_vs_market_20d>=0.10; rank60>=0.90; close_to_ema60>=0.02; all |
| 10 | B2 | 4,057 | 22.899% | 1.0740 | -0.0260 | stock_vs_market_20d>=0.15; rank60>=0.90; close_to_ema60>=0.02; all |
| 11 | B2 | 9,978 | 20.425% | 1.0732 | -0.0268 | stock_vs_market_20d>=0.05; rank60>=0.80; close_to_ema60>=0.02; all |
| 12 | B2 | 6,047 | 21.631% | 1.0678 | -0.0322 | stock_vs_market_20d>=0.05; rank60>=0.90; close_to_ema60>=0.02; all |
| 13 | B2 | 3,570 | 22.101% | 1.0576 | -0.0425 | stock_vs_market_20d>=0.05; rank60>=0.90; close_to_ema60>=0.02; risk_on |
| 14 | B5 | 8,592 | 18.878% | 1.0574 | -0.0426 | return_10d>=0.06; close_position>=0.70; amount_ratio>=1.2; quality_amount=true |
| 15 | B2 | 4,037 | 21.625% | 1.0556 | -0.0444 | stock_vs_market_20d>=0.15; rank60>=0.70; close_to_ema60>=0.00; risk_on |

Insight:

- B2 的 best cell 不是孤立尖峰；前 13 名几乎都落在 B2 的相邻参数区间，说明方向有
  train 稳定性。
- `risk_on` 过滤没有提升排序；Top 12 全是 `market_regime_filter=all`，说明本轮 B2
  的信号主要来自个股相对强势，而不是只来自市场环境过滤。
- B5 的最好 cell 只排第 14，而且 adjusted 仍为负；它更像 B2 的趋势 continuation
  confirmation，而不是独立 primary family。

### 4.2 Family 分布明细

| family | cell_n | candidate_n median | p50 median | p50 max | adjusted median | adjusted max |
|---|---:|---:|---:|---:|---:|---:|
| B2_relative_strength_breakout | 36 | 5,801 | 21.628% | 22.901% | -0.0518 | 0.0036 |
| B5_recent_high_close_plus_amount_expansion | 36 | 5,319 | 18.566% | 20.283% | -0.1030 | -0.0426 |
| B1_near_120d_high_plus_volume_expansion | 36 | 4,438 | 16.443% | 17.583% | -0.1433 | -0.0723 |
| B6_low_drawdown_reclaim_or_ema_reclaim | 18 | 21,120 | 17.181% | 18.308% | -0.1222 | -0.0971 |
| EP07_topn_multichannel_recommended_union | 1 | 5,116 | 16.634% | 16.634% | -0.1058 | -0.1058 |
| B4_volatility_contraction_then_breakout | 36 | 7,664 | 10.425% | 12.504% | -0.4573 | -0.3244 |

Interpretation:

- B2 同时有最高 p50、最高 adjusted、且 top-cell cluster 密集，是唯一值得继续做
  attribution repair 的 family。
- B4 的 family distribution 整体偏低，不是单个 cell 配置差，而是 family 方向与标签
  结构不匹配。
- B6 denominator 最大，但 adjusted 不好，说明“宽泛 reclaim/filter”提升 precision 的能力弱。

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

### 5.1 B2 参数轴读数

| axis | value | cell_n | candidate_n median | p50 median | p50 max | adjusted max |
|---|---:|---:|---:|---:|---:|---:|
| stock_vs_market_20d_min | 0.05 | 12 | 6,932 | 20.164% | 22.110% | -0.0203 |
| stock_vs_market_20d_min | 0.10 | 12 | 5,366 | 21.052% | 22.492% | -0.0025 |
| stock_vs_market_20d_min | 0.15 | 12 | 4,047 | 22.325% | 22.901% | 0.0036 |
| return_60d_rank_pct_min | 0.70 | 12 | 7,397 | 20.278% | 21.659% | -0.0057 |
| return_60d_rank_pct_min | 0.80 | 12 | 5,982 | 21.052% | 22.489% | 0.0036 |
| return_60d_rank_pct_min | 0.90 | 12 | 3,815 | 22.377% | 22.901% | -0.0025 |
| close_to_ema60_min | 0.00 | 18 | 5,803 | 21.604% | 22.901% | 0.0036 |
| close_to_ema60_min | 0.02 | 18 | 5,798 | 21.630% | 22.899% | 0.0026 |
| market_regime_filter | all | 18 | 7,012 | 21.607% | 22.901% | 0.0036 |
| market_regime_filter | risk_on | 18 | 4,036 | 21.628% | 22.798% | -0.0425 |

Insight:

- `stock_vs_market_20d_min` 提高时，p50 单调改善，且 adjusted max 从 -0.0203 提升到
  0.0036；这是 B2 最核心的轴。
- `return_60d_rank_pct_min=0.80` 比 0.90 更稳健：0.90 p50 略高但 denominator 更小，
  conservative adjusted 反而略差。
- `close_to_ema60_min` 从 0 到 0.02 几乎不改变 p50；它可能是冗余过滤，不应作为下一轮
  主扩展轴。
- `risk_on` 明显压缩 denominator 且降低 adjusted max；下一轮应先在 `all` 下做 attribution，
  再把 market regime 作为 sensitivity，而不是 primary predicate。

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

B5 参数轴读数：

| axis | value | cell_n | candidate_n median | p50 median | p50 max | adjusted max |
|---|---:|---:|---:|---:|---:|---:|
| return_10d_min | 0.03 | 12 | 6,504 | 18.056% | 18.239% | -0.0629 |
| return_10d_min | 0.06 | 12 | 5,852 | 18.566% | 18.878% | -0.0426 |
| return_10d_min | 0.10 | 12 | 4,686 | 19.663% | 20.283% | -0.0565 |
| close_position_in_120d_range_min | 0.70 | 12 | 7,491 | 18.650% | 20.283% | -0.0426 |
| close_position_in_120d_range_min | 0.85 | 12 | 5,530 | 18.489% | 19.832% | -0.0654 |
| close_position_in_120d_range_min | 0.95 | 12 | 3,436 | 18.566% | 19.606% | -0.0926 |
| amount_ratio_20d_min | 1.20 | 18 | 6,442 | 18.736% | 20.283% | -0.0426 |
| amount_ratio_20d_min | 1.50 | 18 | 5,263 | 18.423% | 19.721% | -0.0740 |
| quality_amount_flag_required | false_or_missing_allowed | 18 | 5,319 | 18.566% | 20.283% | -0.0549 |
| quality_amount_flag_required | true | 18 | 5,319 | 18.566% | 20.283% | -0.0426 |

Insight:

- `return_10d_min` 是 B5 内部最有方向性的轴；但 0.10 虽提高 p50，却损失 denominator，
  conservative adjusted 不如 0.06。
- `close_position` 提高到 0.85/0.95 没有带来匹配后的收益，说明“收在 120d 区间高位”
  不是独立 edge。
- `amount_ratio_20d_min=1.5` 比 1.2 更差；继续提高 amount threshold 不是修复方向。

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

### 6.6 Sensitivity 和 Concentration 读数

Best cell 的 concentration 风险不高；top instrument share 都低于 0.51%，winner share
低于 1.18%。因此本轮不是由少数股票集中贡献造成的虚假 lift。

| family best cell | max instrument candidate share | max instrument winner share | top1 removed conservative lift range | top3 removed conservative lift range |
|---|---:|---:|---:|---:|
| B2 | 0.506% | 0.976% | 1.0992-1.4039 | 1.0978-1.4021 |
| B5 | 0.454% | 1.171% | 1.0497-1.1763 | 1.0422-1.1679 |
| B1 | 0.382% | 1.077% | 1.0310-1.1202 | 1.0352-1.1248 |
| B6 | 0.370% | 1.001% | 0.9965-1.0977 | 0.9961-1.0972 |
| EP07 | 0.371% | 0.940% | 0.9943-1.0587 | 0.9930-1.0572 |
| B4 | 0.425% | 1.155% | 0.7730-0.9723 | 0.7693-0.9676 |

Path sensitivity:

| family best cell | p20 | p60 | p120 | fast_fail_rate | MAE20 p10 | MFE120 p90 |
|---|---:|---:|---:|---:|---:|---:|
| B2 | 3.678% | 12.198% | 22.473% | 53.467% | -23.764% | 77.753% |
| B5 | 3.014% | 10.382% | 18.878% | 45.240% | -21.922% | 70.898% |
| B6 | 2.337% | 9.373% | 18.155% | 43.645% | -21.100% | 68.490% |
| B1 | 3.005% | 9.779% | 16.552% | 40.820% | -21.476% | 66.386% |
| EP07 | 1.153% | 7.174% | 16.634% | 30.414% | -16.667% | 64.334% |
| B4 | 0.875% | 5.386% | 12.504% | 25.459% | -15.648% | 56.141% |

Insight:

- B2 的右尾最强，但 fast-fail 也最高；它更像高波动强趋势暴露，而不是低风险稳态信号。
- EP07 union 的 fast-fail 最低，但 p120 不高；它可能适合作 recall reservoir，而不是
  precision selector。
- B4 的 MAE 较温和但 MFE/p120 明显低，说明“低波压缩”当前是在降低波动和右尾，而不是
  提高右尾捕获。
- B2/B5/B6 都有 40%-53% fast-fail，下一轮如果继续做 entry universe，需要同时报告
  right-tail enrichment 和 early adverse-path burden，不能只看 +50。

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

若后续按修订合同允许 `positive_beta_exposure_candidate` 进入 19B，该 track 的授权上限
仍是 diagnostic：没有 matched-baseline residual pass 时，不得把 exposure persistence
升级为 `19_entry_universe_pit_tradability_and_enrichment_supported`，也不得授权 EP20。
