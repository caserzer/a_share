# R04b 固定入场 Hold / Exit / Risk-Budget CTA 诊断报告

R04b is fixed-entry policy replay, not entry eligibility.
CTA/trailing is an exit_rule family, not a separate strategy track.
Market and industry states are interaction diagnostics only, not selection gates.
+10 before -5 is legacy diagnostic only for R04b.
max_gain50_retention_vs_hold120 gate threshold = 0.60.
No production entry gate, sizing rule, or CTA strategy is emitted by this diagnostic.

## 结论摘要

Final decision: `r04b_policy_not_robust_hold_exit_diagnostic_complete`。

validation 选出的最终 policy 是 `hold_120d|break_even_after_gain_10pct|market_state_scaled|activation_gain_pct=0.1`。它在 validation 上通过 hard gates：net return 均值相对 hold120 提升 `+3.57%`，p10 左尾提升 `+13.34%`，bad-path loss 压缩 `+24.29%`，同时保留 `83.33%` 的 hold120 +50% 潜在 winner。但 robustness 没有通过，失败点不是 retention，也不是左尾，而是均值 payoff：robustness 的 net return delta 为 `-3.05%`。

核心判断是：R04b 证明了 fixed-entry RPS pool 的 exit / sizing 管理可以明显降低左尾和坏路径，但还没有证明它能在不同 OOS 年份中稳定提高期望收益。CTA / trailing 家族在 validation 的最高 net delta 看起来更强，但主要来自快速退出，通常伴随严重右尾损失；在 robustness 上，所有 trailing / stop family 的 best net delta 都低于 hold120 baseline。因此本轮不能把 CTA 或任何 exit family 升级为可用策略，只能保留为诊断结论。

## 0. 输入与执行完整性

R04b 使用 R04 baseline_A 全 RPS included pool，未使用 mask_B / mask_C 作为 selection pool。R04 source entry price 与 R04b PIT adjusted open 的 reconciliation 全部通过，entry price diff 的 p95 和 max 都只有浮点误差级别。

| split | R04 candidate rows | included rows | replay eligible rows | valid entry rows | entry mismatch | missing price path |
|---|---:|---:|---:|---:|---:|---:|
| train | 8,245 | 6,656 | 6,656 | 6,656 | 0 | 0 |
| validation | 4,130 | 3,453 | 3,453 | 3,453 | 0 | 0 |
| robustness | 4,207 | 2,864 | 2,864 | 2,864 | 0 | 0 |

Policy matrix 共 `261` 行，其中 `249` 个有效 policy/split replay 组合进入 summary，`222` 个 train-selectable policy，`27` 个 ATR activation sensitivity policy 被排除在选择之外。validator 结果为 `passed`，共 `66` 项检查，`0` 个失败项。

## 1. Q1: hold120 baseline 下 RPS pool 的基础画像

hold120 baseline 本身呈现很强的年份差异。validation 是明显差 split：均值 `-6.38%`，p10 `-29.38%`，`loss<=-5%` 达 `57.94%`。robustness 则是正收益 split：均值 `+6.12%`，p10 `-19.92%`，`loss<=-5%` 降到 `35.25%`。

| split | complete / event | censored | net mean | p10 | p90 | loss <= -5% | loss <= -10% | +50 winner count | +50 winner rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 6,403 / 6,656 | 3.80% | +7.64% | -26.76% | +52.53% | 41.70% | 33.45% | 1,400 | 21.86% |
| validation | 3,414 / 3,453 | 1.13% | -6.38% | -29.38% | +18.97% | 57.94% | 45.87% | 216 | 6.33% |
| robustness | 2,800 / 2,864 | 2.23% | +6.12% | -19.92% | +33.67% | 35.25% | 25.46% | 325 | 11.61% |

这解释了为什么 validation 上任何“少亏”的 exit policy 都容易看起来好：baseline 太差，left-tail insurance 的收益被放大。相反，robustness 的 baseline 本来就有正收益和较好右尾，提前退出更容易变成机会成本。

## 2. Q2: train 中胜出的 exit_rule family 与参数

train selection 是在同一 `policy_family_id = hold_rule_id x exit_rule_family_id x sizing_rule_id` 内选参数。所有胜出项都来自 `hold_120d`，说明 train 阶段没有支持把主 holding horizon 缩到 20d/60d 作为默认选择。

