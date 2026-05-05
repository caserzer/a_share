# Explore9 P0.6 可执行入场触发探索报告

本报告是基于已生成的 P0.6 结构化实验结果重新整理的诊断版。未重新运行实验，未修改代码，未把 observed reference、same-close proxy、post-entry audit 或历史交易结果用于主榜选择。

## 1. 最终结论

- `recommendation = continue_p0_6_entry_discovery`。
- 当前不应进入 Explore10 backtest，也不应把任何 P0.6 trigger 升级为可执行主入场规则。
- 25 个 entry trigger variant 中，P1 candidate 数量为 `0`。
- 最关键的失败点不是执行价假设，而是结构性有效性不足：`instrument-year lift >= 1` 的 trigger 为 `0` 个，`missed winner <= 50%` 的 trigger 为 `0` 个，`convertible direct lift >= 1` 的 trigger 为 `0` 个。
- 当前证据更像是 launch 之后的持有确认、加仓观察或失败过滤线索，而不是独立的 launch-after-confirmation entry trigger。

我的诊断：

1. P0.6 的 entry trigger 没有证明“等确认以后再买”优于“同一 launch 直接买”。部分 trigger 看起来 precision 较高，但要么样本太少，要么只是 matched-delay 上好看，不能打赢 direct / convertible baseline。
2. 真正能覆盖大 winner 的信号很少。很多 trigger 的 winner miss rate 在 90% 以上，说明它们把大部分应该关注的 winner 排除在外。
3. 3 日 EMA/成交量确认是当前最像“可保留观察”的方向，但它仍然低于 direct baseline，并且 instrument-year lift 明显不足。
4. pullback / higher-low 类信号的确认成本偏高，missed gain 和 stop risk 都在上升，更像后验好看的持有/加仓条件，不像稳定首入场。

## 2. 实验规模与约束

| 项目 | 数值 | 诊断 |
| --- | ---: | --- |
| launch event panel | 148,075 行 | P0.6A observation pool 样本足够，不是空样本问题 |
| direct launch baseline | 148,060 行 | direct baseline 可用于对照 |
| entry event panel | 67,668 行 | entry 候选足够大，但主榜 dedup 后显著收缩 |
| entry leaderboard | 25 个 trigger | 覆盖了 requirement 要求的主要家族 |
| launch family | 10 个 | 满足至少 5 个 launch family 的要求 |
| entry trigger variant | 25 个 | 满足至少 20 个 trigger variant 的要求 |
| 主榜 P1 candidate | 0 个 | 没有可推进的正式入场假设 |
| `matched_delay_n_jobs` | 24 | 已按机器 24 cores 配置 |

主榜纪律：

- 主榜只允许 `primary_pre_20_launch_pool` 与 `primary_pre_30_launch_pool`。
- 主榜执行假设为 `entry_signal_date` 收盘后产生信号，下一交易日 `next_open` 执行。
- `same_close_proxy = False`。
- entry label 从 entry price reference 重新计算。
- post-entry invalidation audit、false-positive audit 和 observed reference 都不参与选择。

## 3. Launch Pool 本身的含义

| launch pool | episode | 20%/60d | 50%/120d | 100%/240d | 50% 天数中位 | top1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| late_acceleration_hold_only_pool | 738 | 41.1% | 21.4% | 12.0% | 85 | 1.4% |
| sparse_strong_day_diagnostic_pool | 2,011 | 38.7% | 16.4% | 9.2% | 97 | 0.8% |
| lifecycle_gate_rejected_or_hold_only | 1,225 | 35.4% | 16.2% | 9.3% | 91 | 1.1% |
| post_20_30_hold_only_pool | 1,833 | 32.8% | 14.0% | 8.4% | 106 | 1.0% |
| primary_pre_30_launch_pool | 1,829 | 30.5% | 13.4% | 7.2% | 109 | 1.0% |
| primary_pre_20_launch_pool | 4,210 | 30.1% | 12.1% | 6.0% | 112 | 0.7% |

诊断：

