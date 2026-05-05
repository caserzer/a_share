# Explore9 P0.5 扩展探索详细报告：Expand 1

> 本报告为基于 `Explore9/outputs/reports/p0_5_*.csv` 的人工详细解读。
> 本次只更新 markdown 报告，不修改 `run_explore9.py`、配置文件或报告生成器。
> 后续如果再次运行 `report-p0-5`，本手工报告可能被生成器覆盖。

## 1. 核心结论

P0.5 完成了需求中要求的扩展覆盖，但没有找到可以直接升级为 P1 early-entry 主假设的稳定 lead。

- `explore9_p0_5_minimum_coverage_met = true`。
- `recommendation = continue_p0_broad_discovery`。
- P0.5 启用原语 `125` 个，其中新增 `70` 个。
- P0.5 诊断组合 `43` 个，其中高波动 `11` 个、修复初期 `9` 个、rank jump `8` 个、成交质量 `9` 个、sparse strong-day `6` 个。
- early-entry、confirmation、hold/exit 三张榜均已生成；但 `qualified lead = 0`。
- 所有主榜 lift 的最终 lead set 均排除了 `label_horizon_truncated = true` 和 `observed_reference_overlap = true`，对应输出中的两项 rate 均为 `0`。

最重要的发现不是“没有任何信号”，而是：

```text
很多结构在 stock-day 和 dedup trigger-event 口径下有明显 lift，
但一旦切到 instrument-year 口径，就全部低于 baseline。
```

这说明当前 P0.5 线索更像 winner path 中的局部状态、确认片段或持有解释变量，而不是可以稳定扩大到“年度候选股票筛选”的 early-entry 结构。

因此，P0.5 的有效结论是负向但有价值的：

- 不应把 P0 中的高波动、强趋势、post-30、late acceleration 线索误写成初始买点。
- 高波动、放量保持、强势日等结构确实解释了 winner 路径，但它们更偏 confirmation / continuation / hold tolerance。
- early-entry discovery 仍需继续做 broad discovery，尤其需要从单日/简单二变量状态转向更长序列、事件顺序和更低重复计数的结构。

## 2. 覆盖与审计结果

P0.5 的覆盖要求全部通过。

| 检查项 | 实际 | 要求 | 结果 |
| --- | ---: | ---: | --- |
| P0.5 enabled primitives | 125 | 90 | pass |
| P0.5 new primitives | 70 | 35 | pass |
| pairwise / diagnostic combos | 43 | 30 | pass |
| high-volatility combos | 11 | 10 | pass |
| repair initiation combos | 9 | 8 | pass |
| rank jump / leadership combos | 8 | 6 | pass |
| money quality combos | 9 | 6 | pass |
| sparse strong-day patterns | 6 | 5 | pass |
| tested early-entry patterns | 30 | 8 | pass |
| tested high-volatility patterns | 11 | 10 | pass |
| tested repair patterns | 9 | 8 | pass |
| tested rank jump patterns | 8 | 6 | pass |
| tested money quality patterns | 9 | 6 | pass |

但 qualified lead 全部为 0：

| 类别 | tested | qualified |
| --- | ---: | ---: |
| early-entry | 30 | 0 |
| high volatility | 11 | 0 |
| repair initiation | 9 | 0 |
| rank jump / leadership | 8 | 0 |
| money quality | 9 | 0 |

失败原因分布：

| 失败原因 | 数量 | 含义 |
| --- | ---: | --- |
| `instrument_year_lift_not_positive` | 30 | stock-day / trigger-event 看起来有效，但年度股票维度不优于 baseline |
| `dedup_trigger_event_lift_not_positive` | 10 | 去重事件口径不成立，可能主要来自连续 stock-day 重复 |
| `insufficient_stock_day_count` | 2 | 样本太少，只能做诊断 |
| `diagnostic_only_not_p1_ready` | 1 | 指标有效但语义偏后段或诊断，不允许升级为 P1 entry hypothesis |

