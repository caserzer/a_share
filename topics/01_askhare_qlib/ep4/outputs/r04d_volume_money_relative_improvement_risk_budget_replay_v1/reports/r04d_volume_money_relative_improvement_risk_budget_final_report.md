# R04d volume_money 相对改善池 risk-budget replay 最终报告

R04d does not reinterpret R04c v1 as passed.
volume_money is a descriptive relative-improvement lead, not an R04c selected pool.
R04d uses a fixed r02_precision_volume_money pool.
R04d primary policies are shorter hold, time_stop, break_even, fixed_stop, and sizing only.
Robustness is final readout only.
Headline net_return metrics use weighted_net_return; unweighted returns are audit only.
No production entry rule is emitted by this diagnostic.

## 1. 最终结论

| 项目 | 结果 |
|---|---|
| final_decision | `r04d_no_policy_passed_validation` |
| selected_policy_id | 空 |
| validation_status | `passed` |
| failed_checks | 0 |
| validation hard gate pass | 0 / 8 个 train-selected policies |
| 全 validation policy 中 net > 0 | 0 / 58 |
| 全 validation policy 中 delta_vs_hold120 >= 2pct | 0 / 58 |

结论很直接：`volume_money` 的 simple risk-budget / shorter-hold replay 确实能显著压左尾，但不能把 validation net mean 推到正收益，也没有达到 `+2pct` 的相对改善门槛。更关键的是，最能压左尾的短持有 policy 几乎完全牺牲 +50 winner retention。因此 R04d 不能升级为可选 policy，只能保留为 descriptive diagnostic。

这不是 validator 过严导致的假失败。即使不只看 train-selected 的 8 个 policy，而看全部 58 个有效 policy，validation 最好的 net mean 也只有 `-0.58%`，最好的 delta_vs_hold120 也只有 `+1.49%`，仍低于 `net > 0` 和 `delta >= +2pct` 两条核心门槛。

## 2. 实验边界

R04d 不是 R04c 的“补充通过”实验，而是一个新问题：

> 一个在 validation 中相对少亏、左尾改善、且主要由新事件构成的 fixed pool，能否通过简单 risk-budget / shorter-hold / break-even replay，把相对改善转成 OOS 正期望？

固定主池为 `r02_precision_volume_money`，不得重选 pool，不得加入 `range_breakout` / `pullback_drawdown`，不得用 R04d 结果反向删样本。policy 只允许 `no_exit`、`time_stop`、`break_even_after_gain`、`fixed_stop`、`fixed_size`、`volatility_scaled`。ATR / EMA / CTA / profit_lock / market-state gate 均未运行。

## 3. 上游 hold120 no-exit 画像

这是 R04c 中暴露出 `volume_money` 值得单独 diagnostic replay 的原因：validation 虽然绝对收益为负，但相对 matched baseline_A 明显少亏，且左尾改善很大。

| split | replay_complete | censored | net_mean | p10 | loss<=-5 | max_gain50_rate | matched net delta | matched p10 delta | matched loss delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2,969 | 19.08% | +4.22% | -25.43% | 42.10% | 14.48% | -2.52% | +1.39% | -0.07% |
| validation | 1,568 | 24.40% | -2.07% | -26.62% | 46.94% | 5.99% | +4.53% | +3.03% | -10.84% |
| robustness | 1,553 | 29.31% | +7.82% | -15.49% | 25.89% | 10.17% | +0.85% | +2.24% | -6.11% |

解读：

- validation 的 `-2.07%` 说明这个池子不是绝对正期望池。
- validation 相对 matched baseline_A 的 `+4.53pct`、p10 `+3.03pct`、loss<=-5 `-10.84pct` 说明它不是随机噪声，确实有相对少亏和左尾改善。
- robustness 的 `+7.82%` 是强正收益，但 matched delta 只有 `+0.85pct`，说明好年份中一部分表现来自市场背景。
- 因此 R04d 的正确目标不是证明 `volume_money` 已经通过，而是测试“简单风险管理能否把 validation 从相对少亏推成正收益”。

