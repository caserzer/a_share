# R03e family signal bad-shape filter 诊断报告

## 结论

- final_decision: `badshape_filter_no_incremental_edge`
- validation: `passed`, failed checks: `0`, check_count: `36`
- primary grain: `r02_signal_episode_start / r02_episode_start / all_families_dedup_weighted / filter_decision_next_open_anchor`
- 核心形态窗口: `T-10..T-1 + T+1..T+10`，T0 只作为开仓锚点，不进入 BadScore。
- materialized OHLCV 窗口: `-252..+131`；长历史 ATR/MA as-of 用 provider full history 计算。
- baseline_1: T+10 survivor + BadScore 可评估 + filter next-open 120d path complete。

核心结论很直接：当前 BadScore V1 不能作为 family 信号后 T+10 新开仓的硬过滤器。`drop_score_ge5` 在 validation 与 robustness 都没有降低 `P_bad`，反而让 `P_bad` 小幅上升；同时 big winner rate 下降。因此它既没有降低坏路径，也没有保留 winner 上行空间。

更重要的是，BadScore 分数本身没有呈现“分数越高、后续越差”的单调关系。高分桶不一定更坏，低分桶也不明显更好。这说明当前这 10 个坏形态更多是在描述“family 信号后已经进入高波动/高分歧状态”，但没有稳定地区分后续好坏路径。

## 样本与输入

| 项目 | 数值 |
|:---|---:|
| r02_signal_episode_start events | 97,836 |
| r03_seed_family_event events | 28,551 |
| r03_clean_fresh_family_event events | 21,235 |
| 全部 family signal events | 147,622 |
| 全部 baseline_1 events | 21,589 |
| 全部 BadScore complete rate | 19.54% |
| OHLCV window rows | 56,686,848 |
| OHLCV window offset range | -252..+131 |

输入 readiness 全部通过。R02 precision、R02 path-query、R03b、R03c 的 validation artifact 都是 `passed`。这次报告只分析已有产物，没有重新定义实验口径。

## Primary 样本漏斗

Primary 只看 R02 单 family episode-start，并在同一股票同一天多 family 时使用 dedup weight。这个 denominator 不是所有 T0 信号，而是严格的 “T+10 survivor + BadScore complete + filter-anchor 120d path complete”。

| split | baseline | event_count | weighted_count | shape_eval_complete | bad_score_complete | filter_path_complete | signal_anchor_big_winner_rate |
|:---|:---|---:|---:|---:|---:|---:|---:|
| train | all_events | 46,729 | 22,269 | 98.77% | 18.35% | 81.61% | 12.76% |
| train | baseline_1 | 7,471 | 3,387 | 100.00% | 100.00% | 100.00% | 28.31% |
| validation | all_events | 24,429 | 12,004 | 97.95% | 11.54% | 77.07% | 4.67% |
| validation | baseline_1 | 2,557 | 1,188 | 100.00% | 100.00% | 100.00% | 8.92% |
| robustness | all_events | 26,678 | 12,959 | 96.86% | 23.23% | 67.83% | 6.69% |
| robustness | baseline_1 | 4,144 | 1,926 | 100.00% | 100.00% | 100.00% | 6.44% |
| all | all_events | 97,836 | 47,232 | 98.04% | 17.96% | 76.67% | 9.04% |
| all | baseline_1 | 14,172 | 6,501 | 100.00% | 100.00% | 100.00% | 18.29% |

这个漏斗提示一个重要限制：BadScore complete rate 偏低，尤其 validation 只有 11.54%。因此 headline 不是全体 family signal 的结果，而是一个历史覆盖、T+10 生存、filter path 都满足的子样本。这个子样本的 winner rate 也可能与 baseline_0 有明显差异。

## Primary Threshold 结果

`drop_score_ge5` 是 requirement 里的 primary filter。结果不支持。