这组失败原因很关键：P0.5 不是因为没有 lift，而是因为 lift 没有通过更严格的去重和泛化口径。

## 3. 三类 Lead 分离结果

### 3.1 Early Entry Discovery

Early-entry 主榜硬性排除了：

- `post_20pct_from_recent_low = true`
- `post_30pct_from_recent_low = true`
- `observable_state_stage = observable_late_acceleration_risk`

主榜 top 结构如下：

| lead | 样本 | precision | stock-day lift | dedup lift | IY lift | episode coverage | 失败原因 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 扩张性高波 + 相对强度 | 742 | 24.53% | 2.658 | 1.833 | 0.556 | 5.86% | instrument-year 不成立 |
| 高波 + 回撤受控 + 排名强 | 808 | 23.39% | 2.535 | 1.995 | 0.572 | 3.95% | instrument-year 不成立 |
| 扩张性高波 + 成交质量 | 589 | 22.75% | 2.491 | 1.832 | 0.562 | 5.18% | instrument-year 不成立 |
| 高波上半区 + 行业宽度改善 | 1027 | 20.06% | 2.179 | 1.762 | 0.642 | 7.36% | instrument-year 不成立 |
| 高ATR但守住中位价 | 1223 | 16.76% | 1.817 | 1.711 | 0.609 | 8.72% | instrument-year 不成立 |
| 深回撤后首次收复 | 3443 | 12.17% | 1.395 | 1.265 | 0.625 | 16.62% | instrument-year 不成立 |
| 5日排名跃迁 | 7636 | 11.93% | 1.293 | 1.095 | 0.625 | 26.29% | instrument-year 不成立 |

解释：

- early-entry 中最强的是高波动相关结构，不是低波压缩、也不是单纯 rank jump。
- 高波结构的 stock-day precision 能到 `20-25%`，明显高于 early-entry baseline 约 `9%`。
- 但这些 lead 的 instrument-year lift 只有 `0.56-0.64` 左右，说明它们没有把“哪些股票年更可能产生大 winner”筛出来。
- `winner_episode_coverage` 也偏低，高波 early-entry top lead 只覆盖约 `4-9%` 的 winner episode，意味着它们不是主路径，只是少数 winner 路径中的局部片段。

可能推测：

1. 高波动 early-entry 不是假象，但它更像“当 winner 已经进入某个局部加速/修复状态时的触发片段”，不是完整早期发现结构。
2. 当前 early-entry lead 对少数局部事件有用，但没有跨 instrument-year 泛化，可能说明缺少“事件前置条件”，例如更长的底部结构、行业启动顺序、低点后的事件序列。
3. 如果后续继续 early-entry broad discovery，应该减少对单日强度和当前状态的依赖，转向“过去 20/60 日的结构变化路径”。

### 3.2 Confirmation / Continuation

Confirmation 榜的表现比 early-entry 更像路径解释变量。

| lead | 样本 | precision | stock-day lift | dedup lift | IY lift | episode coverage | 失败原因 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 高波 + 放量 + 上半区 | 5067 | 23.54% | 1.654 | 1.665 | 0.780 | 54.36% | instrument-year 不成立 |
| Gap up 上半区且守住 | 795 | 25.16% | 1.767 | 1.648 | 0.693 | 36.92% | instrument-year 不成立 |
| 首次涨停诊断 | 679 | 24.01% | 1.686 | 1.645 | 0.664 | 40.46% | instrument-year 不成立 |
| 首次接近涨停诊断 | 838 | 22.55% | 1.584 | 1.545 | 0.629 | 44.01% | instrument-year 不成立 |
| 极强实体日诊断 | 7547 | 19.74% | 1.388 | 1.265 | 0.753 | 68.12% | instrument-year 不成立 |
| 放量后5日价格保持 | 11435 | 16.59% | 1.165 | 1.065 | 0.706 | 68.66% | instrument-year 不成立 |
| 放量后3日价格保持 | 11000 | 16.16% | 1.135 | 1.060 | 0.680 | 69.07% | instrument-year 不成立 |

