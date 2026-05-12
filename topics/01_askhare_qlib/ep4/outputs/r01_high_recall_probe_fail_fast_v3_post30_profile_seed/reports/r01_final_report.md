# EP4 R01 V3 Post30 Profile Seed 中文解释报告

- Final decision: `stop_ep4_r01_path`
- 报告类型：人工解释版中文报告，基于当前已生成 artifacts 汇总，不修改代码，不重新调参。
- 输出目录：`ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/`
- 冻结 seed：`close_near_high5_gt_0pct_and_vol_ratio10_gt_1_2_and_vol_ratio3_gt_1_2_and_rps5_gt_60`
- R01 阶段边界：不训练模型，不做加仓，不做组合 sizing，不做动态 exit 优化。

## 1. 结论

这次 V3 实验证明了一件很关键的事：post30 profile seed 确实能在事后 T+0..T+30 窗口覆盖大量大 winner，但它不能直接变成一个高质量、低密度、可执行的 R01 entry seed。

核心矛盾有四个：

1. post30 search 的覆盖是 retrospective condition coverage；R01 headline recall 是 executable entry capture。两者不是同一个指标。
2. candidate primary recall 明显高于 EP2 detector，但代价是触发密度过高。
3. 大量 post30 命中在风险距离上不可执行，主要是 `initial_risk_pct < 2%`。
4. matched-delay 对照显示候选 seed 对 1d/3d 延迟很敏感，尤其 validation 和 robustness 的 p05 tail 明显变差。

因此当前结果不能进入 R02。即使 recall-cost 表面通过，也应按 `stop_ep4_r01_path` 处理。

## 2. Post30 Provenance 与 OOS status

Post30 Provenance 来自：

`ep4/outputs/r01_big_winner_post30_indicator_search_v1/reports/post30_condition_search_v1_report.md`

该搜索报告中，同一条件在 845 个 canonical R01 primary big winner 上的 T+0..T+30 覆盖为 797 / 845，即 94.32%，eligible-day density 为 7.91%。但这只是同一股票在 reference date 之后 0 到 30 个交易日内至少一天满足日级条件。

V3 R01 使用的是更严格口径：

- capture basis: `entry_execution_date`
- primary entry window: `reference_date + 1` 到 `reference_date + 30`
- 必须形成 seed episode
- next open 必须可买
- stop 必须存在且低于 entry price
- `initial_risk_pct` 必须在 2% 到 12% 之间
- terminal path 不得跨 split 或缺观察窗口

OOS status: 当前 seed discovery scope 是 `all_splits`，`validation_oos_clean = False`。所以即使所有 hard gates 通过，也最多只能进入 OOS retest，不能直接授权 R02。

这里的 `reference_date` 是 retrospective evaluation anchor，不是当日可观察交易状态。实际可交易证据必须看 `entry_execution_date`。

## 3. Reference Windows

| split | configured_start | effective_reference_end | effective_primary_seed_end | effective_gate_entry_end | big_winner refs | unique instruments | forward_return_p50 |
|:--|:--|:--|:--|:--|--:|--:|--:|
| train | 2017-07-04 | 2021-09-15 | 2021-11-05 | 2021-11-05 | 456 | 206 | 0.5469 |
| validation | 2022-01-01 | 2023-09-14 | 2023-11-03 | 2023-11-03 | 139 | 118 | 0.5344 |
| robustness | 2024-01-01 | 2025-09-16 | 2025-11-05 | 2025-11-05 | 243 | 167 | 0.5311 |

总 reference count 为 838。有效 reference window 已经排除了无法完整观察 post-reference entry 和 probe terminal path 的尾部样本。

## 4. 为什么同一个条件仍然 missed 很多

post30 search 的问题是：“这只股票在大 winner reference date 后 0 到 30 天内，是否至少一天满足条件？”

R01 V3 的问题是：“是否能在 reference date 后 1 到 30 天内形成一个可执行 entry episode，并且这个 episode 通过 stop/risk/buyability/boundary 约束？”

这两个问题差异很大。

| split | refs | post30 signal hit T0..30 | any episode capture | headline executable capture |
|:--|--:|--:|--:|--:|
| train | 456 | 422 / 92.5% | 315 / 69.1% | 212 / 46.5% |
| validation | 139 | 131 / 94.2% | 111 / 79.9% | 66 / 47.5% |
| robustness | 243 | 230 / 94.7% | 162 / 66.7% | 97 / 39.9% |

