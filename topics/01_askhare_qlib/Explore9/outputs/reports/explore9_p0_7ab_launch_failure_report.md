# Explore9 P0.7AB 启动分层与失败过滤详细报告

本报告基于当前 `Explore9/outputs/reports/p0_7_*.csv` 与 `p0_7_run_manifest.json` 更新，只解释实验数据，不引入代码或配置变更。

## 1. 总结判断

- `recommendation = continue_p0_7ab_discovery`。
- 本轮没有可直接晋级 P1 的 launch stratification：`p1_launch_stratification_candidate = 0`。
- 本轮没有可直接晋级 P1 的 failure filter：`p1_failure_filter_candidate = 0`。
- 这不是“完全没有信号”。launch 侧最高 50%/120d 命中率达到 `23.70%`，相对全 launch episode 基线 `14.07%` 有 `1.68x` lift；failure 侧 destructive/high-vol 与 gap-fade 类过滤器能更早识别一部分失败样本，并且 drawdown avoided 有正贡献。
- 但信号目前不能作为可执行规则：launch 侧被 instrument-year 稳定性、same-family lift、winner coverage 与 false positive 拦下；failure 侧被 nonwinner precision lift、winner/big-winner false reject、winner coverage loss 与 matched-delay drawdown 对照拦下。
- P0.7C hold/add-on gate 本批次仍是 deferred contract，报告不输出 P1 hold gate、P1 add-on gate、Explore10 backtest 或 frozen strategy 建议。

最重要的解释是：P0.7AB 已经把“看起来像启动”的状态拆开了，但当前公式矩阵更多是在发现高波动生命周期、失败风险和上下文，而不是找到稳定首入场触发器。下一步应继续 discovery，重点不是放宽 P1 门槛，而是重新定义更窄的 context 组合，减少 false reject 和 instrument-year 失稳。

## 2. 数据边界与纪律

| 项目 | 值 |
| --- | --- |
| phase | P0.7AB / expand_3 |
| research window | 2017-01-01 至 2024-12-31 |
| observed reference | 2025-01-01 至 2026-04-30，仅保留观察审计，不用于 selection |
| provider | `Explore7/data/qlib/cn_data_pit` |
| fallback provider | `Explore1/data/qlib/cn_data` |
| price mode | provider OHLC 已复权 |
| execution assumption | close-derived signal，next trading day open 执行 |
| same-close proxy | False |
| historical trade results used for selection/signal/labeling | False / False / False |
| P0.6 entry results used for selection | False |
| P0.6 launch event panel reused | True |

核心面板规模：

| panel | rows | 说明 |
| --- | ---: | --- |
| `p0_7_launch_episode_panel.parquet` | 4,909 | launch-source row 按 instrument 和 20 个交易日 gap 折叠后的 episode |
| `p0_7_launch_stratum_event_panel.parquet` | 38,980 | P0.7A 公式命中的 stratum event |
| `p0_7_failure_filter_opportunity_panel.parquet` | 779,600 | `38,980 x 20` 的完整 filter opportunity 分母 |
| `p0_7_failure_filter_event_panel.parquet` | 244,784 | 触发的 failure filter event 子集 |

审计结果全部通过：

| check | actual | required | pass |
| --- | ---: | --- | --- |
| launch stratum family / variant | 10 / 20 | 10 / 20 | True |
| failure filter family / variant | 10 / 20 | 10 / 20 | True |
| formula token unmapped | 0 | 0 | True |
| launch event rows without evaluated recommendation | 0 | 0 | True |
| non-signal rows missing denominator reference date | 0 | 0 | True |
| post-target filter counted as false reject | 0 | 0 | True |
| matched delay exact real reject count used | 1 | 1 | True |
| hold/add-on gate deferred | 1 | 1 | True |
| full row CSV disabled by default | 1 | 1 | True |

去重审计显示，本轮原始 formula hit 很密集：`303,392` 条 raw hit 折叠为 `38,980` 条 stratum event，移除重复 hit `264,412` 条。每个保留事件对应的 raw hit 中位数为 `3`，75 分位为 `8`，最大值为 `272`。这说明很多 episode 会在同一生命周期内反复触发相近公式，后续如果要做可执行信号，需要继续压缩同质 hit。