解释：

- Confirmation 线索的 `winner_episode_coverage` 明显高于 early-entry，多个成交/强势日结构覆盖 `54-69%` 的 winner episode。
- 但 precision 和 dedup lift 没有高波 early-entry 那么强，instrument-year lift 仍低于 1。
- 这说明这些结构在很多 winner 路径中会出现，但也会在大量非 winner 或普通波段中出现。

可能推测：

1. 放量后价格保持、强实体日、gap up 守住等结构更适合描述 winner 的中途确认，而不是筛选初始候选。
2. 这些变量可能适合 P1 中做“已有候选的 continuation confidence”或“持有容忍度增强”，但不适合单独当买点。
3. 如果后续做两阶段流程，它们可以作为第二阶段确认变量：先由更早的结构筛出候选，再用这些 confirmation 状态判断是否继续跟踪。

### 3.3 Hold / Exit Tolerance

Hold / exit 榜里最突出的结构是 `后段加速高波`。

| lead | 样本 | precision | stock-day lift | dedup lift | IY lift | episode coverage | 失败原因 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 后段加速高波 | 581 | 43.72% | 2.337 | 2.339 | 1.362 | 5.59% | diagnostic only |
| 强势日后缩量回撤守住 | 6602 | 21.10% | 1.128 | 0.997 | 0.702 | 59.26% | dedup lift 不成立 |
| 长上影强势失败 | 4171 | 18.82% | 1.006 | 0.979 | 0.730 | 63.08% | dedup lift 不成立 |

解释：

- `后段加速高波` 是唯一同时满足 stock-day、dedup 和 instrument-year lift 都大于 1 的结构。
- 但它被标记为 `diagnostic_only_not_p1_ready`，原因是语义已经偏后段，不是 early-entry。
- 它的 episode coverage 只有 `5.59%`，说明它不是大多数 winner 的必经状态，而是少数后段加速 winner 的高精度片段。

可能推测：

1. 已经进入后段加速的高波状态，确实有较高继续冲刺概率。
2. 但这个结构更适合 hold / take-profit / late acceleration risk 研究，不适合迁移到初始发现。
3. 如果 P1 允许 confirmation / hold 分支，这个方向可以保留为“不要过早卖出”的诊断变量，而不是买入变量。

## 4. 分族群实验解读

### 4.1 高波动拆解

高波动是 P0.5 中最强的局部结构来源。

| lead | precision | stock-day lift | dedup lift | IY lift | false positive drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| 扩张性高波 + 相对强度 | 24.53% | 2.658 | 1.833 | 0.556 | -23.16% |
| 高波 + 回撤受控 + 排名强 | 23.39% | 2.535 | 1.995 | 0.572 | -21.09% |
| 扩张性高波 + 成交质量 | 22.75% | 2.491 | 1.832 | 0.562 | -24.29% |
| 高波上半区 + 行业宽度改善 | 20.06% | 2.179 | 1.762 | 0.642 | -22.38% |
| 高ATR但守住中位价 | 16.76% | 1.817 | 1.711 | 0.609 | -22.42% |
| 破坏性高波对照 | 18.88% | 2.046 | 1.593 | 0.842 | -20.55% |

结论：

- 高波动不应被简单当成风险过滤项。
- 有效的高波结构通常带有上半区收盘、相对强度、成交质量、回撤受控或行业宽度改善。
- 但高波动 false positive 的后续回撤仍明显，多个结构的 false positive 平均 120 日未来回撤在 `-21%` 到 `-24%` 左右。
- `破坏性高波对照` 也有正 stock-day / dedup lift，说明当前高波分类仍没有完全区分“破坏性高波”和“大 winner 早期剧烈换手”。