validation 的 73 个 headline misses 可拆成：

| miss 类型 | count | 解释 |
|:--|--:|:--|
| T0..30 没有 signal hit | 8 | 条件本身没有覆盖到 |
| 有 signal hit，但没有被 episode entry 捕获 | 20 | 多数与 20-day episode compression / suppressed reentry 或 entry timestamp 不落在 primary window 有关 |
| 被 episode 捕获，但不可执行 | 45 | 全部是 risk distance 不合格，主要是 stop 太近 |

我的判断：该条件更像“大 winner 事后 profile marker”，不是一个干净的 entry trigger。它经常在上涨已经展开后、价格贴近高点或突破参考位时出现，因此作为 entry 时 stop 太近，导致 initial R 不足。

## 5. Risk / Stop / Buyability 详细解释

R01 V3 的 entry 可执行性由三部分控制。

Stop 选择：

- 使用 next-open entry price。
- 从 `seed_day_low`、`breakout_reference`、`pivot_low_10d` 三个结构参考位中选择一个低于 entry price 的 stop。
- 如果没有有效 stop，episode reject reason 为 `no_valid_stop_below_entry`。

Risk 计算：

```text
initial_risk_pct = (entry_price - initial_structural_stop) / entry_price
```

配置要求：

```text
min_initial_risk_pct = 0.02
max_initial_risk_pct = 0.12
```

Buyability：

- next open 必须有价格。
- next open 必须仍在 PIT universe。
- next open 不能被推断为 limit-up 不可买。
- 买入字段以 `is_buy_executable_next_open` 和 `blocked_buy_reason` 为准。

## 6. Risk/Stop/Buyability 数据

candidate episodes 可执行情况：

| split | passed episodes | rejected episodes |
|:--|--:|--:|
| train | 2064 | 1642 |
| validation | 1029 | 1057 |
| robustness | 971 | 1096 |

rejected episodes 的原因：

| split | risk_distance_below_min | risk_distance_above_max | no_valid_stop_below_entry |
|:--|--:|--:|--:|
| train | 1619 | 22 | 1 |
| validation | 1053 | 4 | 0 |
| robustness | 1085 | 11 | 0 |

这说明主要问题不是买不到，而是 stop 太近导致 `initial_risk_pct < 2%`。

在已经捕获 primary reference 的 episodes 中，不可执行情况如下：

| split | passed captured refs | non-exec captured refs | non-exec 主因 | non-exec risk p50 |
|:--|--:|--:|:--|--:|
| train | 212 | 106 | 104 below-min, 2 above-max | below-min p50 = 1.29% |
| validation | 66 | 45 | 45 below-min | below-min p50 = 1.10% |
| robustness | 97 | 66 | 63 below-min, 3 above-max | below-min p50 = 1.18% |

validation 中，45 个被条件捕获但不可执行的 reference 全部是 `risk_distance_below_min`。这些 episode 的 risk range 为 0.05% 到 2.00%，median 约 1.10%，低于要求的 2%。

一个典型模式是：

| instrument | entry date | reject reason | entry price | stop | initial risk |
|:--|:--|:--|--:|--:|--:|
| SZ000063 | 2022-11-01 | risk_distance_below_min | 20.96 | 20.95 | 0.05% |
| SH600893 | 2022-05-06 | risk_distance_below_min | 37.27 | 37.25 | 0.05% |
| SZ002493 | 2022-11-29 | risk_distance_below_min | 11.91 | 11.90 | 0.08% |
| SZ002603 | 2022-11-17 | risk_distance_below_min | 37.28 | 37.20 | 0.21% |
| SH600028 | 2022-11-23 | risk_distance_below_min | 3.73 | 3.72 | 0.27% |

这些不是没有 winner 信息，而是交易定义上太贴边。若允许这种 entry，R-unit 会被极小 stop distance 放大，后续收益/亏损的 R 解释会失真。

Buyability 不是主要瓶颈：

| split | condition stock-days passed hard filter | rejected stock-days | next-open buy executable rate | limit-up rejected |
|:--|--:|--:|--:|--:|
| train | 15039 | 496 | 98.49% | 31 |
| validation | 8366 | 122 | 98.65% | 8 |
| robustness | 8652 | 196 | 97.93% | 98 |