## 3. P0.7A Launch Stratification

### 3.1 全 launch 基线

全 launch episode 基线用于判断分层是否真正提升：

| 指标 | 全 launch episode baseline |
| --- | ---: |
| future 50% high / 120d | 14.07% |
| launch false positive primary rate | 36.38% |
| median future max drawdown / 60d | -9.93% |
| winner episode coverage | 25.69% |

P0.7A 共有 20 个 launch formula variant，其中 19 个产生 leaderboard 记录；`weak_market_industry_leader` 在当前样本内没有有效 leaderboard 记录。19 个候选全部未通过 P1。

关键 gate 覆盖情况：

| gate | 通过数 / 19 | 解释 |
| --- | ---: | --- |
| 50%/120d 高于全 launch 基线 | 10 | 约一半公式有表面 precision 提升 |
| lift vs all >= 1.10 | 8 | 只有高波动/稀疏强日/部分修复类明显高于全局 |
| lift vs same family >= 1.05 | 3 | 大多数只是 family 自身属性，不是 family 内进一步分层 |
| instrument-year lift >= 1.00 | 0 | 最大值仅 `0.822`，是 launch 侧最硬的否决项 |
| winner coverage >= 5% | 9 | 高 precision 的小样本无法覆盖足够 winner |
| false positive 不劣于 same family | 10 | 仍有 9 个 worse-than-family |
| drawdown 不显著劣于 same family | 17 | drawdown 不是 launch 侧主拦截项 |

### 3.2 按 declared role 聚合

| declared role | eval action | variants | events | episodes | avg 50%/120d | max 50%/120d | avg lift all | avg IY lift |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| risk_warning_context | failure_prone_no_trade | 2 | 920 | 920 | 23.69% | 23.70% | 1.684 | 0.786 |
| launch_observation_context | rejected_or_uncertain | 5 | 7,568 | 7,568 | 17.26% | 23.33% | 1.227 | 0.698 |
| addon_context_deferred | add_on_context_only | 2 | 2,774 | 2,774 | 17.80% | 20.27% | 1.265 | 0.693 |
| diagnostic_context | diagnostic_only | 1 | 720 | 720 | 18.89% | 18.89% | 1.342 | 0.621 |
| hold_continuation_context | hold_continuation_only | 1 | 1,470 | 1,470 | 16.39% | 16.39% | 1.165 | 0.658 |
| watchlist_observation_context | rejected_or_uncertain | 8 | 15,736 | 15,736 | 12.60% | 15.83% | 0.896 | 0.615 |

这里有一个反直觉点：`risk_warning_context` 的 50%/120d 命中率最高，但评估动作是 `failure_prone_no_trade`。这类状态不是简单的“收益差”，而是“高波动、高机会、高失败共存”的区域。它可以用于风险识别或上下文标注，不能直接转换为 entry trigger。

### 3.3 Launch Top 10

| variant | eval action | episode | 50%/120d | lift all | IY lift | winner coverage | false positive | median DD 60d | median T50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| destructive_high_vol_upper_shadow | failure_prone_no_trade | 595 | 23.70% | 1.684 | 0.822 | 2.79% | 43.36% | -12.95% | 71 |
| high_vol_break_median_warning | failure_prone_no_trade | 325 | 23.69% | 1.684 | 0.749 | 1.51% | 39.08% | -12.17% | 84.5 |
| expansion_high_vol_upper_close | rejected_or_uncertain | 420 | 23.33% | 1.658 | 0.802 | 1.98% | 46.19% | -13.11% | 76.5 |
| high_vol_controlled_drawdown | rejected_or_uncertain | 658 | 22.04% | 1.566 | 0.762 | 2.87% | 46.20% | -13.79% | 82.5 |
| late_acceleration_context | add_on_context_only | 602 | 20.27% | 1.440 | 0.656 | 2.44% | 49.34% | -14.59% | 94 |
| first_near_limit_upper_close | diagnostic_only | 720 | 18.89% | 1.342 | 0.621 | 2.71% | 43.89% | -12.41% | 92 |
| post_20_relative_strength_context | hold_continuation_only | 1,470 | 16.39% | 1.165 | 0.658 | 4.73% | 43.40% | -11.61% | 92 |
| repair_reclaim_ema20_quality | rejected_or_uncertain | 714 | 15.83% | 1.125 | 0.609 | 2.26% | 42.44% | -11.61% | 90.5 |
| strong_body_day_node | add_on_context_only | 2,172 | 15.33% | 1.090 | 0.729 | 6.52% | 38.21% | -10.46% | 103 |
| rank_jump_5d_persist_3d | rejected_or_uncertain | 1,829 | 14.87% | 1.057 | 0.662 | 5.38% | 38.55% | -10.65% | 108.5 |