- 最强的 launch pool 反而是 `late_acceleration_hold_only_pool`，但它按 requirement 不能进入 primary entry leaderboard。这说明后段加速确实包含 winner 信息，但它不是“早期可执行首入场”。
- primary pool 的 50%/120d 命中率只有 12.1% 到 13.4%，100%/240d 只有 6.0% 到 7.2%。这不是很强的原始入场底座。
- lifecycle gate 没有污染 primary pool，说明 P0.6 的实验边界是干净的。失败不是因为 post-20/post-30 被错误混入主榜，而是因为主榜 trigger 自身没有提供足够 lift。

## 4. 主榜 Entry Trigger 结果

按综合 score 排序的前 15 个 trigger：

| trigger | n | precision | lift direct | lift convertible | lift delay | iy lift | upside | missed | stop | miss winner | score | 解释 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| hold_3d_close_above_ema20 | 1,352 | 21.7% | 0.88 | 0.77 | 1.11 | 0.45 | 0.91 | 1.9% | 2.6% | 91.9% | 10.99 | 保守确认/加仓观察 |
| hold_5d_close_ge_launch_close | 8 | 37.5% | 1.52 | 0.50 | 1.41 | 0.54 | 1.10 | 1.3% | 8.9% | 99.9% | 9.84 | 样本太少 |
| hold_3d_close_ge_launch_close | 64 | 32.8% | 1.33 | 0.81 | 1.17 | 0.48 | 1.93 | 1.6% | 9.9% | 99.4% | 7.29 | 样本不足且漏 winner |
| volume_hold_3d | 834 | 22.3% | 0.90 | 0.76 | 1.18 | 0.40 | 0.90 | 2.0% | 6.7% | 94.7% | 6.78 | 保守确认/加仓观察 |
| higher_low_reclaim_ema20 | 317 | 21.5% | 0.87 | 0.63 | 1.59 | 0.34 | 0.90 | 4.9% | 7.2% | 98.1% | 6.74 | 结构太晚 |
| hold_5d_close_above_median20 | 317 | 21.8% | 0.88 | 0.70 | 0.76 | 0.35 | 0.89 | 2.0% | 3.7% | 98.4% | 4.82 | 延迟过滤，不是结构入场 |
| pullback_3_8_reclaim_ema20 | 73 | 23.3% | 0.94 | 0.41 | 2.46 | 0.34 | 1.03 | 8.1% | 12.7% | 99.3% | 3.73 | 样本少且 stop risk 高 |
| volume_hold_5d | 230 | 22.6% | 0.92 | 0.66 | 0.84 | 0.35 | 1.00 | 2.3% | 6.8% | 98.6% | 2.95 | 延迟过滤，不是结构入场 |
| pullback_3_8_contraction_upper_close | 109 | 23.9% | 0.97 | 0.45 | 1.18 | 0.36 | 1.80 | 6.8% | 11.7% | 98.8% | 2.31 | 局部 upside，但覆盖差 |
| hold_10d_close_ge_launch_close | 137 | 21.2% | 0.86 | 0.66 | 1.01 | 0.31 | 0.77 | 2.4% | 7.8% | 99.3% | 2.29 | 确认过慢 |
| volume_second_money_rank_jump | 97 | 20.6% | 0.84 | 0.54 | 0.75 | 0.30 | 1.03 | 5.2% | 8.7% | 99.4% | 1.68 | 样本不足 |
| pullback_5_12_low_above_launch_low | 6 | 33.3% | 1.35 | 0.40 | 1.81 | 0.48 | 1.47 | 9.4% | 19.3% | 99.9% | 0.73 | 样本太少且风险过高 |
| higher_low_reaccel_rank | 348 | 16.7% | 0.68 | 0.26 | 1.00 | 0.26 | 1.30 | 10.7% | 13.2% | 95.5% | -0.19 | 晚确认 |
| higher_low_money_quality | 147 | 15.6% | 0.63 | 0.29 | 0.68 | 0.24 | 1.03 | 10.0% | 11.5% | 98.9% | -0.63 | 晚确认 |
| hold_20d_close_ge_launch_close | 32 | 25.0% | 1.01 | 0.53 | 0.99 | 0.36 | 0.55 | 4.3% | 10.9% | 99.8% | -1.51 | 样本不足且太晚 |

只看样本数 `n >= 100` 的 trigger，precision 最高的是 `pullback_3_8_contraction_upper_close`，但也只有 23.9%，并且 `lift direct = 0.97`、`lift convertible = 0.45`、`iy lift = 0.36`。这说明它不是强首入场，只是一个相对收缩后的局部观察点。

