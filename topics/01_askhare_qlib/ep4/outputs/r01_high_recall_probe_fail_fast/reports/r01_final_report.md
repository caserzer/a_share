# EP4 R01 高召回 Probe / Fail-Fast 实验报告

- 实验阶段：`ep4_r01_high_recall_probe_fail_fast`
- 产物版本：`ep4_r01_high_recall_probe_fail_fast_v1`
- 生成时间：`2026-05-11T09:34:03+00:00`
- 配置文件：`ep4/configs/r01_high_recall_probe_fail_fast.yaml`
- 输出目录：`ep4/outputs/r01_high_recall_probe_fail_fast`
- 最终决策：`stop_ep4_r01_path`

本报告基于最新一轮 R01 结构化产物撰写，核心数据来自 `r01_run_manifest.json`、`r01_gate_audit.csv`、`r01_seed_density_audit.csv`、`r01_seed_recall_audit.csv`、`r01_recall_cost_tradeoff.csv`、`r01_baseline_diff_audit.csv`、`r01_random_baseline_health_audit.csv`、`r01_fail_fast_*_audit.csv` 和缓存面板。报告只解释实验结果，不引入新的模型、阈值选择或组合构造。

## 1. 结论摘要

R01 的最终结论是停止当前 EP4 R01 路径，不能进入 R02。

决策不是因为高召回目标完全失败。候选 `ep4_wide_seed_v0` 相比 EP2 bridge 确实捕获了更多 primary big winner，并且 fail-fast 对同种子 no-fail-fast 的损失控制有效；但是候选 seed 的日频密度严重超出冻结上限，同时 matched-random 对照在 validation split 无法达到可靠性要求。按照需求中冻结的 gate matrix，任意 hard gate 失败都必须 fail closed，因此最终只能给出 `stop_ep4_r01_path`。

关键事实：

| 项目 | 数值 |
|:--|--:|
| primary big-winner reference 总数 | 845 |
| candidate seed episode 总数 | 4,783 |
| EP2 bridge seed episode 总数 | 2,389 |
| gate 总数 | 28 |
| 通过 gate 数 | 24 |
| 失败 hard gate 数 | 4 |

失败的 4 个 hard gates：

| gate | split | 观测值 | 阈值 | 结论 |
|:--|:--|--:|--:|:--|
| `seed_density_day_cap` | train | 9.89% | 1.92% | 失败 |
| `seed_density_day_cap` | validation | 8.12% | 1.48% | 失败 |
| `seed_density_day_cap` | robustness | 11.42% | 1.96% | 失败 |
| `random_baseline_reliability_status` | validation | failed | passed | 失败 |

## 2. 实验边界和输入完整性

本轮实验保持 R01 要求中的 phase boundary：

- 不训练模型。
- 不从 validation/robustness 中选择阈值。
- 不做 add、仓位 sizing、组合层优化。
- 不把 ATR、state、trailing exit 作为决策逻辑。
- 不抓取外部数据。

输入 authority audit 全部通过。使用的关键本地输入包括：

| 输入 | 状态 |
|:--|:--|
| EP4 requirement / discussion | passed |
| EP2 engineering baseline manifest / config / launch pool | passed |
| EP2 label freeze / baseline freeze artifact | passed |
| Qlib PIT provider `data/qlib/cn_data_pit` | passed |
| PIT daily universe `pit_mcap500_mainboard_daily.csv` | passed |
| PIT industry membership | passed |
| trading calendar | passed |

这意味着本次失败不是由于缺少 authority input 或数据源漂移，而是实验结果本身触发了冻结 hard gates。

## 3. Big-Winner Reference Set

primary reference 使用 50% / 120 trading days 的 close-confirmed big winner 定义，并按有效窗口排除 forward horizon 不完整的事件。最新数据最大日期为 `2026-04-30`，扣除 120 日 forward horizon 后的有效 reference 截止为 `2025-10-31`。

| split | effective reference end | reference count | unique instruments | forward return p50 | 状态 |
|:--|:--|--:|--:|--:|:--|
| train | 2021-12-31 | 446 | 205 | 54.53% | passed |
| validation | 2023-12-31 | 158 | 127 | 52.93% | passed |
| robustness | 2025-10-31 | 241 | 170 | 53.57% | passed |

reference set 的规模足够支撑本轮 recall audit。robustness 的 effective end 被正确收紧到 `2025-10-31`，避免把 forward window 尚未完整的后验 big winner 放入 primary recall gate。

## 4. Seed 生成和密度问题