| split | policy | baseline_n | passed_n | drop_rate | dropped_p_bad | P_good | P_bad | P_good - P_bad | big_winner_rate | delta_P_bad | delta_P_good | delta_edge | signal_anchor_winner_retention |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| validation | no_filter | 2,557 | 2,557 | 0.00% | NA | 11.11% | 86.95% | -75.84% | 7.74% | 0.00pp | 0.00pp | 0.00pp | 100.00% |
| validation | drop_score_ge3 | 2,557 | 1,063 | 58.33% | 86.44% | 10.71% | 87.68% | -76.97% | 5.45% | +0.72pp | -0.40pp | -1.13pp | 47.17% |
| validation | drop_score_ge5 | 2,557 | 1,994 | 21.72% | 85.66% | 11.51% | 87.31% | -75.81% | 7.10% | +0.36pp | +0.39pp | +0.04pp | 87.74% |
| validation | drop_score_ge7 | 2,557 | 2,341 | 8.75% | 84.62% | 10.89% | 87.18% | -76.29% | 7.38% | +0.22pp | -0.23pp | -0.45pp | 97.17% |
| robustness | no_filter | 4,144 | 4,144 | 0.00% | NA | 16.30% | 82.97% | -66.67% | 4.05% | 0.00pp | 0.00pp | 0.00pp | 100.00% |
| robustness | drop_score_ge3 | 4,144 | 1,582 | 60.85% | 81.31% | 14.19% | 85.54% | -71.35% | 3.85% | +2.57pp | -2.11pp | -4.69pp | 38.71% |
| robustness | drop_score_ge5 | 4,144 | 3,500 | 16.56% | 80.56% | 16.12% | 83.45% | -67.33% | 3.73% | +0.48pp | -0.19pp | -0.66pp | 96.77% |
| robustness | drop_score_ge7 | 4,144 | 3,954 | 4.78% | 80.43% | 16.19% | 83.10% | -66.90% | 4.09% | +0.13pp | -0.11pp | -0.24pp | 99.19% |

解读：

- `drop_score_ge5` 删掉 validation 21.72% 样本、robustness 16.56% 样本，但删掉的样本 `dropped_p_bad` 反而低于 parent `P_bad`。这意味着它不是在优先剔除坏路径，而是在剔除一批相对没有更坏的样本。
- `drop_score_ge3` 更激进，删除 58%-61% 样本，但 P_bad 明显变差，并且 signal-anchor winner retention 只有 47.17% / 38.71%。这个阈值不可用。
- `drop_score_ge7` 太弱，删除样本很少，也没有改善结果。
- `drop_score_ge5` validation 的 `P_good - P_bad` 只改善 0.04pp，robustness 反而恶化 0.66pp，不满足稳定性。

## BadScore 分桶

如果 BadScore 有用，应该看到 `0_2` 明显好于 `5_6` / `7plus`，至少 `P_bad` 应随分数上升而上升。实际没有这个结构。

| split | bucket | event_count | P_good | P_bad | P_good - P_bad | big_winner_rate |
|:---|:---|---:|---:|---:|---:|---:|
| validation | 0_2 | 1,063 | 10.71% | 87.68% | -76.97% | 5.45% |
| validation | 3_4 | 931 | 12.41% | 86.90% | -74.48% | 8.97% |
| validation | 5_6 | 347 | 7.14% | 86.36% | -79.22% | 9.09% |
| validation | 7plus | 216 | 13.46% | 84.62% | -71.15% | 11.54% |
| robustness | 0_2 | 1,582 | 14.19% | 85.54% | -71.35% | 3.85% |
| robustness | 3_4 | 1,918 | 17.82% | 81.59% | -63.77% | 3.63% |
| robustness | 5_6 | 454 | 16.74% | 80.62% | -63.88% | 6.61% |
| robustness | 7plus | 190 | 18.48% | 80.43% | -61.96% | 3.26% |

最明显的问题是：`7plus` 在两个 OOS split 中都不是最坏桶。validation 里 `7plus` 的 P_bad 是 84.62%，低于 `0_2` 的 87.68%；robustness 里 `7plus` 的 P_bad 是 80.43%，也低于 `0_2` 的 85.54%。这基本否定了当前 BadScore 的单调过滤假设。

## Component 触发率

下面是 primary scope 中各 component 的 non-null 样本触发率。这里是 component 自身覆盖，不等于 headline baseline_1 denominator。