## 4. Pool 重建与输入一致性

| 指标 | 数值 |
|---|---:|
| R02 reconstructed events | 7,940 |
| R04c volume_money events | 7,940 |
| overlap events | 7,940 |
| overlap share vs R04d | 100.00% |
| overlap share vs R04c | 100.00% |
| reconciliation_status | `passed` |

R04d 的 pool membership 与 R04c 完全一致，重建没有引入样本漂移。R04d 仍以 R02 family precision panel 作为 membership authority；R04c cache 只用于 reconciliation 和 same-policy matched baseline replay。

## 5. Policy matrix 与 replay 覆盖

| 项目 | 数量 |
|---|---:|
| policy matrix rows | 88 |
| 有效 selectable policies | 58 |
| duplicate equivalent policy rows | 18 |
| invalid time_stop rows | 12 |
| split summary rows | 174 |
| replay universe | `volume_money` + `matched_baseline_A` |

有效 policy 分布：

| family | fixed_size | volatility_scaled |
|---|---:|---:|
| `break_even_after_gain` | 12 | 12 |
| `fixed_stop` | 12 | 12 |
| `no_exit` | 4 | 4 |
| `time_stop` | 1 | 1 |

按 hold rule 分布：

| hold_rule | 有效 policy 数 |
|---|---:|
| `hold_20d` | 16 |
| `hold_40d` | 14 |
| `hold_60d` | 14 |
| `hold_120d` | 14 |

`time_stop` 只有 `time_stop_days=10` 进入有效 selectable row，因为其他 `time_stop_days >= hold_rule_max_days` 或等价 duplicate 被剔除。

## 6. Train 选择出的 parameter set

Train 每个 family 只选择一个参数进入 validation，因此 validation gate 实际检查 8 个 train-selected policy。