所以 headline misses 的主因排序大致是：

1. risk distance below min
2. episode compression / entry timestamp not captured
3. true no signal hit
4. buyability, only minor

## 7. Recall Summary

candidate primary recall：

| split | refs | captured | missed | recall | EP2 recall | diff vs EP2 |
|:--|--:|--:|--:|--:|--:|--:|
| train | 456 | 212 | 244 | 46.49% | 13.82% | +32.68 pp |
| validation | 139 | 66 | 73 | 47.48% | 10.79% | +36.69 pp |
| robustness | 243 | 97 | 146 | 39.92% | 16.87% | +23.05 pp |

candidate 对 primary big winner 的 capture 明显高于 EP2 detector，这是 positive evidence。

但 EP2 bridge recall 相反：

| split | bridge refs | candidate captured | candidate bridge recall | EP2 bridge recall | diff |
|:--|--:|--:|--:|--:|--:|
| train | 171 | 21 | 12.28% | 77.78% | -65.50 pp |
| validation | 35 | 2 | 5.71% | 60.00% | -54.29 pp |
| robustness | 100 | 11 | 11.00% | 56.00% | -45.00 pp |

我的解释：post30 seed 不是 EP2 detector 的同类替代品。它更偏向“强势上涨后的 profile”，而 EP2 bridge 更接近原 EP2 launch detector 的结构性 episode 入口。二者捕获的是不同路径的大 winner。

## 8. Density Cap Tightness

candidate 密度过高，是硬失败的核心。

| split | candidate seed-day rate | seed-day cap | utilization | candidate episode rate | episode cap | utilization |
|:--|--:|--:|--:|--:|--:|--:|
| train | 7.998% | 1.650% | 4.85x | 5.198 | 4.835 | 1.08x |
| validation | 7.717% | 1.325% | 5.82x | 4.636 | 3.547 | 1.31x |
| robustness | 7.938% | 1.754% | 4.53x | 4.708 | 4.838 | 0.97x |

与 EP2 相比：

| split | seed-day count vs EP2 | episode count vs EP2 |
|:--|--:|--:|
| train | 13.09x | 3.23x |
| validation | 15.73x | 3.92x |
| robustness | 12.22x | 2.92x |

这个密度说明该 seed 太宽。它不是一个窄 entry trigger，更像一个高召回扫描条件。如果进入 R02，会把后续阶段变成“从大量强势日里再挑选”，而不是验证一个已经收敛的 R01 entry hypothesis。

## 9. Recall-Cost Tradeoff

Recall-Cost Tradeoff 表面上是通过的：candidate 比 EP2 捕获更多 big winner，并且每个 captured winner 的 loss R 低于 EP2。

| split | candidate captured | EP2 captured | added | lost | net added | candidate failed loss R | EP2 failed loss R | incremental loss R |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 315 | 78 | 268 | 31 | 237 | 479.59 | 158.01 | 321.58 |
| validation | 111 | 28 | 92 | 9 | 83 | 250.29 | 81.48 | 168.81 |
| robustness | 162 | 63 | 126 | 27 | 99 | 196.83 | 97.81 | 99.02 |

Captured Post-Reference Entry Cost：

| split | candidate loss R per captured winner | EP2 loss R per captured winner | diff | incremental loss per added winner |
|:--|--:|--:|--:|--:|
| train | 1.52 | 2.03 | -0.50 | 1.36 |
| validation | 2.25 | 2.91 | -0.66 | 2.03 |
| robustness | 1.22 | 1.55 | -0.34 | 1.00 |

这部分是当前 seed 最有价值的证据：虽然触发很宽，但按 captured winner 归一化后，fail-fast 似乎确实控制了一部分亏损。

但这个 positive evidence 不能覆盖密度失败和 matched-delay 失败。换句话说，它说明“这个 profile 有信息”，不说明“它已经是合格 entry seed”。

## 10. Matched-Delay Ineligible Bias

matched-delay ineligible audit 本身通过，说明延迟对照的不可执行偏差没有严重集中在 top delay-return quintile。

但是 matched-delay no-harm gates 失败：