候选 `ep4_wide_seed_v0` 的目标是提高 big-winner 捕获率，因此它比 EP2 launch detector 明显更宽。但最新结果显示，宽化程度已经超过 R01 对“可执行 probe 密度”的硬约束。

| split | family | eligible stock-days | executable seed-days | seed episodes | seed-day rate | seed episodes / instrument-year |
|:--|:--|--:|--:|--:|--:|--:|
| train | EP4 candidate | 179,135 | 17,708 | 2,287 | 9.89% | 3.27 |
| train | EP2 bridge | 179,135 | 1,149 | 1,149 | 0.64% | 1.64 |
| validation | EP4 candidate | 107,845 | 8,754 | 1,131 | 8.12% | 2.52 |
| validation | EP2 bridge | 107,845 | 532 | 532 | 0.49% | 1.19 |
| robustness | EP4 candidate | 108,406 | 12,383 | 1,365 | 11.42% | 3.12 |
| robustness | EP2 bridge | 108,406 | 708 | 708 | 0.65% | 1.62 |

相对 EP2，candidate 的 seed-day density 放大非常明显：

| split | seed-day rate vs EP2 | episode rate vs EP2 |
|:--|--:|--:|
| train | 15.41x | 1.99x |
| validation | 16.45x | 2.13x |
| robustness | 17.49x | 1.93x |

密度上限利用率也显示同一问题：

| split | candidate seed-day rate | seed-day cap | cap utilization | episode cap utilization |
|:--|--:|--:|--:|--:|
| train | 9.89% | 1.92% | 5.14x | 0.66x |
| validation | 8.12% | 1.48% | 5.48x | 0.71x |
| robustness | 11.42% | 1.96% | 5.83x | 0.64x |

发现：

- episode 级密度没有超 cap，但 seed-day 级密度在三个 split 都超过 cap 5 倍以上。
- 这说明 20 日 episode dedup 把大量密集信号压缩成 episode 后看起来可控，但真实执行层面的 daily probe 候选过多。
- R01 的 density gate 是为了防止“召回率靠撒网密度换来”。从当前结果看，candidate 确实存在这个问题。
- candidate 的 next-open buy executable rate 只有 43% 到 53%，明显低于 EP2 bridge 的 91% 到 99%。这进一步说明宽 seed 在执行层面质量偏低。

## 5. Big-Winner Recall

candidate 的 primary recall 明显高于 EP2 bridge。

| split | family | reference count | captured | missed | recall | recall diff vs EP2 |
|:--|:--|--:|--:|--:|--:|--:|
| train | EP4 candidate | 446 | 73 | 373 | 16.37% | +8.30pp |
| train | EP2 bridge | 446 | 36 | 410 | 8.07% | 0.00pp |
| validation | EP4 candidate | 158 | 15 | 143 | 9.49% | +7.59pp |
| validation | EP2 bridge | 158 | 3 | 155 | 1.90% | 0.00pp |
| robustness | EP4 candidate | 241 | 44 | 197 | 18.26% | +12.03pp |
| robustness | EP2 bridge | 241 | 15 | 226 | 6.22% | 0.00pp |

发现：

- candidate 在 validation 和 robustness 上均通过 `primary_recall_no_harm`，没有低于 EP2。
- recall 提升是真实存在的，不是只发生在 train。
- 但绝对 recall 仍然不高：validation 只捕获 15 / 158，robustness 捕获 44 / 241。
- recall 提升的主要代价是 seed-day 密度暴增，而不是一个干净的结构性识别能力提升。

## 6. Fail-Fast 行为和损失控制

candidate probe simulation 的表现如下：

| split | episodes | mean R | p05 R | median R | p95 R | primary failed rate | fail-fast trigger rate | median holding days |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 1,088 | -0.038 | -0.739 | -0.273 | 1.485 | 93.29% | 58.09% | 8 |
| validation | 416 | -0.142 | -0.627 | -0.314 | 0.911 | 96.39% | 60.82% | 7 |
| robustness | 567 | -0.004 | -0.651 | -0.266 | 1.489 | 83.95% | 58.91% | 8 |

主要 exit trigger：

| split | below breakout ref | below seed-day low | both seed low and breakout ref | natural H20 |
|:--|--:|--:|--:|--:|
| train | 409 | 45 | 175 | 456 |
| validation | 171 | 12 | 70 | 163 |
| robustness | 204 | 46 | 84 | 233 |

对 same-seed no-fail-fast H20 的 validation gate 全部通过：