| policy family | train-selected parameter | score |
|---|---|---:|
| hold_120d / no_exit / fixed_size | no_params | 0.0000 |
| hold_120d / fixed_stop / fixed_size | stop_loss_pct = -10% | 1.4804 |
| hold_120d / break_even_after_gain / fixed_size | activation_gain_pct = 10% | 1.4374 |
| hold_120d / profit_lock_after_gain / fixed_size | activation = 15%, locked = 5% | 1.8037 |
| hold_120d / no_exit / volatility_scaled | no_params | 0.0000 |
| hold_120d / fixed_stop / volatility_scaled | stop_loss_pct = -8% | -0.6762 |
| hold_120d / break_even_after_gain / volatility_scaled | activation_gain_pct = 10% | 1.4312 |
| hold_120d / profit_lock_after_gain / volatility_scaled | activation = 15%, locked = 5% | 1.8737 |
| hold_120d / no_exit / market_state_scaled | no_params | 0.0000 |
| hold_120d / fixed_stop / market_state_scaled | stop_loss_pct = -8% | -0.6854 |
| hold_120d / break_even_after_gain / market_state_scaled | activation_gain_pct = 10% | 1.3942 |
| hold_120d / profit_lock_after_gain / market_state_scaled | activation = 15%, locked = 5% | 1.8392 |

一个重要细节：train 最喜欢的是 profit_lock_after_gain，尤其是 volatility_scaled / market_state_scaled 下的 `15% activation / 5% lock`。但 validation 最终没有选 profit_lock，而是选了 break_even_after_gain + market_state_scaled，说明 train 最优参数没有完全外推。

## 3. Q3: validation 中哪些 policy family 通过 hard gates

validation 使用 train-selected representative 做 family-level selection。12 个 train-selected representatives 中，9 个通过 validation gates，3 个失败。最终排序第一的是 `hold_120d / break_even_after_gain / market_state_scaled`。

| rank | policy family | validation result | net delta | p10 delta | bad-path compression | retention |
|---:|---|---|---:|---:|---:|---:|
| 1 | break_even_after_gain / market_state_scaled | selected | +3.57% | +13.34% | +24.29% | 83.33% |
| 2 | profit_lock_after_gain / market_state_scaled | lower score | +3.42% | +12.36% | +18.35% | 82.87% |
| 3 | no_exit / market_state_scaled | lower score | +2.68% | +11.53% | +9.49% | 100.00% |
| 4 | break_even_after_gain / volatility_scaled | lower score | +2.98% | +10.03% | +20.37% | 83.33% |
| 5 | fixed_stop / market_state_scaled | lower score | +3.27% | +20.52% | +15.53% | 65.28% |
| 6 | profit_lock_after_gain / volatility_scaled | lower score | +2.85% | +9.18% | +13.40% | 82.87% |
| 7 | no_exit / volatility_scaled | lower score | +2.00% | +8.46% | +3.78% | 100.00% |
| 8 | break_even_after_gain / fixed_size | lower score | +1.52% | +2.45% | +17.79% | 83.33% |
| 9 | fixed_stop / volatility_scaled | failed validation gate | +2.70% | +19.66% | -12.23% | 65.28% |
| 10 | profit_lock_after_gain / fixed_size | lower score | +1.35% | +1.30% | +11.38% | 82.87% |
| 11 | no_exit / fixed_size | failed validation gate | 0.00% | 0.00% | 0.00% | 100.00% |
| 12 | fixed_stop / fixed_size | failed validation gate | +0.62% | +15.82% | -19.28% | 72.69% |

这里的验证结果支持“market_state_scaled 有边际帮助”，但不能解释成 market state 变成入场条件。它只是 position weight 的缩放维度，且后续 robustness 并未确认该收益。

## 4. Q4/Q5: final selected policy 的 OOS 表现与 retention gate

Selected policy 在三个 split 上都满足 `max_gain50_retention_vs_hold120 >= 60%`，所以 robustness 失败不是因为砍掉右尾。失败来自均值收益在 robustness 变成负增量。

| split | net mean | hold120 net mean | net delta | p10 delta | loss <= -5% | hold120 loss <= -5% | bad-path compression | +50 retained / +50 total | retention | winner_exit_efficiency | avg holding days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | +4.85% | +7.64% | -2.79% | +10.71% | 26.30% | 41.70% | +15.40% | 1,114 / 1,400 | 79.57% | 62.24% | 93.26 |
| validation | -2.81% | -6.38% | +3.57% | +13.34% | 33.65% | 57.94% | +24.29% | 180 / 216 | 83.33% | 54.12% | 96.51 |
| robustness | +3.06% | +6.12% | -3.05% | +9.32% | 20.96% | 35.25% | +14.29% | 280 / 325 | 86.15% | 52.82% | 101.02 |