## 5. 为什么没有 P1 Candidate

| 诊断切片 | 触发数 | 代表 trigger | n | precision | direct lift | iy lift | miss winner | score |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 样本 >= 100 且 score 最高 | 9 | hold_3d_close_above_ema20 | 1,352 | 21.7% | 0.88 | 0.45 | 91.9% | 10.99 |
| direct lift >= 1 | 4 | hold_5d_close_ge_launch_close | 8 | 37.5% | 1.52 | 0.54 | 99.9% | 9.84 |
| matched-delay lift >= 1 | 10 | hold_3d_close_above_ema20 | 1,352 | 21.7% | 0.88 | 0.45 | 91.9% | 10.99 |
| winner upside lift >= 1 | 8 | hold_5d_close_ge_launch_close | 8 | 37.5% | 1.52 | 0.54 | 99.9% | 9.84 |
| instrument-year lift >= 1 | 0 | - | 0 | NA | NA | NA | NA | NA |
| missed winner <= 50% | 0 | - | 0 | NA | NA | NA | NA | NA |
| stop risk <= 12% | 12 | hold_3d_close_above_ema20 | 1,352 | 21.7% | 0.88 | 0.45 | 91.9% | 10.99 |

最关键的三条：

- 25 个 trigger 全部低于 convertible direct baseline。这意味着 trigger 不是在同一可触发 launch 集合里增加信息，而是把本来可直接入场的 launch 做了低效筛选。
- 25 个 trigger 的 instrument-year lift 全部小于 1。即使单笔 precision 看起来有点提升，也没有转化成跨股票年份的稳定性。
- 25 个 trigger 的 missed-winner rate 全部超过 50%，实际多数超过 90%。作为“首入场规则”，这会系统性漏掉 winner。

失败原因计数：

| failure reason | trigger count |
| --- | ---: |
| entry_lift_vs_convertible_direct_too_low | 25 |
| instrument_year_lift_vs_all_launch_direct_too_low | 25 |
| missed_winner_due_to_no_trigger_too_high | 25 |
| entry_lift_vs_all_launch_direct_too_low | 22 |
| drawdown_reduction_vs_direct_too_low | 20 |
| winner_upside_lift_vs_all_launch_direct_too_low | 17 |
| insufficient_entry_event_count | 16 |
| entry_lift_vs_matched_delay_too_low | 15 |
| instrument_year_lift_vs_matched_delay_too_low | 15 |
| positive_unique_instrument_year_count_too_low | 14 |
| median_entry_to_stop_risk_too_high | 13 |
| insufficient_distinct_year_count | 9 |
| top1_instrument_contribution_too_high | 9 |
| median_missed_gain_too_high | 9 |

诊断：这不是一个单 gate 卡得太严的问题。失败同时发生在 direct lift、convertible lift、instrument-year、winner coverage 和 drawdown reduction 上。放松一个阈值不能让它变成可执行入场规则。

## 6. Dedup 后的真实有效样本

| entry family | raw | first valid | primary counted | first rate | primary rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| price_hold_after_launch | 49,464 | 2,812 | 1,910 | 5.7% | 3.9% |
| volume_confirmation_entry | 6,483 | 1,885 | 1,172 | 29.1% | 18.1% |
| higher_low_reacceleration_entry | 3,863 | 1,330 | 812 | 34.4% | 21.0% |
| pullback_hold_entry | 3,180 | 605 | 188 | 19.0% | 5.9% |
| sparse_strong_day_followthrough_entry | 4,678 | 1,097 | 0 | 23.5% | 0.0% |

诊断：

- `price_hold_after_launch` raw 行很多，但 primary counted rate 只有 3.9%，说明大量信号只是重复确认，不是独立 episode 入场。
- `sparse_strong_day_followthrough_entry` primary counted 为 0，是因为它被设计为 diagnostic / secondary，不应解读为主入场失败或成功。
- `higher_low` 和 `volume` 的 primary counted rate 较高，但 leaderboard 中 lift 仍然不够，说明不是 dedup 把好信号消掉了，而是这些信号本身的可迁移性不足。

## 7. 执行可行性与风险