| split | component | non_null_n | true_rate | true_count |
|:---|:---|---:|---:|---:|
| validation | failed_breakout | 3,188 | 88.68% | 2,812 |
| validation | dense_upper_shadow | 23,339 | 71.09% | 16,705 |
| validation | ma20_break_no_reclaim | 19,948 | 34.09% | 6,289 |
| validation | volatility_up_no_price | 22,056 | 19.15% | 4,246 |
| validation | lower_low_lower_high | 23,339 | 19.13% | 4,163 |
| validation | large_bearish_engulf | 23,339 | 17.71% | 4,102 |
| validation | volume_stall | 23,319 | 17.62% | 4,019 |
| validation | low_upside_efficiency | 22,056 | 17.50% | 4,104 |
| validation | gap_up_fade | 23,339 | 15.90% | 3,922 |
| validation | down_volume_dominance | 23,326 | 14.00% | 2,894 |
| robustness | failed_breakout | 6,920 | 88.66% | 6,168 |
| robustness | dense_upper_shadow | 25,599 | 73.41% | 18,858 |
| robustness | ma20_break_no_reclaim | 20,675 | 26.82% | 5,003 |
| robustness | large_bearish_engulf | 25,599 | 20.50% | 5,343 |
| robustness | down_volume_dominance | 25,596 | 18.67% | 4,388 |
| robustness | low_upside_efficiency | 24,933 | 16.56% | 4,196 |
| robustness | gap_up_fade | 25,599 | 14.51% | 4,032 |
| robustness | volume_stall | 25,558 | 14.47% | 3,565 |
| robustness | lower_low_lower_high | 25,599 | 14.24% | 3,295 |
| robustness | volatility_up_no_price | 24,933 | 14.11% | 3,448 |

`failed_breakout` 和 `dense_upper_shadow` 的触发率过高。一个过滤器如果在 family 信号后的样本里触发 70%-89%，它更像是在识别“family 信号之后常见的高波动/冲高回落环境”，而不是识别少数应避免的坏形态。它们单独作为 filter 时删除太多样本，容易把有效样本一起删掉。

## Component Policy 效果

单 component policy 的结果也不稳定。少数组件在某个 split 能降低 P_bad，但通常伴随严重样本删除或 winner retention 过低。

| split | policy | baseline_n | passed_n | drop_rate | dropped_p_bad | P_good | P_bad | delta_P_bad | delta_edge | winner_retention |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| validation | drop_gap_up_fade | 2,557 | 2,130 | 16.33% | 99.48% | 13.18% | 84.51% | -2.45pp | +4.51pp | 77.36% |
| validation | drop_ma20_break_no_reclaim | 1,726 | 1,462 | 15.24% | 87.60% | 12.04% | 85.74% | -1.22pp | +2.14pp | 92.31% |
| validation | drop_failed_breakout | 2,557 | 307 | 88.64% | 86.51% | 8.89% | 90.37% | +3.42pp | -5.64pp | 15.09% |
| validation | drop_dense_upper_shadow | 2,557 | 687 | 72.31% | 86.50% | 9.42% | 88.15% | +1.19pp | -2.88pp | 39.62% |
| validation | drop_volume_stall | 2,557 | 2,185 | 15.07% | 79.89% | 10.70% | 88.21% | +1.25pp | -1.66pp | 96.23% |
| validation | drop_volatility_up_no_price | 2,557 | 1,975 | 22.56% | 81.72% | 10.00% | 88.48% | +1.53pp | -2.64pp | 92.45% |
| robustness | drop_dense_upper_shadow | 4,144 | 1,202 | 70.51% | 84.39% | 20.07% | 79.58% | -3.39pp | +7.16pp | 16.94% |
| robustness | drop_failed_breakout | 4,144 | 487 | 87.75% | 83.43% | 19.49% | 79.66% | -3.31pp | +6.50pp | 8.87% |
| robustness | drop_gap_up_fade | 4,144 | 3,338 | 18.48% | 94.10% | 18.79% | 80.45% | -2.52pp | +5.01pp | 73.39% |
| robustness | drop_volume_stall | 4,144 | 3,735 | 10.28% | 86.36% | 16.67% | 82.58% | -0.39pp | +0.75pp | 98.39% |
| robustness | drop_down_volume_dominance | 4,144 | 3,072 | 27.67% | 75.05% | 13.21% | 86.00% | +3.03pp | -6.13pp | 84.68% |
| robustness | drop_large_bearish_engulf | 4,144 | 2,666 | 34.74% | 80.42% | 15.51% | 84.33% | +1.36pp | -2.15pp | 68.55% |