| split | baseline | metric | candidate | delay baseline | diff | gate |
|:--|:--|:--|--:|--:|--:|:--|
| validation | 1d same fail-fast | mean_return_r | -0.0894 | -0.0856 | -0.0037 | passed |
| validation | 1d same fail-fast | p05_return_r | -0.6891 | -0.5787 | -0.1104 | failed |
| validation | 3d same fail-fast | mean_return_r | -0.0894 | -0.0559 | -0.0335 | failed |
| validation | 3d same fail-fast | p05_return_r | -0.6891 | -0.5441 | -0.1450 | failed |
| robustness | 1d same fail-fast | p05_return_r | -0.6243 | -0.5250 | -0.0993 | failed |
| robustness | 3d same fail-fast | p05_return_r | -0.6243 | -0.5246 | -0.0997 | failed |

我的猜测：条件触发日可能偏“冲高/加速日”。如果延后 1 到 3 天，部分 entry 避开了最拥挤或最短期过热的位置，tail risk 更好。因此 V3 seed 可能不是“越早越好”的 entry，而是一个标记强势状态的信号，需要另一个更稳的 entry timing 机制。

注意：这只是猜测，当前 R01 不允许调 entry timing 来救这个 seed。

## 11. Matched-Random Reliability

Matched-Random Reliability 是 report-only，但结果提示 random baseline 的可用性较弱。

| split | baseline | eligible rate range | replicates | capacity shortfall | status |
|:--|:--|:--|--:|:--|:--|
| train | matched_random_same_density_no_fail_fast_h20 | 24.45% - 27.91% | 100 | True | failed |
| train | matched_random_same_density_same_fail_fast_h20 | 24.55% - 28.01% | 100 | True | failed |
| validation | matched_random_same_density_no_fail_fast_h20 | 19.63% - 23.72% | 100 | True | failed |
| validation | matched_random_same_density_same_fail_fast_h20 | 19.63% - 23.72% | 100 | True | failed |
| robustness | matched_random_same_density_no_fail_fast_h20 | 16.47% - 19.88% | 100 | True | failed |
| robustness | matched_random_same_density_same_fail_fast_h20 | 16.47% - 19.88% | 100 | True | failed |

这不能作为单独 stop 理由，但说明同密度随机对照很难构造。原因很可能是 candidate seed 密度过高，导致可替代的同桶 stock-days 被大量消耗。

## 12. R-Unit Distribution And Risk Quintile Cost Control

validation candidate 的 executable episodes 风险距离分布：

| metric | value |
|:--|--:|
| initial_risk_pct p01 | 2.04% |
| p05 | 2.13% |
| p25 | 2.57% |
| median | 3.31% |
| p75 | 4.61% |
| p95 | 7.88% |
| p99 | 10.30% |

风险五分位 cost control 全部通过：

| quintile | failed count | candidate avg loss R | no-fail-fast avg loss R | diff |
|:--|--:|--:|--:|--:|
| risk_q1 | 185 | 0.3528 | 0.5600 | -0.2072 |
| risk_q2 | 182 | 0.3136 | 0.4619 | -0.1483 |
| risk_q3 | 178 | 0.2626 | 0.3711 | -0.1085 |
| risk_q4 | 182 | 0.2561 | 0.3508 | -0.0947 |
| risk_q5 | 178 | 0.1943 | 0.2576 | -0.0632 |

这说明 fail-fast 的风险控制在 executable subset 内是有用的。但注意，这个 subset 已经排除了大量 risk below-min 的 post30 hits。也就是说，风险控制证据只适用于“通过 R01 risk filter 后的样本”，不能反推所有 post30 hits 都可交易。

## 13. Fail-Fast Attribution

当前最支持继续研究的证据来自 fail-fast cost control：

- validation 中 `failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast = -0.1250`，通过。
- validation 中 `failed_seed_median_holding_days_diff_vs_same_seed_no_fail_fast < 0`，通过。
- validation 中 `p05_return_r_diff_vs_same_seed_no_fail_fast >= -0.02`，通过。
- 风险五分位下，candidate 的 failed loss R 均低于 no-fail-fast。

我的理解：fail-fast 不是问题本身，反而可能是当前 hypothesis 里相对有效的一部分。真正的问题是 seed 太宽，以及 signal timing 不够稳定。

## 14. Fail-Fast Error Audit

从 aggregate 结果看，fail-fast 没有把 Recall-Cost Tradeoff 推坏。candidate 在 captured winner 维度上的 loss R per captured winner 低于 EP2。