可能推测：

1. A 股大 winner 的早期经常不是低波启动，而是高波动中的结构化换手。
2. 高波动需要“许可条件”，不是“否决条件”；许可条件可能包括上半区收盘、回撤受控、相对强度、行业宽度改善。
3. 单日或 20 日高波仍不足以形成稳定 entry，下一步需要加入事件顺序，例如“高波后是否缩量守住”“高波后是否形成更高低点”。

### 4.2 修复初期

修复初期结构比高波动弱，但更接近 early-entry 语义。

| lead | precision | stock-day lift | dedup lift | IY lift | episode coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 深回撤后首次收复 | 12.17% | 1.395 | 1.265 | 0.625 | 16.62% |
| 回撤速度减弱 + 初修复 | 10.50% | 1.207 | 1.161 | 0.735 | 21.39% |
| 低点修复 + 相对强 | 9.14% | 0.990 | 1.138 | 0.635 | 33.11% |
| 假跌破后快速收复 | 10.44% | 1.132 | 1.075 | 0.711 | 18.94% |

结论：

- 修复类 lead 的平均 lead time 通常更长，族群中位值约 `70` 个交易日。
- 修复类 false positive 后续回撤相对高波动更轻，族群中位约 `-14.8%`。
- 但修复结构的 precision 和 dedup lift 不够强，instrument-year lift 仍低于 1。

可能推测：

1. 修复初期确实更早，但信噪比不足。
2. 单纯“收复中位价”“低点抬高”“回撤速度减弱”太宽，容易覆盖大量普通反弹。
3. 修复类方向如果继续做，需要叠加更强的结构条件，例如行业尚未同步但个股率先转强、缩量回撤后再次放量上破、或连续两次 higher low。

### 4.3 Rank Jump / Leadership

Rank jump 方向具有早期含义，但当前只适合 watchlist。

| lead | precision | stock-day lift | dedup lift | IY lift | episode coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 市场转折前排个股 | 15.50% | 1.679 | 1.344 | 0.382 | 4.63% |
| 个股领先滞后行业 | 13.30% | 1.444 | 1.166 | 0.422 | 12.26% |
| 行业内从中后排跃迁到前20% | 10.69% | 1.161 | 1.140 | 0.353 | 8.31% |
| 行业宽度刚改善的前排个股 | 11.18% | 1.214 | 1.122 | 0.435 | 16.35% |
| 5日排名跃迁 | 11.93% | 1.293 | 1.095 | 0.625 | 26.29% |

结论：

- Rank jump 的 stock-day lift 普遍低于高波动。
- 它的 `trend_speed_not_fast_rate` 很高，族群中位接近 `99%`，说明它确实比绝对强度 top10% 更早。
- 但 precision 不够，instrument-year lift 很弱，说明“早”换来了大量 false positive。

可能推测：

1. Rank jump 更适合作为 first-stage candidate filter，而不是直接 entry。
2. 它可能需要被后续高波守住、成交质量或行业宽度改善确认。
3. 如果要保留 rank jump，应该降低对单次跃迁的信任，改看 rank jump 后 5/10/20 日是否维持、回撤是否受控。

### 4.4 成交质量

成交质量在 coverage 上很强，但在 precision 上不强。

| lead | precision | stock-day lift | dedup lift | IY lift | episode coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 放量后3日价格保持 | 16.16% | 1.135 | 1.060 | 0.680 | 69.07% |
| 放量后5日价格保持 | 16.59% | 1.165 | 1.065 | 0.706 | 68.66% |
| 上涨日放量 | 14.37% | 0.985 | 1.017 | 0.836 | 68.53% |
| 高成交额持续 | 14.28% | 1.005 | 1.048 | 0.845 | 66.21% |
| 成交放大 + 行业宽度改善 | 13.39% | 0.948 | 0.979 | 0.743 | 63.76% |

结论：