解释：

- `destructive_high_vol_upper_shadow` 和 `high_vol_break_median_warning` 是最高 precision 的两类，但 winner coverage 只有 `2.79%` 和 `1.51%`，false positive 分别为 `43.36%` 和 `39.08%`。它们更像风险/波动上下文，不适合作为进入候选。
- `expansion_high_vol_upper_close` 与 `high_vol_controlled_drawdown` 的 50%/120d 也高，但 same-family baseline 已经很强，family 内新增 lift 不够，并且 false positive 明显高。
- `strong_body_day_node` 覆盖最好，winner coverage `6.52%`，但 50%/120d 只有 `15.33%`，只略高于全局基线，IY lift 仍低。
- `post_20_relative_strength_context` 与 `late_acceleration_context` 按设计被归为 hold/add-on context，本轮只保留为 audit，不输出可执行建议。

### 3.4 Launch Rejection 原因

| rejection reason | count |
| --- | ---: |
| instrument_year_lift_too_low | 19 |
| lift_vs_same_family_baseline_too_low | 16 |
| lift_vs_all_launch_baseline_too_low | 11 |
| winner_episode_coverage_too_low | 10 |
| false_positive_rate_worse_than_same_family | 9 |
| drawdown_worse_than_same_family | 2 |

Launch 侧的主问题不是某一个公式太弱，而是所有公式都没有跨 instrument-year 的稳定 lift。也就是说，当前分层更像是在解释某些年份/个股/行业下的状态，而不是形成稳健的跨样本启动规则。

### 3.5 生命周期审计

| later lifecycle state | declared lifecycle stage | stratum events | episodes |
| --- | --- | ---: | ---: |
| False | pre_20_launch | 2,354 | 1,589 |
| False | watchlist | 10,705 | 4,690 |
| False | sparse_strong_day_node | 1,583 | 1,404 |
| False | post_20_30_continuation | 361 | 361 |
| False | late_acceleration | 97 | 97 |
| False | risk_warning | 126 | 125 |
| True | pre_20_launch | 7,869 | 3,001 |
| True | watchlist | 9,903 | 3,355 |
| True | sparse_strong_day_node | 2,379 | 1,881 |
| True | post_20_30_continuation | 1,685 | 1,685 |
| True | late_acceleration | 701 | 701 |
| True | risk_warning | 1,217 | 929 |

later lifecycle hit 没有改写 first event，而是生成新的 stratum event。这个纪律是正确的：它避免把后验生命周期状态回填到启动日，从而污染 launch stratification。

## 4. P0.7B Failure Filter

### 4.1 Filter Opportunity 与 Denominator

所有 20 个 filter variant 都以 `38,980` 个 launch stratum event 为 opportunity 分母，因此总 opportunity 为 `779,600`。non-triggered rows 也保留了 reference date，缺失为 `0`。