有两个值得注意的细节：

- `gap_up_fade` 是少数在 validation 与 robustness 都降低 P_bad 的 component，但它的 winner retention 只有 77.36% / 73.39%，只略高于 70% 保留线，安全边际不够，且没有作为 BadScore 组合贡献出稳定结果。它可以作为后续研究候选，但不应直接硬过滤。
- `failed_breakout` 和 `dense_upper_shadow` 在 robustness 看起来降低 P_bad，但删除 70%-88% 样本，并且 winner retention 只有 8.87%-16.94% 或 16.94%-39.62%。这类规则代价太高，不能用于新开仓过滤。

## Component Overlap

高 overlap 解释了为什么 BadScore 累加没有形成有效排序：很多 component 在同一批高波动样本上同时触发，新增分数并没有提供独立信息。

| split | component_a | component_b | eligible_n | both_true_rate | jaccard |
|:---|:---|:---|---:|---:|---:|
| validation | failed_breakout | dense_upper_shadow | 2,557 | 65.74% | 69.05% |
| validation | ma20_break_no_reclaim | lower_low_lower_high | 1,726 | 11.21% | 55.63% |
| validation | volatility_up_no_price | low_upside_efficiency | 2,557 | 15.91% | 48.09% |
| validation | volume_stall | low_upside_efficiency | 2,557 | 13.05% | 45.86% |
| validation | volume_stall | volatility_up_no_price | 2,557 | 11.78% | 45.60% |
| robustness | failed_breakout | dense_upper_shadow | 4,144 | 62.31% | 64.94% |
| robustness | ma20_break_no_reclaim | lower_low_lower_high | 2,719 | 5.80% | 47.65% |
| robustness | failed_breakout | large_bearish_engulf | 4,144 | 32.71% | 36.44% |
| robustness | volatility_up_no_price | low_upside_efficiency | 4,144 | 8.36% | 36.02% |
| robustness | volume_stall | low_upside_efficiency | 4,144 | 7.11% | 31.28% |

`failed_breakout + dense_upper_shadow` 的 Jaccard 在 validation / robustness 都很高。这两个 component 同时触发并不代表两个独立坏信号，而更可能是同一种“冲高回落、高位震荡”的重复刻画。

## Family 维度

按 family 拆开看，`drop_score_ge5` 仍没有找到明显稳定受益的 family。多数 family 在 validation 与 robustness 的 `delta_P_bad` 都为正，即过滤后 P_bad 更高。

| family | validation delta_P_bad | validation delta_edge | robustness delta_P_bad | robustness delta_edge |
|:---|---:|---:|---:|---:|
| momentum_rps | +0.94pp | -1.37pp | +0.94pp | -1.49pp |
| oscillator | +0.26pp | -0.03pp | +0.62pp | -0.97pp |
| price_trend | +1.59pp | -2.41pp | +0.31pp | -0.47pp |
| pullback_drawdown | +1.46pp | -1.89pp | +0.37pp | -0.39pp |
| range_breakout | +0.00pp | -0.33pp | +0.57pp | -0.89pp |
| volatility_band | +0.82pp | -0.72pp | +0.43pp | -0.64pp |
| volume_money | +0.53pp | -0.34pp | +0.34pp | -0.58pp |

这个结果说明问题不是由某个单一 family 拖累。BadScore V1 在 family 粒度上也没有表现出稳定的风险剔除能力。

## R03 Seed/Fresh 旁证

R03 seed-family 与 clean-fresh 只是旁证，不是 primary decision grain。它们的结果与 primary 方向一致：`drop_score_ge5` 没有形成稳定改善。