- 成交质量不是 early-entry 主线。
- 它在 winner episode 中经常出现，coverage 高达 `64-69%`。
- 但 stock-day lift 和 dedup lift 接近 1，说明它不是有效筛选器。

可能推测：

1. 成交质量更像“winner 发展过程中的必要但不充分条件”。
2. 放量后价格保持可能适合作为 continuation confirmation 或止盈延后条件。
3. 单纯成交放大仍不应进入 P1 entry hypothesis；需要和价格结构、行业启动、回撤控制一起使用。

### 4.5 Sparse Strong-Day Diagnostic

Sparse strong-day 的 precision 和 episode coverage 都比较高，但泛化权限有限。

| lead | precision | stock-day lift | dedup lift | IY lift | episode coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gap up 上半区且守住 | 25.16% | 1.767 | 1.648 | 0.693 | 36.92% |
| 首次涨停诊断 | 24.01% | 1.686 | 1.645 | 0.664 | 40.46% |
| 首次接近涨停诊断 | 22.55% | 1.584 | 1.545 | 0.629 | 44.01% |
| 极强实体日诊断 | 19.74% | 1.388 | 1.265 | 0.753 | 68.12% |

结论：

- 强势日结构能解释很多 winner 的路径。
- 首次涨停、首次接近涨停、gap up 守住的 precision 明显高于 baseline。
- 但它们不是早期发现：出现时通常已经有明显强势日，且 instrument-year lift 不成立。

可能推测：

1. Sparse strong-day 可以作为 path diagnostic，帮助解释 winner 是如何进入加速段的。
2. 它适合作为 P1 中的 lifecycle 标记或 confirmation feature，不适合作为 general entry lead。
3. 如果后续做序列研究，可以把首次涨停/强实体日作为路径节点，而不是入口信号。

## 5. 四种评价口径的冲突

P0.5 的关键价值是同时输出四种口径。它们给出的结论不同：

| 口径 | 本轮观察 | 解释 |
| --- | --- | --- |
| stock-day precision / lift | 多个 lead 很强，最高 stock-day lift `2.658` | 局部状态确实能提高未来 120 日 50% high 概率 |
| dedup trigger-event lift | 高波、强势日仍有 lift，最高 `2.339` | 去掉连续日期重复后，部分事件仍有信息 |
| instrument-year hit lift | 除 `后段加速高波` 外全部低于 1 | 这些 lead 不能稳定筛出更好的股票年 |
| winner episode coverage | confirmation / money / sparse 较高，early-entry 较低 | 很多变量解释 winner 路径，但不是早期入口 |

这说明不能只按 stock-day lift 排名。典型例子：

- `扩张性高波 + 相对强度`：stock-day lift `2.658`，dedup lift `1.833`，但 IY lift `0.556`，episode coverage `5.86%`。
- `高波 + 回撤受控 + 排名强`：dedup lift `1.995`，但 IY lift `0.572`，episode coverage `3.95%`。
- `放量后3日价格保持`：episode coverage `69.07%`，但 stock-day lift `1.135`，IY lift `0.680`。
- `后段加速高波`：stock-day lift `2.337`、dedup lift `2.339`、IY lift `1.362`，但语义是后段状态，不能作为 early-entry。

可能推测：

1. 当前数据中存在“局部触发事件有效，但股票年选择无效”的结构。
2. Instrument-year 口径暴露出一个问题：多数 lead 是 winner 发生过程中反复出现的状态，而不是在 winner 发生前就能把正确股票筛出来的状态。
3. 后续如果目标是 early-entry，必须把排序主口径继续放在 dedup trigger-event + instrument-year，而不是回退到 stock-day lift。

## 6. P0 第一版线索的降级与保留

P0 第一版里最强的若干 lead 在 P0.5 中需要重新定位：