| family | train-selected policy | train score | train net | validation net | validation delta | validation p10 delta | validation loss delta | validation retention | robustness net | robustness delta | robustness retention |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `time_stop__volatility_scaled` | `hold_20d__time_stop__time_stop_days10__volatility_scaled` | -0.488 | +0.22% | -0.58% | +1.49% | +18.56% | -24.82% | 0.88% | +0.57% | -7.25% | 1.72% |
| `fixed_stop__volatility_scaled` | `hold_20d__fixed_stop__stop_loss_pctm0p05__volatility_scaled` | 2.622 | +0.42% | -0.63% | +1.45% | +19.93% | -14.28% | 6.19% | +0.65% | -7.18% | 5.52% |
| `fixed_stop__fixed_size` | `hold_20d__fixed_stop__stop_loss_pctm0p05__fixed_size` | 1.878 | +0.36% | -0.63% | +1.44% | +18.93% | -0.82% | 6.19% | +0.63% | -7.20% | 5.52% |
| `time_stop__fixed_size` | `hold_20d__time_stop__time_stop_days10__fixed_size` | -0.488 | +0.23% | -0.69% | +1.38% | +16.72% | -20.95% | 0.88% | +0.61% | -7.21% | 1.72% |
| `no_exit__volatility_scaled` | `hold_20d__no_exit__none__volatility_scaled` | 1.587 | +0.56% | -0.88% | +1.19% | +15.69% | -16.46% | 6.19% | +1.02% | -6.81% | 5.86% |
| `break_even_after_gain__volatility_scaled` | `hold_20d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | 1.437 | +0.51% | -0.89% | +1.19% | +15.78% | -17.49% | 6.19% | +0.98% | -6.85% | 5.86% |
| `break_even_after_gain__fixed_size` | `hold_20d__break_even_after_gain__activation_gain_pct0p08__fixed_size` | 1.576 | +0.44% | -0.96% | +1.12% | +13.39% | -14.44% | 6.19% | +1.01% | -6.82% | 5.86% |
| `no_exit__fixed_size` | `hold_20d__no_exit__none__fixed_size` | 1.816 | +0.52% | -0.96% | +1.12% | +13.11% | -13.20% | 6.19% | +1.06% | -6.76% | 5.86% |

Train 选择呈现出一个非常清晰的偏向：几乎全部 family 都选到了 `hold_20d`，因为短持有在 train 上对左尾和平均持仓日有利。但这也预埋了 validation 失败的核心原因：短持有极度牺牲 winner retention。

## 7. Validation gate 结果

Validation hard gate 要同时满足：

- `net_return_mean > 0`
- `net_return_mean_delta_vs_volume_money_hold120 >= +2pct`
- `p10_delta_vs_volume_money_hold120 >= 0`
- `loss_le_minus5_delta_vs_volume_money_hold120 < 0`
- `max_gain50_retention_vs_volume_money_hold120 >= 50%`
- denominator / censored / max_gain50 count 足够

8 个 train-selected policy 的 gate 结果：

| rank | policy | family | net_mean | delta_vs_hold120 | p10_delta | loss_delta | retention | censored | failed gates |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `hold_20d__time_stop__time_stop_days10__volatility_scaled` | `time_stop__volatility_scaled` | -0.58% | +1.49% | +18.56% | -24.82% | 0.88% | 4.10% | net, delta, retention |
| 2 | `hold_20d__fixed_stop__stop_loss_pctm0p05__volatility_scaled` | `fixed_stop__volatility_scaled` | -0.63% | +1.45% | +19.93% | -14.28% | 6.19% | 5.06% | net, delta, retention |
| 3 | `hold_20d__time_stop__time_stop_days10__fixed_size` | `time_stop__fixed_size` | -0.69% | +1.38% | +16.72% | -20.95% | 0.88% | 4.10% | net, delta, retention |
| 4 | `hold_20d__fixed_stop__stop_loss_pctm0p05__fixed_size` | `fixed_stop__fixed_size` | -0.63% | +1.44% | +18.93% | -0.82% | 6.19% | 5.06% | net, delta, retention |
| 5 | `hold_20d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.89% | +1.19% | +15.78% | -17.49% | 6.19% | 5.35% | net, delta, retention |
| 6 | `hold_20d__no_exit__none__volatility_scaled` | `no_exit__volatility_scaled` | -0.88% | +1.19% | +15.69% | -16.46% | 6.19% | 5.40% | net, delta, retention |
| 7 | `hold_20d__break_even_after_gain__activation_gain_pct0p08__fixed_size` | `break_even_after_gain__fixed_size` | -0.96% | +1.12% | +13.39% | -14.44% | 6.19% | 5.35% | net, delta, retention |
| 8 | `hold_20d__no_exit__none__fixed_size` | `no_exit__fixed_size` | -0.96% | +1.12% | +13.11% | -13.20% | 6.19% | 5.40% | net, delta, retention |

失败归因非常集中：

| failed gate | 失败 policy 数 |
|---|---:|
| `net_return_mean` | 8 / 8 |
| `net_return_mean_delta_vs_volume_money_hold120` | 8 / 8 |
| `max_gain50_retention_vs_volume_money_hold120` | 8 / 8 |

也就是说，validation 不是“差一条小规则”。所有 train-selected policy 都同时卡在正收益、相对 +2pct、winner retention 三条核心门槛。

## 8. 全 policy validation 扫描

为了排除“train 只选 8 个 policy 导致漏掉好 policy”的可能性，下面看全部 58 个有效 policy 的 validation 分布。

| 指标 | 结果 |
|---|---:|
| validation net > 0 policy 数 | 0 / 58 |
| validation net mean 最高值 | -0.58% |
| delta_vs_hold120 >= +2pct policy 数 | 0 / 58 |
| delta_vs_hold120 最高值 | +1.49% |
| retention >= 50% policy 数 | 14 / 58 |
| retention 最高值 | 83.19% |

Validation net mean 最高的 15 个 policy：

