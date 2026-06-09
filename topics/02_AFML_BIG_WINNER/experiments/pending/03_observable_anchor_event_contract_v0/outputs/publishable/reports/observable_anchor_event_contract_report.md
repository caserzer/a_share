# 可观测锚点事件合约 V0 报告

最终决策：`event_contract_sample_blocked`

## 核心结论

本实验把 02 的反向生命周期画像改写为一个可观测事件合约：`first_ema60_reclaim -> rank jump -> rank persistence`，事件在 `rank_persistence` 完成日收盘确认，次一可成交开盘评估标签。结果显示，E_S3 在若干读数上确实能提高 `confirm_20` 触上界概率，但它没有通过合同授权门槛，不能升级为 universal entry。

失败不是因为事件数不够，也不是因为可执行性差。真正的阻塞点是 `baseline_false_repair_excluded` 的匹配覆盖率不足：全样本覆盖率只有 `63.5%`，validation 覆盖率只有 `54.8%`，均低于合同门槛。这意味着在“同样剔除 as-of false-repair”的干净基线池里，可比对照不够稳定，当前样本无法干净证明 `rank persistence` 有独立增量。

更重要的是，即使只看已匹配样本，E_S3 的前向优势也不是干净的收益优势：相对 `baseline_false_repair_excluded`，`confirm_20` lift 为 `1.44`，但 `failure_10` 失败率也高出 `6.9pct`，20 日平均收益只高 `0.49pct`，且 robustness 段 20 日收益差为负。这个组合更像“修复后波动和上行触达概率同时升高”，而不是可直接交易的稳定正收益事件。

## 实验合约与复现信息

- 主事件：`E_S3`，EMA60 reclaim 后出现 20 日相对强度跳升，并在后续 20 个交易日满足 persistence coverage。
- t0：`rank_persistence` 被确认的收盘日。
- 执行价：t0 后次一可成交开盘价，日频 OHLCV 只能做保守可成交 proxy。
- 主 headline：`E_S3_all` vs `baseline_false_repair_excluded`，`confirm_20`，unconditional universal readout。
- secondary / diagnostic：`baseline_raw`、`failure_10`、regime-conditioned、`E_S3 ∩ G_S2`、near-winner、C_S6、60d 连续读数。
- 行业数据状态：v0 为 `unavailable`。rank persistence 只使用 `stock_vs_market_20d`，不能排除行业 beta。
- source git revision：`db22957d6ea5120e47452b343974f375a4f3dd73`
- upstream reverse lifecycle decision：`reverse_lifecycle_sequence_supported_universal_dominance`
- upstream manifest hash：`8f67723cbfb0716d5b3d633a290cf3aab387dc9f94a048bc0b5e4d0f492081d3`

## Gate Replay

| gate / metric | value | contract threshold | status |
|:--|--:|--:|:--|
| total_event_count | 1561 | >= 120 | pass |
| validation_event_count | 529 | >= 30 | pass |
| robustness_event_count | 601 | >= 30 | pass |
| executable_rate | 99.94% | >= 80% | pass |
| event_label_complete_rate | 99.94% | >= 70% | pass |
| baseline_match_coverage, excluded family | 63.53% | >= 80% | fail |
| validation_baseline_match_coverage, excluded family | 54.82% | >= 70% | fail |
| robustness_baseline_match_coverage, excluded family | 74.79% | >= 70% | pass |

blocked reasons：

```text
min_baseline_match_coverage
min_validation_baseline_match_coverage
```

解释：样本门阻塞来自 headline 所用的 `baseline_false_repair_excluded` family。`baseline_raw` 的覆盖率较高，不能替代 excluded family，因为 raw baseline 保留了 as-of false-repair，会把“剔除假修复”与“rank persistence 独立增量”混在一起。

## Headline Readout

| comparison | coverage | event confirm20 | baseline confirm20 | lift | confirm diff | failure10 diff | forward20 diff |
|:--|--:|--:|--:|--:|--:|--:|--:|
| E_S3 vs baseline_false_repair_excluded | 63.53% | 23.97% | 16.63% | 1.44 | +7.34pct | +6.90pct | +0.49pct |
| E_S3 vs baseline_raw | 80.68% | 23.49% | 20.95% | 1.12 | +2.55pct | +2.58pct | +0.12pct |

读法：