| filter variant | opportunity | signal rate | events | median delay | pending false reject | median DD avoided | before 12% DD | before 20% DD | post-target signals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| industry_breadth_evaporation_10d | 38,980 | 71.42% | 27,839 | 3 | 64.08% | 9.74% | 45.33% | 18.52% | 10 |
| no_followthrough_5d | 38,980 | 59.96% | 23,371 | 5 | 45.47% | 9.37% | 43.87% | 18.23% | 0 |
| industry_breadth_evaporation_5d | 38,980 | 52.52% | 20,472 | 2 | 48.21% | 9.74% | 46.11% | 18.93% | 0 |
| no_followthrough_10d | 38,980 | 51.09% | 19,915 | 10 | 33.00% | 8.61% | 37.23% | 18.12% | 0 |
| money_distribution_5d | 38,980 | 46.27% | 18,036 | 2 | 45.34% | 10.42% | 45.25% | 17.99% | 8 |
| upper_shadow_money_distribution_10d | 38,980 | 46.10% | 17,970 | 3 | 55.14% | 10.54% | 36.25% | 13.83% | 31 |
| break_launch_low_5d | 38,980 | 43.87% | 17,102 | 2 | 38.74% | 9.94% | 50.81% | 21.93% | 0 |
| money_distribution_10d | 38,980 | 40.36% | 15,732 | 3 | 48.09% | 10.34% | 37.42% | 14.22% | 22 |
| break_ema20_after_launch_5d | 38,980 | 39.41% | 15,363 | 2 | 29.44% | 9.62% | 49.61% | 20.79% | 0 |
| break_median20_after_launch_5d | 38,980 | 36.97% | 14,411 | 2 | 31.70% | 9.10% | 47.82% | 20.07% | 0 |
| break_launch_low_3d | 38,980 | 34.09% | 13,289 | 2 | 32.24% | 10.05% | 50.33% | 21.60% | 0 |
| rank_evaporation_10d | 38,980 | 24.49% | 9,546 | 5 | 19.15% | 10.03% | 50.34% | 27.01% | 0 |
| upper_shadow_volume_failure_5d | 38,980 | 21.88% | 8,527 | 2 | 26.34% | 10.54% | 38.21% | 13.94% | 0 |
| wide_stop_risk_no_new_entry_10d | 38,980 | 17.08% | 6,656 | 4 | 34.87% | 14.71% | 28.29% | 10.10% | 0 |
| rank_evaporation_5d | 38,980 | 12.78% | 4,980 | 3 | 10.96% | 10.00% | 53.05% | 25.98% | 0 |
| wide_stop_risk_no_add_5d | 38,980 | 10.09% | 3,932 | 3 | 19.85% | 14.99% | 32.83% | 12.64% | 0 |
| destructive_high_vol_5d | 38,980 | 8.60% | 3,352 | 3 | 10.64% | 11.81% | 63.28% | 33.59% | 0 |
| destructive_high_vol_3d | 38,980 | 5.91% | 2,302 | 2 | 7.50% | 12.24% | 64.29% | 33.19% | 0 |
| gap_fade_after_launch_5d | 38,980 | 3.67% | 1,430 | 2 | 4.65% | 12.57% | 50.84% | 23.71% | 5 |
| gap_fade_break_prior_close_5d | 38,980 | 1.43% | 559 | 2 | 1.70% | 14.51% | 55.10% | 26.83% | 4 |

这个表给出两个方向：

- 高频 filter，比如 industry breadth evaporation、no followthrough、money distribution，会覆盖大量机会，但 pending false reject 过高，不能直接作为拒绝规则。
- 低频 filter，比如 destructive high vol、gap fade prior close，false reject 更低且 drawdown avoided 更好，但 recall 太低，不能独立保护组合。

### 4.2 Failure Filter Gate 覆盖

failure leaderboard 共 `400` 行：20 个 filter variant 乘以 19 个 exact launch scope，再加 `all_launch_strata` 全局 audit scope。没有一行通过全部 P1 gate。

| gate | pass rows / 400 |
| --- | ---: |
| event_count >= 200 | 251 |
| nonwinner recall >= 20% | 253 |
| failure recall >= 20% | 255 |
| nonwinner precision lift >= 1.05 | 69 |
| failure precision lift >= 1.05 | 282 |
| winner false reject <= 25% | 171 |
| big winner false reject <= 15% | 105 |
| pending winner coverage loss <= 30% | 207 |
| total winner coverage loss <= 20% | 141 |
| median drawdown avoided vs matched delay >= 0 | 192 |
| before 12% drawdown rate >= 50% | 398 |
| before 20% drawdown rate >= 50% | 399 |
| instrument-year filter effect lift >= 1.00 | 205 |
| all gates pass | 0 |

真正卡住 failure filter 的不是“是否能在大跌前发出信号”。大多数 row 都满足 before-drawdown timing。核心问题是过滤动作不够选择性：nonwinner precision lift 只有 69/400 通过，并且 big winner false reject 与 winner coverage loss 太高。