| trigger | raw n | next-open gap | missed vs launch | stop risk | wide stop | limit-like open |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hold_3d_close_above_ema20 | 6,989 | -0.0% | 0.8% | 3.7% | 10.2% | 0.4% |
| hold_3d_close_ge_launch_close | 4,567 | -0.0% | 2.4% | 7.7% | 25.1% | 0.6% |
| pullback_3_8_contraction_upper_close | 1,043 | -0.1% | 4.0% | 9.1% | 38.2% | 1.0% |
| volume_hold_3d | 2,745 | -0.1% | 2.7% | 9.9% | 35.5% | 0.7% |
| volume_hold_5d | 2,632 | -0.1% | 3.3% | 10.7% | 43.5% | 0.2% |
| higher_low_reclaim_ema20 | 2,281 | -0.0% | 8.8% | 11.8% | 48.8% | 0.5% |
| higher_low_money_quality | 332 | -0.0% | 10.0% | 11.9% | 49.7% | 0.6% |
| higher_low_reaccel_rank | 1,250 | -0.1% | 13.2% | 16.1% | 69.3% | 0.6% |

诊断：

- next-open gap 很小，说明 P0.6 的执行价假设本身不是主要问题。
- 3 日 EMA hold 的 stop risk 和 missed gain 最低，但它打不赢 direct baseline。
- higher-low / pullback 类信号的 missed gain 和 stop risk 明显变大。它们更像“走势已经走出来之后再确认”，不适合作为首入场。

## 8. Missed Winner 是核心缺陷

| trigger | winner no trigger | miss winner | winner missed by wait | coverage after entry |
| --- | ---: | ---: | ---: | ---: |
| hold_3d_close_above_ema20 | 2,270 | 91.9% | 13.5% | 22.9% |
| volume_hold_3d | 2,340 | 94.7% | 16.9% | 14.7% |
| higher_low_reaccel_rank | 2,359 | 95.5% | 45.9% | 8.7% |
| higher_low_reclaim_ema20 | 2,422 | 98.1% | 31.2% | 4.6% |
| volume_hold_5d | 2,436 | 98.6% | 14.7% | 4.1% |
| pullback_3_8_contraction_upper_close | 2,440 | 98.8% | 30.0% | 2.9% |
| higher_low_money_quality | 2,442 | 98.9% | 42.9% | 2.3% |
| hold_3d_close_ge_launch_close | 2,455 | 99.4% | 6.7% | 1.9% |

诊断：

- `hold_3d_close_above_ema20` 是目前最温和的确认条件，但仍漏掉 91.9% 的 launch winner。
- 更严格的 price hold / pullback / higher-low 条件会把 miss winner 推到 98% 到 99% 以上。
- 因此 P0.6 的当前 trigger 不能被用作“等待确认后才允许入场”的硬条件。它们最多只能作为仓位管理、加仓观察或失败过滤的一部分。

## 9. Failure / Invalidation 审计

| trigger | raw n | pre-filter hit | post-audit hit | failure rate | nonwinner dd |
| --- | ---: | ---: | ---: | ---: | ---: |
| higher_low_money_quality | 332 | 23.8% | 28.9% | 35.5% | -9.8% |
| hold_3d_close_above_ema20 | 6,989 | 52.1% | 64.3% | 37.9% | -10.4% |
| hold_3d_close_ge_launch_close | 4,567 | 23.5% | 44.9% | 38.1% | -10.4% |
| pullback_3_8_contraction_upper_close | 1,043 | 24.4% | 43.1% | 40.6% | -11.3% |
| volume_hold_5d | 2,632 | 19.0% | 34.6% | 40.6% | -11.3% |
| higher_low_reclaim_ema20 | 2,281 | 11.7% | 33.5% | 41.2% | -11.2% |
| volume_hold_3d | 2,745 | 16.2% | 38.0% | 42.3% | -11.5% |
| higher_low_reaccel_rank | 1,250 | 8.6% | 30.3% | 44.2% | -12.7% |

诊断：

- failure rate 大多在 38% 到 44% 区间，说明这些 trigger 不只是“覆盖少但质量高”。
- post-entry invalidation hit rate 较高，尤其 `hold_3d_close_above_ema20` 达到 64.3%。这支持一个方向：失败过滤可能有价值，但不能倒推出 entry trigger 有效。
- nonwinner drawdown 多在 -10% 到 -13%，没有看到确认入场显著改善 drawdown 的证据。