- `observable_late_acceleration_risk` / 后段加速类：降级为 hold / exit tolerance，不计入 early-entry。
- `post_20pct_from_recent_low`、`post_30pct_from_recent_low`：只能做 confirmation / continuation / hold，不是初始买点。
- 高波动单变量：保留，但必须拆成扩张性高波、破坏性高波、反转高波、后段加速高波和失败高波。
- 成交放大：不作为主线，只作为确认变量或失败警示变量。
- 强势日：保留为 sparse diagnostic，不升级为 general hypothesis。

本轮最值得保留的方向不是“一个可交易规则”，而是几类 research leads：

1. **高波动许可条件**：高波不是风险否决，关键在于是否上半区收盘、回撤受控、相对强、成交支持。
2. **路径确认变量**：放量后价格保持、强实体日、gap up 守住能解释 winner 发展过程。
3. **后段持有变量**：后段加速高波对 continuation 有高 precision，但只服务 hold / exit。
4. **早期 watchlist 变量**：rank jump 和修复初期结构可能更早，但当前不能单独提高年度筛选质量。

## 7. 基于数据的可能推测

以下推测不是结论，只是后续 broad discovery 的候选方向。

### 推测 1：真正 early-entry 可能不是单日状态，而是事件序列

证据：

- early-entry 中多个单日/二变量 lead 的 stock-day lift 很强，但 IY lift 全部低于 1。
- 高波、rank jump、修复收复都能解释局部 winner 状态，却不能稳定筛出股票年。

推测：

```text
未来 winner 的早期结构可能不是某一天满足一个状态，
而是“修复 -> 守住 -> 再次跃迁 -> 成交确认”的多事件顺序。
```

后续应观察：

- 第一次修复后 5/10/20 日是否守住。
- 高波后是否缩量回撤但不破关键低点。
- rank jump 后是否维持行业前排。
- 放量后是否进入更高低点结构。

### 推测 2：高波动是 winner 的必要通道之一，但需要“失败过滤”

证据：

- 高波 early-entry top lead 的 stock-day lift `2.18-2.66`，dedup lift `1.71-2.00`。
- false positive 后续平均回撤仍可达 `-21%` 到 `-24%`。
- 破坏性高波对照也有正 lift，说明当前拆分仍不够干净。

推测：

```text
大 winner 早期可能必须经历高波换手，
但很多高波只是普通波动或失败反弹。
```

下一步需要优先找失败过滤变量，而不是继续证明“高波有 lift”。

可能的失败过滤方向：

- 高波后 N 日是否跌破触发日低点。
- 高波后成交是否快速萎缩但价格守住。
- 高波后是否形成 higher low。
- 高波后行业宽度是否继续改善。

### 推测 3：成交质量不是入口变量，而是路径确认变量

证据：

- 放量后 3/5 日价格保持的 episode coverage 接近 `69%`。
- 但 stock-day lift 只有 `1.13-1.17`，dedup lift 约 `1.06`，IY lift 小于 1。

推测：

```text
成交质量广泛存在于 winner 路径，
但它本身太常见，无法筛选 winner。
```

成交质量更适合回答：

- 已有候选是否仍值得跟踪。
- 是否从 early watchlist 升级到 confirmation。
- 是否允许 hold 更久。

不适合回答：

- 哪只股票是早期 winner。
- 哪一天是初始买点。

### 推测 4：Rank jump 可能是最早的 watchlist 变量，但不是 entry

证据：

- Rank jump 族群的 `trend_speed_not_fast_rate` 中位接近 `99%`，说明它确实早于绝对强趋势。
- 但 precision 只有 `10-16%`，IY lift 普遍很弱。

推测：

```text
Rank jump 适合做早期 watchlist 扩容，
但必须等待后续结构确认。
```

它可能的正确用途是：

- 第一阶段生成观察池。
- 第二阶段等待高波守住、成交确认、行业宽度改善。
- 第三阶段才判断是否进入 P1 hypothesis。

### 推测 5：修复初期结构需要更强上下文

证据：