### 4.3 all_launch_strata 全局审计

全局 scope 不是主 leaderboard 选择依据，但能帮助看 filter 的整体性格：

| filter variant | events | conversion | nonwinner recall | failure recall | failure precision | failure lift | winner false reject | DD vs delay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| destructive_high_vol_3d | 1,353 | 4.64% | 4.32% | 7.06% | 55.43% | 1.524 | 6.57% | 3.84% |
| destructive_high_vol_5d | 1,980 | 6.78% | 6.36% | 10.18% | 54.60% | 1.501 | 9.42% | 3.31% |
| rank_evaporation_10d | 6,661 | 22.82% | 23.68% | 33.16% | 52.86% | 1.453 | 17.97% | -0.23% |
| rank_evaporation_5d | 3,346 | 11.46% | 11.72% | 16.33% | 51.82% | 1.425 | 9.94% | 0.09% |
| no_followthrough_10d | 15,022 | 51.47% | 54.90% | 65.36% | 46.20% | 1.270 | 31.18% | -1.44% |
| gap_fade_break_prior_close_5d | 307 | 1.05% | 0.95% | 1.33% | 45.93% | 1.263 | 1.66% | 5.47% |
| break_launch_low_5d | 12,516 | 42.88% | 43.67% | 53.84% | 45.68% | 1.256 | 38.18% | -0.16% |
| gap_fade_after_launch_5d | 906 | 3.10% | 2.85% | 3.84% | 45.03% | 1.238 | 4.61% | 3.73% |

全局视角下最值得继续看的不是高频 filter，而是两类低频高选择性信号：

- `destructive_high_vol_3d/5d`：failure precision lift 最高，false reject 相对低，drawdown vs matched delay 为正，但 recall 明显不足。
- `gap_fade_after_launch_5d` / `gap_fade_break_prior_close_5d`：false reject 很低，drawdown vs delay 为正，但 signal 太少，不能覆盖主要失败。

`rank_evaporation_5d/10d` 的 failure lift 也不错，但 matched-delay drawdown 对照不稳定，尤其 `10d` 为负，说明它可能只是晚识别已经恶化的状态，而不是有效提前过滤。

### 4.4 Exact Scope Top Failure Lift

| filter variant | launch scope | events | conversion | nonwinner recall | failure recall | failure lift | winner false reject | DD vs delay | distinct instruments |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| destructive_high_vol_5d | repair_quality_watchlist:repair_higher_low_reclaim | 60 | 2.04% | 1.91% | 4.72% | 2.319 | 3.21% | 7.74% | 52 |
| destructive_high_vol_3d | repair_quality_watchlist:repair_higher_low_reclaim | 44 | 1.49% | 1.43% | 3.42% | 2.292 | 2.14% | 7.66% | 39 |
| destructive_high_vol_3d | money_price_keep_context:money_price_upper_keep | 63 | 1.98% | 1.93% | 4.32% | 2.182 | 2.38% | 6.44% | 54 |
| destructive_high_vol_3d | money_price_keep_context:money_expansion_no_distribution | 90 | 2.75% | 2.58% | 5.33% | 1.937 | 3.98% | 8.32% | 67 |
| gap_fade_break_prior_close_5d | relative_strength_persistence:industry_relative_strength_persistence | 19 | 0.92% | 0.89% | 1.76% | 1.925 | 1.06% | 4.75% | 18 |
| destructive_high_vol_5d | money_price_keep_context:money_price_upper_keep | 102 | 3.21% | 3.00% | 6.05% | 1.887 | 4.76% | 4.41% | 85 |
| destructive_high_vol_5d | prelaunch_path_quality:controlled_repair_from_deep_drawdown | 16 | 3.94% | 3.60% | 7.38% | 1.873 | 6.67% | 13.01% | 15 |
| rank_evaporation_5d | sparse_strong_day_lifecycle_node:first_near_limit_upper_close | 58 | 8.06% | 9.25% | 14.87% | 1.846 | 3.01% | -1.50% | 55 |
| destructive_high_vol_3d | prelaunch_path_quality:controlled_repair_from_deep_drawdown | 14 | 3.45% | 3.05% | 6.04% | 1.752 | 6.67% | 11.99% | 13 |
| destructive_high_vol_5d | money_price_keep_context:money_expansion_no_distribution | 128 | 3.91% | 3.52% | 6.76% | 1.726 | 6.72% | 5.14% | 92 |