## 10. 年度稳定性

| trigger | years | n total | min y n | max y n | mean precision | min precision | max precision | zero years |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hold_3d_close_above_ema20 | 8 | 1,352 | 19 | 267 | 26.3% | 8.1% | 42.9% | 0 |
| hold_5d_close_ge_launch_close | 5 | 8 | 1 | 3 | 23.3% | 0.0% | 66.7% | 3 |
| hold_3d_close_ge_launch_close | 7 | 64 | 1 | 30 | 31.6% | 0.0% | 100.0% | 1 |
| volume_hold_3d | 8 | 834 | 11 | 196 | 25.6% | 8.6% | 37.2% | 0 |
| higher_low_reclaim_ema20 | 7 | 317 | 20 | 67 | 21.8% | 5.0% | 45.0% | 0 |
| hold_5d_close_above_median20 | 8 | 317 | 2 | 60 | 25.4% | 9.4% | 50.0% | 0 |
| pullback_3_8_reclaim_ema20 | 7 | 73 | 5 | 19 | 21.6% | 0.0% | 40.0% | 1 |
| volume_hold_5d | 8 | 230 | 1 | 47 | 20.8% | 0.0% | 38.5% | 1 |
| pullback_3_8_contraction_upper_close | 7 | 109 | 5 | 31 | 30.1% | 5.6% | 80.0% | 0 |
| hold_10d_close_ge_launch_close | 7 | 137 | 10 | 30 | 22.9% | 0.0% | 54.5% | 1 |
| volume_second_money_rank_jump | 7 | 97 | 10 | 19 | 22.1% | 0.0% | 50.0% | 1 |
| pullback_5_12_low_above_launch_low | 4 | 6 | 1 | 2 | 37.5% | 0.0% | 100.0% | 2 |

诊断：

- 年度 precision 波动很大。`hold_3d_close_above_ema20` 的 min precision 只有 8.1%，虽然覆盖 8 年且无零命中年份，但整体 direct lift 仍小于 1。
- 2020、2017 这类强趋势年份显著抬高部分 trigger 的均值；2018、2023 普遍走弱。
- 小样本高 precision 的 trigger 不具备年度稳定性，例如 `hold_5d_close_ge_launch_close` 只有 8 条主榜样本，5 个年份里有 3 个 zero-success years。

## 11. 行业和 Instrument-Year 诊断

代表 trigger 的最大行业暴露：

| trigger | top industry | n | precision | 50%/120d | dd before gain |
| --- | --- | ---: | ---: | ---: | ---: |
| hold_3d_close_above_ema20 | 银行 | 219 | 13.7% | 1.8% | -8.2% |
| volume_hold_3d | 非银金融 | 117 | 12.0% | 8.5% | -16.4% |
| higher_low_reclaim_ema20 | 银行 | 57 | 10.5% | 5.3% | -10.5% |
| hold_5d_close_above_median20 | 银行 | 50 | 14.0% | 4.0% | -7.9% |
| volume_hold_5d | 银行 | 33 | 15.2% | 3.0% | -7.4% |
| pullback_3_8_contraction_upper_close | 电子 | 13 | 30.8% | 0.0% | -14.9% |

诊断：

- 最大行业并没有贡献出特别强的 50%/120d 命中。比如 `hold_3d_close_above_ema20` 最大行业是银行，50%/120d 只有 1.8%。
- 行业层面没有看到一个清晰、可推广的 “entry trigger × industry” 组合。局部行业高 precision 更像样本偶然或趋势年份驱动。
- instrument-year lift 全部低于 1 是硬伤。即使个别 trigger 在单笔 precision 或 upside 上有亮点，也没有转化为跨股票年份的稳定 advantage。

## 12. 对各类 Trigger 的判断

### 12.1 3 日 EMA / 3 日 Volume Hold

可保留为观察方向，但不能作为主入场：

- `hold_3d_close_above_ema20` 样本最多，stop risk 最低，missed gain 也低。
- 但它的 direct lift 只有 0.88，convertible lift 只有 0.77，instrument-year lift 只有 0.45。
- 这说明它比较像“买入后仍然没有明显坏掉”的 continuation check，而不是能提升首入场质量的 trigger。

### 12.2 Close >= Launch Close 的严格 price hold

不适合作为主入场：