- 相对 clean baseline，E_S3 的 `confirm_20` 优势更明显，但这是在低覆盖样本上得到的。
- `failure_10_diff` 为正，说明 E_S3 不是单纯降低失败概率的信号。它提高了上行触达概率，也提高了短期失败暴露。
- `forward20 diff` 很小，说明 barrier 的“触达上界”没有稳定转化为 20 日均值收益优势。
- 因为 headline family 的 coverage gate 未过，本实验不能宣称 `rank persistence` 独立有效。

## Split 稳定性

| baseline family | split | coverage | confirm20 lift | confirm diff | failure10 diff | forward20 diff |
|:--|:--|--:|--:|--:|--:|--:|
| baseline_false_repair_excluded | train | 58.47% | 2.03 | +12.86pct | +7.29pct | +3.06pct |
| baseline_false_repair_excluded | validation | 54.82% | 2.03 | +9.25pct | +4.40pct | +0.52pct |
| baseline_false_repair_excluded | robustness | 74.79% | 1.19 | +4.26pct | +7.59pct | -0.63pct |
| baseline_raw | train | 70.07% | 1.31 | +6.32pct | +3.41pct | +2.62pct |
| baseline_raw | validation | 79.96% | 0.94 | -1.09pct | -1.47pct | -0.69pct |
| baseline_raw | robustness | 88.89% | 1.15 | +3.69pct | +4.79pct | -0.44pct |

关键发现：

- validation 是固定负 beta 压力窗。clean baseline 下 validation 的 `confirm20 lift` 很高，但 coverage 只有 `54.8%`，不能作为稳健支持。
- robustness 段 clean baseline coverage 达标，但 `forward20 diff = -0.63pct`，且 `failure10 diff = +7.59pct`。这否定了“全周期稳定 forward-return edge”的说法。
- raw baseline 在 validation 段 lift 小于 1，forward20 为负。若不做 false-repair 归因分解，会得到互相冲突的结论。
- 三段都无法形成稳定的正向收益差，因此 `split_stability = not_stable_or_sample_blocked` 是合理结论。

## False-Repair 归因

| item | count / value |
|:--|--:|
| E_S3 candidates before false-repair exclusion | 1771 |
| event_invalidated_false_repair_count | 204 |
| candidates after false-repair exclusion | 1567 |
| final canonical E_S3 events | 1563 |
| baseline_raw rows used in attribution | 4440 |
| baseline_raw as-of false-repair count | 458 |
| baseline_false_repair_excluded rows used in attribution | 3283 |

归因读法：

- E_S3 自身确实排除了 t0 当时已经失败的修复路径，约 `11.5%` 的候选被剔除。
- raw baseline 中仍有 `458` 条 as-of false-repair。与 raw baseline 比较时，edge 会部分来自“事件端剔除了假修复，而基线端保留假修复”。
- excluded baseline 去掉这部分污染后，`confirm20 lift` 从 `1.12` 升到 `1.44`，但覆盖率降到 `63.5%`，failure10 差也扩大到 `+6.9pct`。
- 这说明 false-repair 处理不是一个小技术细节，而是决定归因质量的主变量。当前结果不能把 edge 直接归功于 rank persistence。

## Baseline Timing 诊断

| baseline family | t0 policy | count | median reclaim -> t0 | confirm20 rate | failure10 rate | forward20 mean | main claim |
|:--|:--|--:|--:|--:|--:|--:|:--|
| baseline_raw | observed_failure_decision_date | 1296 | 30d | 21.79% | 12.29% | +0.42% | yes |
| baseline_false_repair_excluded | observed_failure_decision_date | 838 | 30d | 18.40% | 8.48% | +0.16% | yes |
| baseline_raw | deterministic_max_horizon | 1282 | 60d | 20.05% | 9.28% | +0.37% | no |
| baseline_false_repair_excluded | deterministic_max_horizon | 644 | 59d | 18.01% | 6.21% | +0.59% | no |

洞察：

- 主口径使用 observed-failure t0 是正确的，因为它是 close-observed 的失败判定日，不用合成平均 offset。
- deterministic-offset 诊断显示，若把 baseline 统一推迟到最大观察窗口附近，baseline 的失败率会下降，forward20 会略好。这会压缩 E_S3 的净优势。
- 因此 E_S3 的结论对 baseline t0 有敏感性。当前不能跳过 timing audit 直接说“站回均线后 persistence 一定有效”。

## Regime 读数

headline family：`baseline_false_repair_excluded`，split：`all`。