- 深回撤后首次收复、回撤速度减弱、假跌破收复都有正 stock-day / dedup lift。
- 但 precision 只有 `10-12%`，IY lift 不成立。

推测：

```text
修复初期结构方向是对的，
但当前定义太宽，把大量普通反弹也纳入了。
```

后续应加入：

- 修复前的下跌衰竭程度。
- 修复后的守住天数。
- 行业内相对位置是否改善。
- 修复过程中成交是否从恐慌放量转向健康换手。

### 推测 6：强势日是 winner path node，不是 general entry lead

证据：

- 首次涨停、首次接近涨停、gap up 守住 precision 较高。
- 但都未通过 instrument-year lift。
- 极强实体日 episode coverage 高达 `68.12%`。

推测：

```text
强势日更像 winner 路径中的节点，
可以用于解释“什么时候进入加速段”，
但不能用来证明“它是早期入口”。
```

### 推测 7：Instrument-year gate 很严格，但本轮不能放松

证据：

- 多数 lead 在 stock-day / dedup 口径下有正 lift，却被 IY gate 全部否决。
- 如果只看 stock-day，P0.5 会得出过于乐观的结论。

推测：

```text
instrument-year gate 可能偏严格，
但它揭示了 stock-day 重复计数和路径状态重复的问题。
```

后续可以审计 denominator 是否需要分层，但不应在当前阶段放弃该 gate。

## 8. 下一阶段建议

当前不建议直接进入 Explore10，也不建议把 P0.5 top lead 写成 P1 formal entry hypothesis。

更合理的下一步是继续 P0 broad discovery，重点放在：

1. **事件序列**：从单日状态扩展到 3/5/10/20 日路径，例如“高波后守住”“rank jump 后维持”“修复后再突破”。
2. **失败过滤**：专门研究 high-vol false positive、volume false positive、repair false positive。
3. **两阶段框架**：rank jump / repair 生成 watchlist，高波守住 / 成交质量 / 强势日做 confirmation。
4. **生命周期分离**：entry、confirmation、hold/exit 必须继续分榜，不得混成一个总 leadboard。
5. **年度稳定性审计**：下一轮需要把 top trigger-event lead 的 year-by-year trigger precision 和 IY hit-rate 单独展开，避免 pooled lift 掩盖年份差异。

如果后续要进入 P1，建议只允许以下方向以“诊断/确认”身份进入：

- 高波 + 放量 + 上半区：confirmation candidate。
- 放量后 3/5 日价格保持：continuation / hold candidate。
- 首次涨停、首次接近涨停、gap up 守住：sparse path diagnostic。
- 后段加速高波：hold / exit tolerance candidate。

但 early-entry formal hypothesis 仍应暂缓。

## 9. 数据纪律

- `p0_label_panel_reused = true`
- `p0_episode_labels_reused = true`
- `p0_5_new_feature_panel_generated = true`
- `observed_reference_used_for_selection = false`
- `historical_trade_results_used_for_labeling = false`
- `historical_trade_results_used_for_signal = false`
- `historical_trade_results_used_for_selection = false`
- `explore8_profile_csv_used_for_label = false`
- `explore8_profile_csv_used_for_signal = false`
- `explore8_profile_csv_used_for_selection = false`
- `evaluation_only_false_positive_definition` 只由 forward label 与未来回撤审计计算，不进入 T 日 feature、lead formula、candidate selection 或 ranking input。

## 10. 最终判断

P0.5 的结论是：

```text
未发现足够稳定的 early-entry 结构。
当前 Explore9 的有效方向主要是 confirmation / continuation / hold tolerance，
不应把这些 lead 误写成初始买点。
```

推荐保持：

```text
recommendation = continue_p0_broad_discovery
```

Explore10 只能作为远期路径记录；是否进入策略回测必须等待更稳定的 early-entry 或明确的 confirmation / hold P1 假设形成后再评估。