robustness 仍然保留了 `86.15%` 的 +50 winner，也把 `loss<=-5%` 从 `35.25%` 降到 `20.96%`。但它把均值从 hold120 的 `+6.12%` 降到 `+3.06%`，说明在较好的市场年份里，这个 break-even policy 的保护成本超过了左尾收益。

## 5. Q6: CTA / trailing 是否真的优于 fixed_stop / time_stop / profit_lock

不成立。只看 validation 的 best net delta，EMA_trailing、time_stop、fixed_stop 都排在前面；但这些最高收益版本大多是短持有、快退出，并严重压缩右尾。

| exit family | validation best net delta | validation best p10 delta | validation best bad compression | validation best retention | validation median retention |
|---|---:|---:|---:|---:|---:|
| EMA_trailing | +5.97% | +25.30% | +52.18% | 29.17% | 18.06% |
| time_stop | +5.74% | +22.35% | +40.48% | 49.54% | 12.04% |
| fixed_stop | +5.71% | +23.60% | +43.32% | 72.69% | 39.81% |
| profit_lock_after_gain | +5.44% | +19.96% | +31.83% | 96.30% | 46.06% |
| break_even_after_gain | +5.43% | +20.02% | +32.38% | 94.44% | 46.30% |
| ATR_trailing | +5.42% | +21.35% | +32.99% | 66.20% | 39.81% |
| no_exit | +5.41% | +19.89% | +31.57% | 100.00% | 49.54% |

更关键的是 robustness 上，按 net delta 排名，所有 active exit family 的 best net delta 都低于 hold120 no-exit baseline：

| exit family | robustness best net delta | robustness best p10 delta | robustness best bad compression | robustness best retention |
|---|---:|---:|---:|---:|
| no_exit | 0.00% | +12.41% | +15.71% | 97.23% |
| profit_lock_after_gain | -0.27% | +12.44% | +15.95% | 95.38% |
| break_even_after_gain | -0.64% | +12.56% | +16.27% | 93.54% |
| ATR_trailing | -0.83% | +13.39% | +16.37% | 67.69% |
| fixed_stop | -3.52% | +14.59% | +22.26% | 78.77% |
| time_stop | -3.65% | +13.91% | +21.27% | 44.00% |
| EMA_trailing | -5.40% | +15.67% | +28.91% | 27.08% |

因此 CTA / trailing 的真实结论是：它们能买到更强的左尾保护，但在右尾保留和跨 split 稳定性上没有胜过 break_even / profit_lock / no_exit 对照。特别是 EMA_trailing 的 validation best policy 只有 `11.11%` retention，time_stop 的 best policy 只有 `1.85%` retention，这类结果不应被解释为有效策略。

## 6. Q7: 改善来自降低左尾，还是来自砍掉右尾

selected policy 的改善主要来自降低左尾，而不是直接砍掉右尾。证据是：

| split | p10 delta | bad-path compression | retention | net delta |
|---|---:|---:|---:|---:|
| validation | +13.34% | +24.29% | 83.33% | +3.57% |
| robustness | +9.32% | +14.29% | 86.15% | -3.05% |

但这也暴露了更重要的问题：即使没有把 +50 winner 砍掉，exit policy 仍可能损害均值。原因可能是它提前退出了大量不会达到 +50%、但仍有中等正收益的路径，或者 market_state_scaled 降低了正收益年份的风险暴露。换句话说，`max_gain50_retention_vs_hold120 >= 60%` 是必要的防自欺约束，但不是保证正期望的充分条件。

## 7. Q8/Q9: market / industry subgroup 是否只是 interaction

interaction audit is not entry selection.

market / industry 字段没有进入 entry filter；它们只出现在 sizing 或 interaction audit 中。更重要的是，validation 和 robustness 的 interaction cell 大量存在年份集中问题，不能据此形成新的 gate。

| split | interaction cells | research_lead_eligible=true | eligible share | false share |
|---|---:|---:|---:|---:|
| train | 8,217 | 2,490 | 30.30% | 69.70% |
| validation | 8,466 | 0 | 0.00% | 100.00% |
| robustness | 8,466 | 0 | 0.00% | 100.00% |
| overall | 25,149 | 2,490 | 9.90% | 90.10% |

另外，`subgroup_denominator_status == insufficient_replay_complete` 的 cell 为 `10,707 / 25,149 = 42.57%`。这意味着 subgroup 表最多能提供 descriptive diagnostics，不能把少数 cell 写成稳定线索。