| regime | event_count | coverage | confirm20 lift | confirm diff | failure10 diff | forward20 diff |
|:--|--:|--:|--:|--:|--:|--:|
| risk_off | 375 | 35.73% | 0.81 | -2.88pct | +11.34pct | -1.37pct |
| risk_on | 728 | 83.79% | 1.45 | +8.62pct | +8.58pct | +0.13pct |
| transition | 460 | 54.13% | 2.70 | +12.90pct | +2.21pct | +2.43pct |

洞察：

- `risk_off` 明确不支持：coverage 低、lift 小于 1、failure10 高、forward20 为负。
- `risk_on` 覆盖率可用，confirm20 有优势，但 forward20 几乎不动，failure10 高出 `8.58pct`。它更像高波动确认，而不是净收益信号。
- `transition` 的读数最好，但 coverage 只有 `54.1%`，不能作为 regime-conditional 授权依据。
- 如果后续继续研究，`risk_off` 应当作为硬排除或单独建模对象，而不是与 risk_on / transition 混在 universal contract 里。

## G_S2 弱过滤门

`G_S2` 通过事件数为 `780`，约占最终 E_S3 的 `49.9%`。

| split | event_count | coverage | confirm20 lift | failure10 diff | forward20 diff |
|:--|--:|--:|--:|--:|--:|
| all | 780 | 64.87% | 1.48 | +7.79pct | +0.34pct |
| train | 238 | 60.92% | 2.20 | +7.64pct | +2.68pct |
| validation | 252 | 56.75% | 2.04 | +5.53pct | +0.21pct |
| robustness | 290 | 75.17% | 1.17 | +8.53pct | -0.85pct |

洞察：

- G_S2 不能救主结论。它略微提高 all-split lift，但没有改善 coverage gate，也没有降低 failure10。
- robustness 段 `forward20 diff` 仍为负，说明“金额/VWAP 承接”更像修复质量标签，不足以变成稳定 entry 条件。
- 因此 G_S2 应继续保持 weak filter / diagnostic，不应升级为硬入场门。

## C_S6 与口径转换

| split | event_count | 02 axis-low reference pass | 03 reclaim-close contract pass | delta |
|:--|--:|--:|--:|--:|
| all | 1563 | 45.81% | 37.62% | -8.19pct |
| train | 431 | 51.74% | 41.53% | -10.21pct |
| validation | 529 | 34.40% | 28.54% | -5.86pct |
| robustness | 603 | 51.58% | 42.79% | -8.79pct |

03 的 C_S6 使用 reclaim close 作为 +20% 基准，而不是 02 的 retrospective axis low。这个转换让通过率下降约 `8.2pct`，平均确认延迟约 `12.3` 天。C_S6 的语义是“已经明显走出来之后的继续确认”，天然滞后，不适合作为主事件。

## Near-Winner 诊断

near-winner 使用未来 120 日 MFE，明确是 profile-only future outcome control，不进入阈值选择、baseline 匹配或 gate。

| split | event_count | near_winner_count | near_winner confirm20 rate | near_winner forward20 mean |
|:--|--:|--:|--:|--:|
| all | 1563 | 180 | 36.11% | +3.95% |
| train | 431 | 61 | 34.43% | +4.05% |
| validation | 529 | 51 | 29.41% | +1.81% |
| robustness | 603 | 68 | 42.65% | +5.47% |

洞察：

- 当 E_S3 事件后验落入 near-winner 强路径时，短期表现明显更好。
- 但 near-winner 本身用未来 120 日 MFE 定义，不能被当成 t0 可用信号。
- 这组读数说明真正有价值的可能不是“reclaim 后 persistence”本身，而是 persistence 之后能否继续形成更高阶路径质量。这个问题需要新的、t0 可观测的 continuation discriminator，而不是直接复用 future MFE。

## 执行性与 60d Censoring

| metric | value |
|:--|--:|
| executable denominator | 1563 |
| executable numerator | 1562 |
| non_executable_next_open | 1 |
| limit_rule_unavailable_count | 0 |
| executable_rate | 99.94% |
| main_label_complete_rate | 99.94% |

执行性不是本实验失败原因。日频保守可成交 proxy 下，只有 1 条事件不可执行。

60d 连续读数：