| metric | candidate | no-fail-fast baseline | diff | gate |
|:--|--:|--:|--:|:--|
| mean return R | -0.142 | -0.193 | +0.051 | report |
| p05 return R | -0.627 | -1.381 | +0.754 | passed |
| failed seed average loss R | 0.285 | 0.410 | -0.125 | passed |
| failed seed median holding days | 7 | 22 | -15 | passed |

发现：

- fail-fast 对控制左尾和缩短失败持有期是有效的。
- validation 中 p05 R 从 -1.381 改善到 -0.627，失败平均损失从 0.410R 降到 0.285R。
- 但 fail-fast 只能改善“进入之后的失败处理”，不能解决“进入候选太多”的密度问题。
- candidate 的 median R 在三个 split 都为负，说明大多数 probe 本身不是好交易，只是用小损失换少数 winner 的上行可能。

## 7. 与 EP2 Bridge 的对比

validation split 中，candidate 相比 EP2 `probe_with_simple_stop` bridge 的表现：

| metric | candidate | EP2 bridge | diff |
|:--|--:|--:|--:|
| mean return R | -0.142 | -0.068 | -0.074 |
| p05 return R | -0.627 | -0.870 | +0.243 |
| failed seed average loss R | 0.285 | 0.257 | +0.028 |
| failed seed median holding days | 7 | 12 | -5 |

解释：

- candidate 的左尾好于 EP2 bridge，说明 structural fail-fast 有一定保护作用。
- candidate 的平均 R 比 EP2 bridge 更差，说明更宽 seed 池引入了大量低质量事件。
- failed seed average loss R 比 EP2 bridge 略高，说明虽然退出更快，但更宽入口带来的坏交易数量和结构仍然更重。
- 这不是一个“用 fail-fast 完整替代 entry quality”的成功案例。

## 8. Recall-Cost Tradeoff

R01 的 recall-cost audit 通过，但它不能覆盖 density hard gate 的失败。

| split | candidate failed loss R | EP2 failed loss R | incremental loss R | added captures | lost captures | net added captures | loss R / added winner | exposure days / added winner | status |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| train | 285.12 | 177.40 | 107.72 | 98 | 25 | 73 | 1.48 | 62.73 | passed |
| validation | 114.29 | 86.46 | 27.82 | 25 | 3 | 22 | 1.26 | 50.09 | passed |
| robustness | 127.04 | 101.33 | 25.71 | 63 | 11 | 52 | 0.49 | 26.69 | passed |

发现：

- 每新增一个 big winner 的增量失败损失在 validation 是 1.26R，低于 5R 上限。
- 每新增一个 big winner 的增量 exposure 在 validation 是 50.09 天，低于 250 天上限。
- 这个结果说明“高召回 + fail-fast”在单位 winner 成本上并非不可接受。
- 但 recall-cost pass 的前提是已经允许这么高的 seed-day 密度；而 density gate 明确不允许。

因此，R01 的核心矛盾是：candidate 在捕获更多 winner 和单位 recall cost 上有正面证据，但它主要靠过宽的 daily seed coverage 达成，违反了可执行密度约束。

## 9. Matched-Delay Baseline

matched-delay baseline 的 reliability gate 通过。

| split | delay | candidate rows | ineligible rows | ineligible rate | status |
|:--|--:|--:|--:|--:|:--|
| train | 1d | 2,176 | 688 | 31.62% | passed |
| train | 3d | 2,176 | 748 | 34.38% | passed |
| validation | 1d | 832 | 220 | 26.44% | passed |
| validation | 3d | 832 | 236 | 28.37% | passed |
| robustness | 1d | 1,134 | 378 | 33.33% | passed |
| robustness | 3d | 1,134 | 480 | 42.33% | passed |

validation 中 same-fail-fast matched-delay 结果：

| baseline | mean return diff | p05 return diff | failed avg loss diff | median holding diff |
|:--|--:|--:|--:|--:|
| delay 1d same fail-fast | +0.0025 | +0.0273 | +0.0126 | -3 |
| delay 3d same fail-fast | +0.0223 | -0.0028 | +0.0442 | -1 |

发现：

- delay 1d / 3d 没有明显推翻 candidate 的 timing 价值。
- 但 delay baseline 的解释力有限，因为它仍然继承 candidate 的原始 structural reference。
- matched-delay 通过只能说明“不是简单延迟一点就明显更好”，不能说明 seed density 合理。

## 10. Matched-Random Baseline 健康度