### downtrend_low_breadth

selected policy 在 downtrend_low_breadth 下的方向看起来还可以，但全部被 year concentration 挡住：

| split | replay count | net delta | bad-path compression | retention | top1 year share | eligible |
|---|---:|---:|---:|---:|---:|---|
| train | 173 | -1.69% | +10.40% | 92.16% | 66.47% | false |
| validation | 348 | +2.59% | +25.00% | 94.34% | 100.00% | false |
| robustness | 199 | +1.32% | +16.58% | 100.00% | 100.00% | false |

这个 cell 可以说明“下跌低宽度环境里 exit insurance 的 path protection 可能更明显”，但不能作为后续单独推广方向。validation / robustness 的 top1 year share 都是 `100%`，这不是稳健样本。

### industry_lagging

industry_lagging 更不能升级。validation 看起来好，但 robustness 均值大幅转负：

| split | replay count | net delta | bad-path compression | retention | top1 year share | eligible |
|---|---:|---:|---:|---:|---:|---|
| train | 642 | -0.54% | +19.00% | 88.79% | 40.19% | true |
| validation | 591 | +3.68% | +20.81% | 90.62% | 69.88% | false |
| robustness | 352 | -9.23% | +12.00% | 85.88% | 59.38% | false |

这组数据反而提示：industry_lagging 下 exit policy 的左尾保护存在，但机会成本也更大，尤其在 robustness 中不能抵消收益损失。

## 8. Denominator 与失败占比

winner denominator 没有不足问题：policy/split 层面的 `insufficient_winner_denominator` 占比为 `0.00%`。真正的问题是 retention gate 本身很难过：

| split | policy cells | retention passed | pass share | failed retention gate |
|---|---:|---:|---:|---:|
| train | 249 | 39 | 15.66% | 210 |
| validation | 249 | 42 | 16.87% | 207 |
| robustness | 249 | 39 | 15.66% | 210 |
| overall | 747 | 120 | 16.06% | 627 |

这说明大部分 aggressive exit / trailing policy 都是在用右尾换左尾，R04b 的 60% retention gate 有实际约束力。报告不能只展示 validation net delta 最好看的 EMA/time_stop cell。

## 9. Legacy metric 只作诊断

`+10 before -5` 在 R04b 中不是 primary metric，因为 exit policy 会主动制造或避免 -5 事件。selected policy 的 legacy 指标仍显示原始 RPS pool path 很差，但这些字段没有参与 final decision。

| split | legacy +10 before -5 | legacy bad path | legacy early failure | legacy race ambiguous |
|---|---:|---:|---:|---:|
| train | 38.04% | 64.65% | 51.95% | 0.05% |
| validation | 31.57% | 68.23% | 52.97% | 0.00% |
| robustness | 35.75% | 56.39% | 45.95% | 0.03% |

这些数值和 R04 的结论一致：RPS 更像右尾候选池，而不是自然入场点。R04b 的价值在于管理持有路径，不在于重新定义入场胜率。

## 10. 是否值得进入下一版 R04c

不建议把当前结果推进到更接近真实交易的候选流程。R04b 的结论还停留在 diagnostic complete：validation 找到了一个合理的 break-even + market_state_scaled policy，但 robustness 没有确认均值收益。

值得继续的方向只有一个：把 R04c 设计成“exit insurance 何时值得开启”的诊断，而不是继续扩大 CTA 参数网格。更具体地说：

- 保留 fixed-entry baseline_A 全池，不引入 mask_C 或 subgroup entry filter。
- 重点比较 `no_exit / break_even / profit_lock` 在不同 calendar regime 下的机会成本，而不是继续追逐 validation best net delta。
- CTA / EMA / time_stop 只能作为对照或 sensitivity，不应作为主线，因为它们在 validation 的好看结果大多来自右尾损失。
- market / industry 只能作为 interaction 或 sizing intensity，不得变成 selection pool。
- R04c 的 primary gate 应继续要求 retention、left-tail、net delta 同时成立；只改善坏路径但损害 robustness 均值，应判为失败。

本轮最重要的 insight 是：R04b 不是失败的实验，而是一个有效的否定结果。它证明了“RPS fixed-entry + exit management”确实能压缩左尾，但还没证明这种保险在好年份和差年份都值得付费。下一步如果继续研究，应该研究保险成本的状态依赖，而不是把 CTA 当成新的 alpha 来源。