| split | scope | stage | baseline_n | passed_n | P_good | P_bad | delta_P_bad | delta_edge | delta_big_winner |
|:---|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| validation | r03_seed_family_event | seed_family | 599 | 509 | 11.98% | 86.83% | +1.40pp | -2.49pp | -0.66pp |
| robustness | r03_seed_family_event | seed_family | 1,068 | 908 | 16.84% | 82.49% | +0.91pp | -1.63pp | -0.65pp |
| validation | r03_clean_fresh_family_event | fresh_1 | 357 | 295 | 17.61% | 79.58% | +3.39pp | -4.83pp | +0.49pp |
| robustness | r03_clean_fresh_family_event | fresh_1 | 590 | 523 | 17.80% | 81.78% | +0.33pp | -0.71pp | -0.19pp |
| validation | r03_clean_fresh_family_event | fresh_2 | 209 | 185 | 13.51% | 83.78% | +0.97pp | -0.74pp | +1.08pp |
| robustness | r03_clean_fresh_family_event | fresh_2 | 306 | 266 | 21.64% | 78.36% | +0.64pp | -0.78pp | -1.44pp |
| validation | r03_clean_fresh_family_event | fresh_3 | 106 | 85 | 8.62% | 91.38% | +4.24pp | -5.62pp | +0.89pp |
| robustness | r03_clean_fresh_family_event | fresh_3 | 159 | 130 | 22.22% | 77.78% | +1.41pp | -1.92pp | +1.01pp |

Fresh stage 中样本量更小，个别指标会跳动，但没有哪个 stage 在 validation 与 robustness 同时给出 “P_bad 下降 + edge 改善 + winner 不损失” 的组合。

## Findings

1. `BadScore >= 5` 不应作为新开仓硬过滤器。
   它在 primary OOS 两个 split 都让 P_bad 上升。validation 从 86.95% 升到 87.31%，robustness 从 82.97% 升到 83.45%。

2. 高 BadScore 不是更坏路径。
   `7plus` 分桶在 validation 与 robustness 都不是最坏桶，甚至 P_bad 低于 `0_2`。这说明 10 个坏形态直接加总没有形成有效排序。

3. 当前坏形态更像“分歧状态描述”，不是“坏路径预测器”。
   很多 family 信号本身就发生在高波动、突破、回落、放量的环境里。把这些特征放到 T+10 后看，会捕捉到大量已经进入分歧的 survivor，但这不等于后续更差。

4. 单 component 有少数候选，但不能直接上线。
   `gap_up_fade` 在两个 OOS split 都降低 P_bad，方向值得后续单独研究；但 winner retention 只有 77.36% / 73.39%，样本删除也不小。它更适合作为后续探索对象，而不是当前版本直接纳入 hard filter。

5. `failed_breakout` / `dense_upper_shadow` 太宽，不能作为独立坏形态过滤。
   两者触发率非常高且 overlap 高。作为硬过滤时删除大量样本，winner retention 损失严重。

6. baseline_1 本身存在明显可评估样本偏差。
   BadScore complete rate 低，尤其 validation 只有 11.54%。因此任何 headline 都只代表 “历史覆盖完整、T+10 生存、filter path 完整” 子样本，不能直接外推到所有 family signal。

## Insight

这次结果反而说明了一件重要事情：在 family 信号出现后等 10 天再用“坏形态”过滤，不一定能提升开仓质量。因为到 T+10 时，样本已经经历了一个 survival selection；留下来的股票里，很多高分坏形态并不代表马上转坏，而可能只是强趋势或强分歧中自然出现的噪音。

从交易含义看，当前 BadScore 最大的问题不是“太松”或“太严”，而是方向不对。它把多个常见顶部/分歧形态相加，但这些形态在 family 信号后的 survivor 中并不稀有，也不独立。分数越高只说明这只股票过去 20 根 bar 更热、更抖、更有冲高回落，不稳定地等同于未来 bad path。

如果继续做这个方向，建议不要沿用 `BadScore >= 5` 的硬阈值。更合理的后续方向是：

- 把 `gap_up_fade` 单独拆出来做更严格定义，重点看 winner retention 与可交易样本量。
- 将 bad-shape 从 hard filter 改成 position sizing / risk budget 信号，而不是直接 drop。
- 把 component 去重，避免 `failed_breakout`、`dense_upper_shadow`、`large_bearish_engulf` 这类高度重叠信号重复加分。
- 重新评估是否应该在 T0 附近做 entry-quality 过滤，而不是等 T+10 后再做新开仓判断。

当前版本的可执行结论：不使用 R03e BadScore V1 作为 family 信号开仓过滤器。