这些 exact-scope 结果解释了为什么不能直接晋级：

- failure lift 很高的 row，事件数大多远低于 `min_failure_filter_event_count = 200`，recall 也远低于 `20%`。
- `repair_higher_low_reclaim + destructive_high_vol` 是最值得继续研究的失败上下文，但当前只是在少数失败上很准，不是完整的拒绝规则。
- `rank_evaporation_5d + first_near_limit_upper_close` 的 recall 相对更高，但 matched-delay drawdown 为负，说明过滤日的时点优势不足。

### 4.5 Failure Rejection 原因

| rejection reason | count |
| --- | ---: |
| nonwinner_precision_lift_too_low | 331 |
| big_winner_false_reject_rate_too_high | 295 |
| winner_coverage_loss_total_too_high | 259 |
| winner_false_reject_rate_too_high | 229 |
| drawdown_avoided_vs_matched_delay_too_low | 208 |
| instrument_year_filter_effect_lift_too_low | 195 |
| winner_coverage_loss_pending_too_high | 193 |
| insufficient_failure_filter_event_count | 149 |
| nonwinner_reject_recall_too_low | 147 |
| failure_reject_recall_too_low | 145 |
| failure_precision_lift_too_low | 118 |

这组 rejection reason 的含义很明确：failure filter 现在可以解释很多失败，但作为“拒绝入场/退出 opportunity”的规则太粗。它会把太多仍可能成为 winner 的 launch event 过滤掉，导致 opportunity cost 过高。

## 5. Matched-Delay Baseline

matched-delay 运行纪律：

| setting | value |
| --- | --- |
| pseudo reject set mode | exact_real_reject_count |
| random seed | 20260505 |
| repeats | 20 |
| sample with replacement | False |
| rows with bootstrap empirical delay | 399 |
| rows disabled due no real rejects | 1 |

matched-delay 统计：

| metric | mean | median | min | max |
| --- | ---: | ---: | ---: | ---: |
| pseudo reject nonwinner precision | 84.00% | 85.27% | 72.08% | 94.00% |
| pseudo rejected nonwinner median DD avoided | 11.92% | 11.18% | 7.90% | 17.26% |
| bootstrap mean DD avoided | 11.94% | 11.24% | 7.89% | 16.69% |
| bootstrap std | 0.82% | 0.57% | 0.05% | 6.87% |

matched-delay 是本轮 failure filter 的关键对照。很多 filter 的绝对 drawdown avoided 看起来不错，但如果换成相同拒绝数量、相似延迟分布的伪拒绝，优势就消失。这解释了为什么 `drawdown_avoided_vs_matched_delay_too_low` 出现 208 次。

## 6. 市场 Regime 与行业观察

### 6.1 市场 regime

| market regime | events | mean 50%/120d | max 50%/120d |
| --- | ---: | ---: | ---: |
| market_drawdown | 13,514 | 14.80% | 21.23% |
| market_trend_on | 14,546 | 14.52% | 19.66% |
| market_choppy | 10,920 | 11.60% | 20.88% |

最高的 regime-family 组合：

| market regime | stratum family | events | 50%/120d |
| --- | --- | ---: | ---: |
| market_drawdown | high_vol_destructive_warning | 457 | 21.23% |
| market_choppy | high_vol_quality_permit | 407 | 20.88% |
| market_trend_on | high_vol_destructive_warning | 580 | 19.66% |
| market_drawdown | high_vol_quality_permit | 511 | 18.59% |
| market_trend_on | high_vol_quality_permit | 660 | 18.18% |

这里不能简单得出“drawdown 市场更好”的交易结论。更合理的解释是，高波动 launch/failure context 在 drawdown 或 choppy regime 里有更高的右尾潜力，但同时失败风险和 false positive 也更高，需要和 failure filter 联合建模。

### 6.2 行业差异

样本数不少于 100 的行业-family 组合中，最高命中率集中在电子、国防军工、计算机、有色金属：