| rank | policy | family | net_mean | delta_vs_hold120 | p10_delta | loss_delta | retention | censored | matched_delta | avg_days |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `hold_20d__time_stop__time_stop_days10__volatility_scaled` | `time_stop__volatility_scaled` | -0.58% | +1.49% | +18.56% | -24.82% | 0.88% | 4.10% | -0.03% | 11.0 |
| 2 | `hold_20d__fixed_stop__stop_loss_pctm0p05__volatility_scaled` | `fixed_stop__volatility_scaled` | -0.63% | +1.45% | +19.93% | -14.28% | 6.19% | 5.06% | +0.12% | 15.0 |
| 3 | `hold_20d__fixed_stop__stop_loss_pctm0p05__fixed_size` | `fixed_stop__fixed_size` | -0.63% | +1.44% | +18.93% | -0.82% | 6.19% | 5.06% | +0.31% | 15.0 |
| 4 | `hold_20d__time_stop__time_stop_days10__fixed_size` | `time_stop__fixed_size` | -0.69% | +1.38% | +16.72% | -20.95% | 0.88% | 4.10% | +0.07% | 11.0 |
| 5 | `hold_120d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.72% | +1.36% | +9.28% | -17.19% | 69.03% | 22.03% | +2.61% | 94.6 |
| 6 | `hold_20d__fixed_stop__stop_loss_pctm0p08__volatility_scaled` | `fixed_stop__volatility_scaled` | -0.80% | +1.28% | +17.58% | -11.26% | 6.19% | 5.26% | +0.25% | 17.6 |
| 7 | `hold_120d__break_even_after_gain__activation_gain_pct0p1__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.81% | +1.27% | +8.76% | -14.33% | 72.57% | 22.66% | +2.81% | 100.7 |
| 8 | `hold_20d__fixed_stop__stop_loss_pctm0p08__fixed_size` | `fixed_stop__fixed_size` | -0.83% | +1.25% | +16.41% | -7.14% | 6.19% | 5.26% | +0.49% | 17.6 |
| 9 | `hold_20d__fixed_stop__stop_loss_pctm0p1__volatility_scaled` | `fixed_stop__volatility_scaled` | -0.85% | +1.23% | +16.26% | -12.69% | 6.19% | 5.26% | +0.25% | 18.7 |
| 10 | `hold_20d__no_exit__none__volatility_scaled` | `no_exit__volatility_scaled` | -0.88% | +1.19% | +15.69% | -16.46% | 6.19% | 5.40% | +0.21% | 21.0 |
| 11 | `hold_20d__break_even_after_gain__activation_gain_pct0p15__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.88% | +1.19% | +15.69% | -16.51% | 6.19% | 5.40% | +0.21% | 21.0 |
| 12 | `hold_20d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.89% | +1.19% | +15.78% | -17.49% | 6.19% | 5.35% | +0.19% | 20.6 |
| 13 | `hold_20d__break_even_after_gain__activation_gain_pct0p1__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.89% | +1.18% | +15.77% | -16.93% | 6.19% | 5.35% | +0.21% | 20.8 |
| 14 | `hold_20d__fixed_stop__stop_loss_pctm0p1__fixed_size` | `fixed_stop__fixed_size` | -0.91% | +1.16% | +14.75% | -10.04% | 6.19% | 5.26% | +0.49% | 18.7 |
| 15 | `hold_120d__break_even_after_gain__activation_gain_pct0p15__volatility_scaled` | `break_even_after_gain__volatility_scaled` | -0.94% | +1.13% | +7.75% | -8.55% | 78.76% | 23.63% | +3.22% | 111.2 |

这张表给出两个重要信息：

- 短持有 policy 的 validation net 更好、p10 改善更大、censored 更低，但 retention 只有 0.88%-6.19%，基本把右尾截掉。
- 120d break-even policy 能保留 69%-79% winner，并且 matched_delta 很好，但 validation 仍是负收益，且 delta_vs_hold120 仍低于 +2pct。

## 9. 按 hold / exit / sizing 的结构归因

### 9.1 按 hold_rule

| hold_rule | policy 数 | best net | median net | best delta | best p10_delta | median retention | min censored |
|---|---:|---:|---:|---:|---:|---:|---:|
| `hold_20d` | 16 | -0.58% | -0.88% | +1.49% | +19.93% | 6.19% | 4.10% |
| `hold_40d` | 14 | -1.44% | -2.09% | +0.63% | +19.58% | 25.66% | 6.36% |
| `hold_60d` | 14 | -1.35% | -1.75% | +0.73% | +19.47% | 33.63% | 6.80% |
| `hold_120d` | 14 | -0.72% | -1.81% | +1.36% | +19.31% | 69.03% | 9.26% |

`hold_20d` 是 validation 绝对收益最好的持有长度，但 retention 不可接受。`hold_120d` 加 break-even 能保留右尾，但无法把 validation 转正。中间的 40/60 天没有形成更优折中。

### 9.2 按 exit family

| exit family | policy 数 | best net | median net | best delta | best p10_delta | median retention | min censored |
|---|---:|---:|---:|---:|---:|---:|---:|
| `time_stop` | 2 | -0.58% | -0.64% | +1.49% | +18.56% | 0.88% | 4.10% |
| `fixed_stop` | 24 | -0.63% | -1.87% | +1.45% | +19.93% | 26.55% | 5.06% |
| `break_even_after_gain` | 24 | -0.72% | -1.61% | +1.36% | +15.78% | 30.09% | 5.35% |
| `no_exit` | 8 | -0.88% | -1.78% | +1.19% | +15.69% | 30.97% | 5.40% |

`time_stop` 的左尾压缩最强，但本质是极短持有，winner retention 几乎归零。`fixed_stop` 与 `break_even` 都没有把 validation 推正。`break_even` 在长持有时更像“保右尾的保险”，但保险费仍然太高。

### 9.3 按 sizing

| sizing | policy 数 | best net | median net | best delta | best p10_delta | median retention | min censored | avg position_weight_mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `fixed_size` | 29 | -0.63% | -1.85% | +1.44% | +18.93% | 26.55% | 4.10% | 1.000 |
| `volatility_scaled` | 29 | -0.58% | -1.59% | +1.49% | +19.93% | 26.55% | 4.10% | 0.872 |

`volatility_scaled` 有小幅帮助，尤其在 top policy 上把 validation net 从 `-0.69%` 改到 `-0.58%`，但这不是决定性改善。它更像降低风险暴露后的分布平移，不是新的 alpha 来源。

## 10. Robustness readout

由于没有 validation-selected policy，R04d 没有正式 selected robustness readout。但从全 policy robustness 表看，结论同样清楚：在好年份里，volume_money hold120 no-exit 本身最好，risk-budget policy 普遍降低收益。

Robustness net mean 最高的 policy：

| rank | policy | family | net_mean | delta_vs_hold120 | p10_delta | loss_delta | retention | censored | matched_delta | avg_days |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `volume_money_hold120_no_exit_fixed_size` | `no_exit__fixed_size` | +7.82% | +0.00% | +0.00% | +0.00% | 54.48% | 29.31% | +0.85% | 121.0 |
| 2 | `hold_120d__no_exit__none__volatility_scaled` | `no_exit__volatility_scaled` | +7.32% | -0.51% | +2.75% | -1.22% | 54.48% | 29.31% | +0.99% | 121.0 |
| 3 | `hold_120d__break_even_after_gain__activation_gain_pct0p15__fixed_size` | `break_even_after_gain__fixed_size` | +7.23% | -0.60% | +1.00% | -3.32% | 52.07% | 27.99% | +1.37% | 112.7 |
| 4 | `hold_120d__break_even_after_gain__activation_gain_pct0p1__fixed_size` | `break_even_after_gain__fixed_size` | +6.79% | -1.04% | +2.67% | -5.89% | 50.00% | 26.72% | +1.29% | 104.7 |
| 5 | `hold_120d__break_even_after_gain__activation_gain_pct0p15__volatility_scaled` | `break_even_after_gain__volatility_scaled` | +6.75% | -1.07% | +3.15% | -4.01% | 52.07% | 27.99% | +1.32% | 112.7 |
| 6 | `hold_120d__break_even_after_gain__activation_gain_pct0p1__volatility_scaled` | `break_even_after_gain__volatility_scaled` | +6.32% | -1.50% | +4.28% | -7.00% | 50.00% | 26.72% | +1.28% | 104.7 |
| 7 | `hold_120d__break_even_after_gain__activation_gain_pct0p08__fixed_size` | `break_even_after_gain__fixed_size` | +6.28% | -1.55% | +3.94% | -8.14% | 46.55% | 25.63% | +1.30% | 97.7 |
| 8 | `hold_120d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | `break_even_after_gain__volatility_scaled` | +5.85% | -1.98% | +5.08% | -9.36% | 46.55% | 25.63% | +1.23% | 97.7 |