| split | rows | complete | censored | forward60 mean | forward60 median |
|:--|--:|--:|--:|--:|--:|
| train | 431 | 431 | 0 | +0.76% | -1.68% |
| validation | 529 | 529 | 0 | -3.78% | -4.13% |
| robustness | 603 | 543 | 60 | +6.39% | +0.24% |
| all | 1563 | 1503 | 60 | +1.20% | -2.09% |

洞察：

- 60d 读数与 20d/10d 主标签分开 censor 是必要的。robustness 近端存在 60 条 `censored_incomplete_horizon`，不能静默进入 60d 均值。
- validation 的 60d 均值为 `-3.78%`，说明负 beta 压力窗下事件后续并不稳定。
- robustness 的 60d 均值为正，但有右截断，且 20d edge 相对 baseline 已经为负，不能用 60d 后验表现覆盖 headline 失败。

## 事件分布与样本结构

| dimension | count |
|:--|--:|
| train events | 431 |
| validation events | 529 |
| robustness events | 603 |
| risk_on events | 728 |
| transition events | 460 |
| risk_off events | 375 |
| G_S2 passed | 780 |
| C_S6 confirmed | 588 |
| near_winner profile-only | 180 |

事件按年份分布：

| year | events |
|:--|--:|
| 2018 | 88 |
| 2019 | 68 |
| 2020 | 75 |
| 2021 | 200 |
| 2022 | 295 |
| 2023 | 234 |
| 2024 | 251 |
| 2025 | 237 |
| 2026 | 115 |

样本结构比较均衡，主要问题不是事件不足，而是 clean baseline 的可比对照不足。尤其 validation 和 risk_off 的 coverage 太低，导致结论无法授权。

## 解释性洞察

1. E_S3 是一个“确认指标”，不是充分的领先入场指标。它在 t0 已经要求 reclaim、rank jump 和 persistence 完成，因此天然处在修复之后。结果中的 confirm20 lift 表明它确实捕捉到一部分后续上行触达概率，但 failure10 同时升高，说明它捕捉的也是波动扩张和路径分化。

2. 当前最强证据不是“rank persistence 稳定赚钱”，而是“false-repair 排除非常重要”。只要 baseline 是否保留 false-repair 发生变化，lift、coverage、failure 差都会明显变化。因此下一阶段若继续做事件合约，应优先把 false-repair / low-energy repair 的可观测判别做扎实，而不是继续堆 persistence 条件。

3. 负 beta 压力窗没有给出支持。validation 中 raw baseline 的 lift 小于 1，clean baseline 虽 lift 高但 coverage 不足，且事件自身 20d/60d 表现为负。任何 universal entry 结论都必须被 validation 否决。

4. risk_off 应当被单独处理。risk_off 下 clean baseline coverage 只有 `35.7%`，confirm lift 低于 1，failure10 高出 `11.3pct`。在弱市场中，站回 EMA60 后的 persistence 更可能是反弹噪声或高波动修复，而非可靠趋势延续。

5. 如果要继续推进，方向应是“事件后质量二次判别”，不是直接授权 E_S3。near-winner 与 C_S6 都提示，真正好的路径会在 E_S3 后继续表现出质量差异；但 near-winner 用未来 outcome，C_S6 又太滞后。下一版需要寻找 t0 或 t0+少量天数可观测的 continuation proxy，例如更严格的承接、低失败回撤、相对强度不降、放量不滞涨等。

## 最终判断

本实验达成了一个有价值的负结果：把 02 的反向生命周期画像改写成可观测 E_S3 合约后，主事件没有通过 universal edge 授权。它可以作为画像诊断和后续特征工程的候选，但不能直接进入策略、组合或回测阶段。

当前正确结论是：

```text
event_contract_sample_blocked
```

不授权下一阶段交易化。若继续研究，应优先解决三个问题：

- 提高 `baseline_false_repair_excluded` 的可比覆盖率，特别是 validation 与 risk_off。
- 把 false-repair / insufficient-runup 的 t0 可观测判别做成独立候选事件或过滤门。
- 为 E_S3 后续路径质量寻找非后验、低滞后的 continuation discriminator。

## 主要产物

- `event_instances.csv`
- `event_label_outcomes.csv`
- `event_vs_baseline_forward_stats.csv`
- `baseline_false_repair_attribution_audit.csv`
- `baseline_t0_timing_audit.csv`
- `false_repair_exclusion_audit.csv`
- `executability_audit.csv`
- `event_vs_near_winner_forward_stats.csv`
- `s6_basis_transform_audit.csv`
- `run_manifest.json`