| industry | stratum family | events | 50%/120d |
| --- | --- | ---: | ---: |
| 电子 | high_vol_destructive_warning | 180 | 28.33% |
| 国防军工 | sparse_strong_day_lifecycle_node | 110 | 25.45% |
| 电子 | high_vol_quality_permit | 227 | 25.11% |
| 国防军工 | relative_strength_persistence | 138 | 24.64% |
| 计算机 | relative_strength_persistence | 226 | 23.01% |
| 计算机 | rank_jump_persistence_watchlist | 222 | 22.07% |
| 计算机 | money_price_keep_context | 279 | 21.86% |
| 计算机 | industry_breadth_coherence | 111 | 21.62% |

低命中率集中在银行、交通运输：

| industry | stratum family | events | 50%/120d |
| --- | --- | ---: | ---: |
| 交通运输 | prelaunch_path_quality | 134 | 0.75% |
| 银行 | post_20_30_or_late_continuation_context | 158 | 1.27% |
| 银行 | money_price_keep_context | 1,053 | 1.61% |
| 银行 | sparse_strong_day_lifecycle_node | 236 | 1.69% |
| 银行 | repair_quality_watchlist | 662 | 1.81% |
| 银行 | relative_strength_persistence | 560 | 1.96% |

行业差异很强，后续可以作为 discovery 方向，但本轮不能把行业条件直接作为 P1 推荐：当前 P0.7AB 只验证 launch/failure 公式本身，行业拆解是 audit，不是 selection 入口。

## 7. 当前可保留的研究信号

可以保留为下一轮候选上下文：

- `destructive_high_vol_3d/5d`：低频、低 false reject、failure lift 与 drawdown-vs-delay 都较好。问题是 recall 太低，应研究它与特定 launch scope 的组合，而不是全局 filter。
- `gap_fade_break_prior_close_5d`：false reject 最低，drawdown avoided 高，但事件数太少。适合做“强失败确认”而不是主过滤器。
- `repair_higher_low_reclaim + destructive_high_vol`：exact-scope failure lift 最高，可能是“修复失败转破坏”的风险节点。
- `money_price_keep_context + destructive_high_vol`：failure lift 稳定出现在多个 money-price scope，值得继续拆成成交额结构、上影线、median20 break 的组合。
- `first_near_limit_upper_close + rank_evaporation`：recall 比 destructive 类好，但时点优势不足，需要更早的 rank deterioration 特征。

暂不应推进为执行规则：

- `industry_breadth_evaporation_5d/10d`：覆盖极广，signal rate 到 `52.52%/71.42%`，pending false reject 到 `48.21%/64.08%`，更像市场环境变量。
- `no_followthrough_5d/10d`：failure recall 高，但 false reject 与 coverage loss 过大。
- `break_launch_low`、`break_ema20`、`break_median20`：规则直观，但全局视角下 precision lift 不够，且 matched-delay 对照没有明显优势。
- `wide_stop_risk`：drawdown avoided 高，但 failure precision lift 很低，可能只是识别“本来就宽止损/高波动”的状态。

## 8. 下一步建议

1. 继续 P0.7AB discovery，不进入 P1。
2. Launch 侧不要放宽 P1 门槛；应先解决 instrument-year lift 全部低于 1 的问题。优先把 high-vol、repair、money-price 三类 context 和行业/market regime 做更窄的组合审计。
3. Failure 侧不要把高频 filter 作为主拒绝规则。下一轮优先研究低频高选择性 filter 的组合，例如 destructive high vol + repair/money-price context，目标是提高 recall，同时保持 false reject 低。
4. 对 `rank_evaporation` 做更早窗口版本。当前 5d/10d 能识别失败，但 matched-delay 优势弱，说明信号可能太晚。
5. 行业拆解显示科技成长链和银行/交通运输差异巨大，后续可以设计行业条件化 audit，但应保持 PIT 行业归属和 selection 纪律。
6. P0.7C hold/add-on 仍应延后。当前 hold/add-on context 的数据价值是生命周期标注，不足以输出执行建议。

本轮结论是：P0.7AB 的工程与审计链路已经可用，数据也确实揭示了若干 failure/launch context；但这些 context 还停留在 discovery 质量，不能升级为 P1 可执行策略。