- `hold_3d_close_ge_launch_close` precision 有 32.8%，但只有 64 条主榜样本，miss winner 达到 99.4%。
- `hold_5d_close_ge_launch_close` precision 37.5%，但只有 8 条样本。
- 它们筛得太狠，容易把真正的大 winner 排除掉。

### 12.3 Pullback Reclaim / Pullback Hold

只适合作为二级观察，不适合硬入场：

- `pullback_3_8_contraction_upper_close` 是样本 >=100 中 precision 最高的 trigger，但 direct lift 只有 0.97，convertible lift 只有 0.45。
- missed gain 6.8%，stop risk 11.7%，wide stop 38.2%，说明等待回踩确认的成本不低。
- 该方向可能帮助识别“未失败的持有状态”，但不能证明“等回踩再入场”更优。

### 12.4 Higher-Low Re-acceleration

当前证据偏负面：

- `higher_low_reaccel_rank` precision 16.7%，direct lift 0.68，stop risk 13.2%，wide stop 69.3%。
- `higher_low_money_quality` precision 15.6%，direct lift 0.63。
- 这类信号太晚，更多是在趋势已经展开后追认结构。

### 12.5 Sparse Strong-Day Follow-Through

保持 diagnostic 身份：

- sparse strong-day 相关 family 在 primary counted 中为 0，这是符合实验设计的。
- 它们不能拿来证明主入场，但可以继续用于观察强趋势生命周期、后续持有和加仓条件。

## 13. 我对 P0.6 结果的整体解释

P0.6 的主要价值不是发现了入场 trigger，而是把一个容易误判的方向排除了：

- 如果只看单笔 precision，会误以为部分 strict hold / pullback trigger 有用。
- 加入 direct baseline 后，大多数优势消失。
- 加入 convertible direct baseline 后，25 个 trigger 全部失败。
- 加入 instrument-year 后，25 个 trigger 全部失败。
- 加入 missed winner 后，25 个 trigger 全部失败。

所以当前最合理的解释是：

1. Launch event 本身包含部分 winner 信息。
2. 等待确认会牺牲覆盖率，并且没有稳定提升 entry quality。
3. 当前 confirmation / pullback / higher-low 条件更适合做持有确认、失败过滤、仓位加减，而不是首入场。
4. 若继续 P0.6，不应继续扩大类似的简单 hold/pullback 网格；更应该换问题定义，例如研究 launch pool 分层、regime 分层、或把这些 trigger 改成 exit/hold gate。

## 14. 建议

短期建议：

- 不进入 Explore10 backtest。
- 不把任何 P0.6 trigger 写成正式 entry hypothesis。
- 保留 `hold_3d_close_above_ema20`、`volume_hold_3d`、`pullback_3_8_contraction_upper_close` 作为后续 hold / add-on / failure filter 候选观察项。
- 放弃把 strict close >= launch close、20 日 hold、higher-low rank reacceleration 作为主入场方向。

如果继续 P0.6 discovery，我建议优先改研究问题，而不是继续加 trigger：

- 从“等待确认后首入场”改为“launch 后是否继续持有或是否失败退出”。
- 对 primary launch pool 先做 market regime / industry regime 分层，再看 entry 是否还需要 trigger。
- 将 sparse strong-day 和 late acceleration 明确放到 continuation / add-on 方向，不再和 early entry 混在一起比较。
- 对 winner miss rate 设置硬约束，任何 miss winner 超过 80% 的 trigger 不再进入主 entry 讨论。

## 15. Manifest 纪律

- `p0_label_panel_reused = True`
- `p0_5_feature_panel_reused = True`
- `p0_5_reports_used_for_schema_or_family_reference_only = True`
- `p0_5_ranked_results_used_for_selection = False`
- `historical_trade_results_used_for_labeling = False`
- `historical_trade_results_used_for_signal = False`
- `historical_trade_results_used_for_selection = False`
- `observed_reference_used_for_selection = False`
- `same_close_proxy_used_in_main_leaderboard = False`
- `post_entry_invalidation_audit_used_for_selection = False`
- `false_positive_definitions_used_for_selection = False`
- `entry_labels_rebased_to_entry_price = True`
- `p0_stock_day_label_panel_used_for_entry_label_directly = False`
- `entry_price_reference_used = next_open`