matched-random 是本轮失败的第二个关键原因。它按 train-frozen industry / liquidity / volatility bucket 做 same-density random controls，100 个 no-replacement replicates。

| split | baseline | buckets | min eligible rate | median eligible rate | mean eligible rate | shortfall buckets | replicates | status |
|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| train | no fail-fast H20 | 377 | 0.00 | 37.67% | 37.67% | 4 | 100 | failed |
| train | same fail-fast H20 | 377 | 0.00 | 37.67% | 37.72% | 4 | 100 | failed |
| validation | no fail-fast H20 | 239 | 0.00 | 29.00% | 29.83% | 4 | 100 | failed |
| validation | same fail-fast H20 | 239 | 0.00 | 29.00% | 29.84% | 4 | 100 | failed |
| robustness | no fail-fast H20 | 251 | 0.00 | 26.00% | 26.59% | 2 | 100 | failed |
| robustness | same fail-fast H20 | 251 | 0.00 | 26.00% | 26.62% | 2 | 100 | failed |

发现：

- 每个 split 都存在 eligible rate 为 0 的 bucket。
- validation split 的 random baseline reliability hard gate 失败，因此不能把 random controls 作为可靠反事实证据使用。
- shortfall bucket 数量不多，但 gate 是 fail-closed：只要关键 bucket 无法构造可靠对照，就不能用随机对照支持进入 R02。
- 这也暴露了 candidate 的部分信号落在非常稀疏或结构特殊的 bucket 中，随机同密度对照难以稳定复现。

## 11. Label A Bridge 和失败路径

Label bridge 是 audit-only，不参与阈值选择。它用于观察 candidate seeds 在 EP2 风格 label 下的质量分布。

| split | label | rows | positive rate | same-day ambiguous |
|:--|:--|--:|--:|--:|
| train | H10 U1.5 D1.0 | 1,088 | 43.20% | 24 |
| train | H20 U2.0 D1.0 | 1,088 | 36.86% | 19 |
| validation | H10 U1.5 D1.0 | 416 | 37.02% | 3 |
| validation | H20 U2.0 D1.0 | 416 | 30.05% | 2 |
| robustness | H10 U1.5 D1.0 | 567 | 39.51% | 20 |
| robustness | H20 U2.0 D1.0 | 567 | 35.10% | 10 |

fail-fast error audit：

| split | error type | count | avg loss R | p95 loss R | avg H20 return |
|:--|:--|--:|--:|--:|--:|
| train | false reject winner | 26 | 0.527 | 0.791 | -0.047 |
| train | missed failure | 158 | 0.363 | 0.963 | -0.062 |
| validation | false reject winner | 10 | 0.439 | 0.743 | -0.071 |
| validation | missed failure | 82 | 0.351 | 0.856 | -0.060 |
| robustness | false reject winner | 17 | 0.383 | 0.615 | 0.052 |
| robustness | missed failure | 62 | 0.281 | 0.676 | -0.047 |

发现：

- validation 的 H20 U2.0 D1.0 positive rate 只有 30.05%，说明候选 episode 大部分并不具备强短期收益质量。
- missed failure 数量明显多于 false reject winner，说明 fail-fast 规则仍然漏掉相当多坏路径。
- false reject winner 数量较少但不可忽略，尤其 train 和 validation 中其平均 loss R 不低。
- 当前 fail-fast 是有效的成本控制工具，但还不是足以支撑宽入口的完整质量过滤器。

## 12. R-Unit 和风险距离分布

以主 probe budget 0.25R 观察：

| split | population | initial risk p05 | initial risk median | initial risk p95 | return R p01 | return R p99 | failed avg loss R |
|:--|:--|--:|--:|--:|--:|--:|--:|
| train | candidate | 2.12% | 3.69% | 8.75% | -1.14 | 3.11 | 0.278 |
| train | EP2 bridge | 2.20% | 4.10% | 8.81% | -1.33 | 2.31 | 0.237 |
| validation | candidate | 2.10% | 3.74% | 8.65% | -0.96 | 2.41 | 0.285 |
| validation | EP2 bridge | 2.13% | 3.68% | 7.96% | -1.02 | 2.32 | 0.259 |
| robustness | candidate | 2.12% | 3.81% | 8.81% | -0.90 | 2.73 | 0.256 |
| robustness | EP2 bridge | 2.15% | 4.08% | 9.28% | -1.00 | 1.88 | 0.252 |

发现：