Robustness 里有 7 个 policy 高于 baseline_A robustness `+6.12%`，但没有任何 policy 高于 volume_money hold120 no-exit 的 `+7.82%`。这说明 risk-budget 在好年份主要是“保险费”：能改善 p10 和 loss tail，但会牺牲整体收益。

## 11. Censored 与可交易完整性

R04d 中一个确实正面的发现是：shorter hold 明显改善可交易完整性。

| policy | split | replay_complete | split_boundary censored | missing_price censored | total censored |
|---|---|---:|---:|---:|---:|
| `volume_money_hold120_no_exit_fixed_size` | validation | 75.60% | 23.63% | 0.77% | 24.40% |
| `hold_20d__time_stop__time_stop_days10__volatility_scaled` | validation | 95.90% | 3.91% | 0.19% | 4.10% |
| `hold_20d__fixed_stop__stop_loss_pctm0p05__volatility_scaled` | validation | 94.94% | 4.87% | 0.19% | 5.06% |
| `hold_120d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | validation | 77.97% | 21.26% | 0.77% | 22.03% |
| `volume_money_hold120_no_exit_fixed_size` | robustness | 70.69% | 16.61% | 12.38% | 29.31% |
| `hold_20d__time_stop__time_stop_days10__volatility_scaled` | robustness | 97.04% | 2.59% | 0.36% | 2.96% |
| `hold_20d__fixed_stop__stop_loss_pctm0p05__volatility_scaled` | robustness | 94.72% | 4.92% | 0.36% | 5.28% |
| `hold_120d__break_even_after_gain__activation_gain_pct0p08__volatility_scaled` | robustness | 74.37% | 13.02% | 12.38% | 25.63% |

可交易完整性改善是真的，但它没有转化为通过 gate 的收益改善。短持有解决了 censored 问题，也压了左尾，但代价是 winner retention 断崖式下降。

## 12. 必需诊断清单

| 清单 | 结果 |
|---|---|
| validation net > 0 policies | None |
| validation passed but robustness failed policies | None |
| robustness strong_pass policies | None |
| winner retention < 50% policies | 大量存在，主要集中在 `hold_20d` / `hold_40d` / fixed_stop / time_stop |
| censored_share > 25% policies | 主要是 hold120 或接近 hold120 的 long-hold policy |
| weighted-pass but unweighted-fail policies | None |
| matched_baseline_A same-policy delta <= 0 policies | `hold_20d__time_stop__time_stop_days10__volatility_scaled` |

## 13. Findings

### 13.1 左尾改善是真实的

Validation top policy 的 p10 改善非常大：`+13pct` 到 `+20pct`，loss<=-5 delta 也大多为负。尤其 `hold_20d__time_stop__time_stop_days10__volatility_scaled` 的 p10 delta 为 `+18.56pct`，loss delta 为 `-24.82pct`。这说明 `volume_money` 的亏损路径可以被简单持有期/止损类规则显著压缩。

### 13.2 但收益改善不够

所有 validation policy 的 net mean 都仍为负，最好也只有 `-0.58%`。所有 policy 的 delta_vs_hold120 都低于 `+2pct`，最好只有 `+1.49pct`。这说明 R04d 的失败不是某个参数没调好，而是简单 risk-budget 的收益杠杆不够。

### 13.3 winner retention 是最硬的瓶颈

短持有 policy 的 retention 普遍只有 `0.88%` 到 `6.19%`。它们通过提前退出压住亏损，但同时也提前卖掉了未来可能到 +50% 的右尾样本。R04c/R04d 对 `volume_money` 的价值假设本来就依赖“相对少亏 + 部分右尾”，如果右尾被砍掉，剩下的是一个低波动但仍负收益的策略。

### 13.4 长持有 break-even 是更合理的保险形态，但仍不够

`hold_120d__break_even_after_gain__activation_gain_pct0p08/0p10/0p15__volatility_scaled` 在 validation 中能保留 69%-79% retention，matched delta 也有 `+2.61pct` 到 `+3.22pct`。但它们的 validation net 仍是 `-0.72%` 到 `-0.94%`，delta_vs_hold120 也只有 `+1.13pct` 到 `+1.36pct`。这说明“保右尾的 break-even 保险”方向比短持有更健康，但仍达不到 R04d v1 的通过标准。

### 13.5 volatility_scaled 是辅助，不是主因

`volatility_scaled` 平均 position_weight 约 `0.872`。它在 validation 上略好于 fixed_size，例如 top time_stop 从 `-0.69%` 改到 `-0.58%`，但并没有改变最终结论。它更像降低暴露后的风险平滑，而不是让 pool 产生正期望。

### 13.6 robustness 进一步说明保险有成本

Robustness 中 `volume_money_hold120_no_exit_fixed_size` 本身是 `+7.82%`，是全表最高。risk-budget policy 即使能改善 p10 / loss tail，也没有一个超过 hold120 no-exit。也就是说，在好年份中这些 policy 主要付出了保险费，降低了收益上限。

## 14. 后续研究判断

### 不建议继续在 R04d v1 框架内加复杂 exit

当前证据不支持直接升级到 CTA / trailing / 更多 stop 参数。原因是简单 policy 已经给出了清楚形态：短持有压左尾但杀右尾，长持有保右尾但收益改善不够。继续加复杂 exit 很可能只是提高自由度，把 validation 的少数路径拟合得更好，但无法解决 pool 本身的绝对期望问题。

### volume_money 仍值得保留为 portfolio-level relative lead

R04d 不否定 `volume_money`。它否定的是“单独 volume_money pool + 简单 risk-budget 能直接变成正期望 policy”。`volume_money` 在 validation 相对 matched baseline_A 的改善仍然明显，且 pool 与 baseline_A overlap 低，说明它可以作为后续 union pool 或 portfolio-level sleeve 的组成部分，而不是单独主策略。

### 下一步更合理的是 R04e / union pool，而不是 R04d 参数加深

更高 ROI 的后续方向：

1. 把 `volume_money` 与 `range_breakout`、`pullback_drawdown` 这类同样有相对改善但事件 universe 不完全重叠的 pool 做 frozen union。
2. 在 union pool 上先看 hold120 / shorter-hold 的 portfolio-level 分布，而不是继续单池调参。
3. 如果要重开 `volume_money`，应把问题改成“relative-loss-reduction sleeve”或“组合中降低左尾的事件源”，而不是要求它单独转正。

### 若要改 gate，必须新 requirement

R04d v1 的 `net > 0`、`delta >= +2pct`、`retention >= 50%` 是预先冻结的 hard gate。不能因为看到 `-0.58%` 和 `+1.49pct` 接近而回填通过。若要研究“少亏型池子是否可用于组合层”，应新建 requirement，使用组合级 expected return / drawdown / turnover / overlap 作为 primary metric，而不是修改 R04d v1 的 final decision。

## 15. 一句话总结

`volume_money` 是一个有相对左尾改善的候选事件源，但不是一个能被简单 hold/exit/sizing 规则转成正期望的单独主池。R04d 的价值在于确认了失败结构：左尾可以压，censored 可以降，但正收益和右尾保留不能同时满足。因此后续应转向 frozen union / portfolio-level 组合诊断，而不是继续在单池上加复杂 exit。