但这不等于 fail-fast 没有 false reject。V3 当前 headline stop 的主要原因不是 fail-fast false reject，而是：

- density cap 失败；
- bridge EP2 recall 失败；
- matched-delay no-harm 失败；
- post30 signal 到 executable entry 的落差过大。

因此后续如果继续研究，优先级不应该是先优化 fail-fast window，而应该先解决 entry seed 和 timing 的可执行性。

## 15. Counterfactual Failure Inheritance

当前失败大概率会继承到简单 counterfactual：

1. 放宽 density cap：会提高 capture，但直接违背 R01 的低密度目标。
2. 放宽 risk lower bound：会让更多 post30 hits 成为 executable，但会使 R-unit 对极小 stop distance 非常敏感，损害 R 口径可信度。
3. 调整 fail-fast：可能改善局部 tail，但无法解决 seed density 和 matched-delay timing 问题。
4. 只看 primary recall：会过度乐观，因为 bridge recall 和 matched-delay tail 都在提示该 seed 与原 EP2 结构不同。

我的猜测：这个 post30 condition 更适合作为“winner 状态画像”或后续 feature，而不是直接作为 R01 entry trigger。它可能要和一个更稀疏、更靠近可执行结构位的 entry rule 组合，才可能变成可继续的 hypothesis。

## 16. Failed Gates

严格 validator 失败只来自 hard research gates，不是 artifact/schema 问题。

| gate | split | value | threshold | interpretation |
|:--|:--|--:|--:|:--|
| seed_density_day_cap | train | 7.998% | 1.650% | 太宽 |
| seed_density_episode_cap | train | 5.198 | 4.835 | episode 也偏多 |
| seed_density_day_cap | validation | 7.717% | 1.325% | 太宽 |
| seed_density_episode_cap | validation | 4.636 | 3.547 | episode 也偏多 |
| seed_density_day_cap | robustness | 7.938% | 1.754% | 太宽 |
| bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector | validation | -54.29 pp | -5 pp | 不像 EP2 bridge 替代 |
| bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector | robustness | -45.00 pp | -10 pp | 不像 EP2 bridge 替代 |
| matched_delay_3d_mean_no_harm | validation | -3.35 pp | -0.50 pp | 3d delay 更好 |
| matched_delay_1d_p05_no_harm | validation | -11.04 pp | -3 pp | tail 明显更差 |
| matched_delay_3d_p05_no_harm | validation | -14.50 pp | -3 pp | tail 明显更差 |
| robustness_p05_return_r_diff_vs_matched_delay_same_fail_fast_min | robustness | -9.97 pp | -3 pp | robustness tail 不稳 |

report-only failed:

| gate | split | status | interpretation |
|:--|:--|:--|:--|
| random_baseline_reliability_status | validation | failed | 同密度随机对照容量不足，不能作为 hard decision |

## 17. R02 Handoff

R02 Handoff: 不授权。

原因：

- Final decision 是 `stop_ep4_r01_path`。
- discovery scope 是 `all_splits`，不是 clean OOS。
- density cap 多 split 失败。
- matched-delay tail no-harm 失败。
- bridge EP2 recall 大幅落后。

如果继续研究，建议不要把当前 seed 直接推 R02。更合理的后续方向是：

1. 把 post30 condition 当成状态画像，不当作 entry trigger。
2. 单独寻找更低密度、更接近可执行结构位的 entry timing。
3. 保留 fail-fast 成本控制思路，但不要用它掩盖 entry seed 太宽的问题。
4. 若要重开实验，应先明确目标是“post30 winner state classifier”还是“pre-entry executable trigger”，两者不能混用。

## 18. 总体判断

这次实验的价值不是证明 V3 seed 可进入下一阶段，而是把 post30 profile 和 executable entry 的差异量化了：

- post30 coverage 很高，说明条件确实描述了大 winner 后续状态。
- executable capture 明显下降，说明这个状态不天然等于可交易 entry。
- risk below-min 是最大漏斗，说明很多命中发生在 stop 太近的位置。
- density 过高说明它太像扫描器，不像 entry seed。
- matched-delay tail 失败说明 timing 可能偏拥挤或过热。

因此当前 hypothesis 应停止，不进入 R02。若继续，应把它降级为 feature/profile evidence，而不是继续包装成 R01 entry seed。