- candidate 的 initial risk pct 分布与 EP2 bridge 接近，不是因为单笔 risk distance 特别异常导致失败。
- validation 中 candidate 的 failed avg loss R 高于 EP2 bridge，说明问题更多来自 seed pool 质量和密度，而不是单纯 R-unit 归一化错误。
- candidate 的 p99 return R 高于 EP2 bridge，说明它确实保留了一部分右尾 winner；但 median return R 为负，右尾不足以覆盖宽入口带来的大量普通失败。

## 13. Gate Matrix 解释

通过的 hard gates 说明：

- authority inputs 完整。
- validation 没有被用于阈值选择。
- denominator 非零。
- validation unique instrument-year 足够。
- primary recall 不弱于 EP2。
- fail-fast 相比 same-seed no-fail-fast 改善了 validation 的损失和持有期。
- matched-delay reliability 通过。
- recall-cost tradeoff 在 validation 和 robustness 上没有超出冻结成本边界。

失败的 hard gates 决定最终结论：

| gate | 原因 |
|:--|:--|
| train `seed_density_day_cap` | candidate seed-day rate 是 cap 的 5.14 倍 |
| validation `seed_density_day_cap` | candidate seed-day rate 是 cap 的 5.48 倍 |
| robustness `seed_density_day_cap` | candidate seed-day rate 是 cap 的 5.83 倍 |
| validation `random_baseline_reliability_status` | matched-random exact-bucket controls 不可靠 |

按照 R01 冻结决策矩阵，当前不满足 `go_to_r02` 或 `go_to_r02_with_robustness_warning` 的必要条件，也不能归档为单纯 cost-control sleeve，因为 density 和 random reliability 是硬失败。因此唯一允许的决策是：

`stop_ep4_r01_path`

## 14. 研究含义

本轮实验给出的是一个混合信号：

正面证据：

- 高召回 seed 确实比 EP2 bridge 多捕获 big winner。
- fail-fast 对同种子 no-fail-fast 的左尾和持有期改善明显。
- recall-cost tradeoff 在冻结阈值下通过。
- robustness split 中 recall 提升和 unit recall cost 仍然成立。

负面证据：

- candidate 的 daily seed density 远超可执行上限，且三个 split 一致失败。
- 高 recall 更像是由大范围撒网产生，而不是由干净的可执行入口产生。
- validation median R 为 -0.314，primary failed rate 达 96.39%，说明普通 probe 质量很弱。
- matched-random 对照不能可靠构造，削弱了“candidate 显著优于同密度随机入口”的证据。
- fail-fast 可以止损，但不能让一个过宽 seed family 自动变成可进入下一阶段的策略入口。

## 15. 后续建议

在当前 requirement 下，不应启动 R02。若要继续研究，应新开 requirement，而不是在 R01 内继续调参。

更合理的后续方向：

1. 先研究 seed density 的来源，把 daily seed-day rate 降到冻结 cap 附近，再重新评估 recall。
2. 对 wide seed 做结构分解，找出贡献大部分 recall 的 price / money / liquidity / volatility 子条件，避免无差别扩宽。
3. 单独分析 matched-random 失败 bucket，确认是样本稀缺、行业结构特殊，还是候选信号集中在不可替代的状态。
4. 如果继续做 cost-control sleeve，也应先定义新的 sleeve requirement，因为当前 R01 的 gate matrix 不允许在 hard gate 失败后直接 handoff。

## 16. 产物索引

关键报告：

- `reports/r01_gate_audit.csv`
- `reports/r01_seed_density_audit.csv`
- `reports/r01_seed_recall_audit.csv`
- `reports/r01_recall_cost_tradeoff.csv`
- `reports/r01_baseline_diff_audit.csv`
- `reports/r01_random_baseline_health_audit.csv`
- `reports/r01_fail_fast_path_audit.csv`
- `reports/r01_fail_fast_error_audit.csv`
- `reports/r01_r_unit_distribution_audit.csv`

关键缓存：

- `cache/r01_big_winner_reference_panel.parquet`
- `cache/r01_seed_episode_panel.parquet`
- `cache/r01_probe_simulation_panel.parquet`
- `cache/r01_baseline_simulation_panel.parquet`

运行 manifest：

- `manifests/r01_run_manifest.json`

## 17. R02 Handoff

R02 只能在 R01 决策为 `go_to_r02` 或 `go_to_r02_with_robustness_warning` 时使用 surviving episodes。当前决策为 `stop_ep4_r01_path`，因此 R02 不应启动；如需继续，必须新建 requirement，并明确是否要重新定义 seed-density 目标、random-control 可靠性标准和 cost-control sleeve 边界。
