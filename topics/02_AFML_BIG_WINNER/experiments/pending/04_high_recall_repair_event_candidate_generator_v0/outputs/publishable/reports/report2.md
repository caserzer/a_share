# 04 补充报告：对照 02 后的 +50 Event-Anchored Recall 复核

本补充报告用于回答一个单独问题：对照 02 的 reverse lifecycle 画像，04 当前候选池的 `+50` recall 是否偏低。

结论：**是，偏低，而且是结构性偏低**。04 当前 setup-inclusive density-kept 候选池作为 high-recall event generator 还没有达到预期；问题不主要是 precision，而是 event 结构和 density/canonical 规则把可用候选压掉了。

## 1. 口径说明

这里区分三种口径：

1. `episode-anchored recall`：02/04 主 recall 口径。分母是 02 冻结的 target big-winner episodes；只看某个窗口内是否有候选 event 捕获 episode。
2. `event-anchored precision`：分母是 04 生成的候选 event；看该 event 自己从 t0 往后 120 日 MFE 是否达到 `+50%`。
3. `+50 event-anchored bridge recall`：分母仍是 02 target episodes，但只有当窗口内存在至少一个候选 event，且这个 event 自己从 t0 往后 120 日 MFE >= `+50%`，才算捕获。

严格意义上的 `event-anchored recall` 需要“全市场所有可能 +50 event”的完整分母，目前 04 没有定义这个 universe。因此本报告采用第三种桥接口径，它最贴近“候选池是否捕获了可作为后续 primary/meta 样本的 +50 event”。

## 2. 当前 04 的 +50 Bridge Recall

setup-inclusive density-kept canonical event pool 的结果如下：

| window | any event recall | +50 event recall |
|:--|--:|--:|
| low+20 | 23.6% | 12.9% |
| low+30 | 39.5% | 22.2% |
| before-first-50pct | 55.3% | 35.2% |
| before episode high | 57.0% | 36.4% |
| low+120 | 71.4% | 41.5% |

最重要的 actionable 口径是 `before-first-50pct`：当前 any-event recall 为 `55.3%`，但要求捕获 event 自己后续还能从 t0 走出 `+50%` 时，只剩 `35.2%`。

这说明当前候选池并不只是“precision 低”；它对真正可作为 +50 event 样本的捕获也偏低。

## 3. 对照 02：为什么这个 recall 偏低

02 的目标 episode 本身给出了更高的生命周期可捕获性：

| 02 证据 | 数值 / 解释 |
|:--|:--|
| target big-winner episodes | 866 |
| winner 120d MFE mean | 84.9% |
| validation winner 120d MFE mean | 71.8% |
| robustness winner 120d MFE mean | 92.3% |
| long duration bucket | 551 / 866 = 63.6% |
| long bucket low-to-high median | 约 110 个交易日 |
| winner EMA60 reclaim occurrence | 约 95%-97% |
| S3 rank persistence winner rate | 57.3% |
| S6 continuation discriminator winner rate | 79.2% |

02 的核心含义是：大赢家不是一次性短促反弹为主，而是低点后有较长生命周期，且多数 winner 会出现 EMA60 reclaim、rank persistence、continuation 等可观察阶段。

在这个前提下，04 如果定位为 high-recall event generator，`before-first-50pct` 的 +50 bridge recall 只有 `35.2%`，确实过低。它意味着大量 02 中真实存在、且有较长推进路径的 big-winner episode，并没有被当前 04 的 density-kept event 结构有效捕获为后续仍能 +50 的 event。

## 4. 偏低的直接原因

### 4.1 Event-anchored +50 天然比 episode-anchored +50 更难

02 的 +50 是从 retrospective low 算起；04 的 event-positive 是从 event t0 算起。如果 event 已经比 low 高了 10%-20%，它要从更高基准再涨 50%，自然会漏掉一批 episode。

这部分是合理损耗，不是 bug。但它不能解释全部差距。

### 4.2 Density folding 杀掉了大量 setup recall

04 当前 density loss 非常明显：

| window | setup raw/canonical recall | setup density-kept recall | loss |
|:--|--:|--:|--:|
| low+10 | 59.1% | 13.7% | 45.4% |
| low+20 | 59.5% | 23.6% | 35.9% |
| low+30 | 63.4% | 39.5% | 23.9% |
| before-first-50pct | 71.2% | 55.3% | 15.9% |

也就是说，很多 candidate 不是不存在，而是在 setup-inclusive union density 里被折叠掉了。对于 high-recall primary candidate generator，这种损耗过大。

### 4.3 E0 与 reclaim/quality event 混在同一个 union density 中互相挤压

当前 setup-inclusive union 把 E0/E1/E2/E4 放进同一个 20 日 union density。结果是 E0 作为更早、更密集的 setup context，经常抢占 union cluster 的 canonical 位置，后面的 E1/E2/E4 被折叠。

这个现象可以从 setup 与 reclaim-based 的对比看出来：

| window | setup-inclusive density-kept recall | reclaim-based density-kept recall |
|:--|--:|--:|
| low+20 | 23.6% | 35.9% |
| low+30 | 39.5% | 46.8% |
| before-first-50pct | 55.3% | 69.6% |
| before episode high | 57.0% | 70.9% |

reclaim-based 不含 E0，反而 recall 更高。这是一个明确的结构信号：E0 不应该与 E1/E2/E4 在同一个 density/canonical 选择里竞争。

## 5. 更深层根因拆解

把 `before-first-50pct` 的 866 个 target episode 做 waterfall，可以看到 recall 低不是单点问题，而是三段损耗叠加：

| window | raw 未命中 | density 折损 | 有 density event 但无 +50-positive event | +50 bridge 捕获 |
|:--|--:|--:|--:|--:|
| low+20 | 351 / 40.5% | 311 / 35.9% | 92 / 10.6% | 112 / 12.9% |
| low+30 | 317 / 36.6% | 207 / 23.9% | 150 / 17.3% | 192 / 22.2% |
| before-first-50pct | 249 / 28.8% | 138 / 15.9% | 174 / 20.1% | 305 / 35.2% |

这里的 `raw 未命中` 指 setup-inclusive raw/canonical 在窗口内没有任何候选；`density 折损` 指 raw/canonical 有命中但 density-kept 没命中；第三列指窗口内有 density-kept event，但没有任何 event 自身的 120d MFE 达到 +50%。因此 `35.2%` 不是单纯被 precision 拖低，而是先被 raw coverage、再被 density、最后被 event-anchored label basis 连续压缩。

### 5.1 density 折损不是随机噪声，而是 pre-low E0 抢占

对 density-loss episode 逐个回溯 union cluster 后，发现 setup-inclusive 的低窗口损耗几乎全部来自同一个机制：20 日 union density 保留了低点前的最早 E0，导致低点当天或低点后的 E0/E1/E2/E4 被折叠；但被保留的 pre-low event 又落在 actionable window 之外。

| window | density-loss episodes | retained event 在 low 前 | retained first source | first in-window folded source | full folded cluster source | median gap |
|:--|--:|--:|:--|:--|:--|--:|
| low+30 | 207 | 207 / 100.0% | E0: 202 / 207 | E0: 207 / 207 | E0+E1+E2+E4: 147 / 207 | 4 sessions |
| before-first-50pct | 138 | 138 / 100.0% | E0: 136 / 138 | E0: 138 / 138 | E0+E1+E2+E4: 133 / 138 | 5 sessions |

这解释了为什么 `pre-low 20d` recall 很高，但 `low+10/20/30` recall 会突然塌陷：density 的簇起点经常在 low 前 1-19 个交易日，保留下来的 canonical t0 不计入 low-to-plus 窗口；后面真正落在 low 后的 E0、reclaim、quality、relative-strength turn 都被同一个簇吃掉。

### 5.2 E0/E1/E2/E4 不是四条独立召回通道

`before-first-50pct` 的 raw family overlap 很高：

| raw family / union | captured episodes | recall |
|:--|--:|--:|
| E0 | 612 | 70.7% |
| E1 | 605 | 69.9% |
| E2 | 603 | 69.6% |
| E4 | 571 | 65.9% |
| setup-inclusive raw union | 617 | 71.2% |

拆 overlap 后更清楚：

| overlap bucket | episodes | share |
|:--|--:|--:|
| E0 only | 11 | 1.3% |
| E1/E2/E4 only over E0 | 5 | 0.6% |
| E0 and E1/E2/E4 both | 601 | 69.4% |
| setup raw absent | 249 | 28.8% |

也就是说，E1/E2/E4 当前不是在扩展新 episode coverage，而是在 E0 已经能触达的 episode 上派生确认事件。原因在实现上也成立：E1 来自 seed low，E2/E4 又只从 density-kept reclaim 派生。它们在 raw 层面高度共线，进入同一个 union density 后自然不是“多路召回”，而是“同一路事件序列互相挤压”。

### 5.3 setup-inclusive 比 reclaim-based 差，是因为 E0 通道污染了事件通道

如果把 E0 拿掉，让 E1/E2/E4 作为 reclaim-based 通道单独 density，`before-first-50pct` 能覆盖 603 个 episode；当前 setup-inclusive 只覆盖 479 个。

| window | setup only | reclaim only | both | setup/reclaim union recall |
|:--|--:|--:|--:|--:|
| low+20 | 36 | 143 | 168 | 40.1% |
| low+30 | 76 | 139 | 266 | 55.5% |
| before-first-50pct | 2 | 126 | 477 | 69.9% |
| before episode high | 1 | 121 | 493 | 71.0% |

最关键的是 `before-first-50pct`：有 126 个 episode 是 reclaim-based 能捕获、setup-inclusive 捕获不到。这个数量正好说明，E0 不应该参与最终 event channel 的 density；它更适合作为 context/eligibility，而不是和 reclaim/quality/rank-turn 竞争唯一 canonical t0。

### 5.4 +50 bridge 还被 timing / basis 再压一层

即使保留下来的 density event 命中了 episode，它也未必从自身 trade-open basis 往后还有 +50。用每个 episode 的 first density-kept event 做诊断，`before-first-50pct` 里 479 个 any-event capture 只有 293 个 first event 是 +50-positive；报告中的 any-positive bridge 是 305 个，说明后续同窗口 event 只额外救回 12 个 episode。

| duration bucket | episodes | any density before-first | first event +50-positive | first-positive / density |
|:--|--:|--:|--:|--:|
| fast | 103 | 38 / 36.9% | 8 / 7.8% | 21.1% |
| medium | 212 | 105 / 49.5% | 44 / 20.8% | 41.9% |
| long | 551 | 336 / 61.0% | 241 / 43.7% | 71.7% |

fast/medium 掉得最厉害。原因不是这些 episode 不涨，而是 event t0 相对 low 已经偏晚，或者用 next-open 作为 label basis 后，剩余 120d MFE 不够 +50。long bucket 因为后续推进空间更长，first event positive retention 明显更高。

### 5.5 raw coverage 本身也有 regime 偏置

raw 未命中也不是均匀分布。`before-first-50pct` 下，risk-off 的 raw recall 有 83.0%，但 risk-on 只有 55.2%，transition 只有 61.6%。

| market regime | episodes | setup raw recall | setup density recall | reclaim density recall |
|:--|--:|--:|--:|--:|
| risk_off | 453 | 83.0% | 61.8% | 80.4% |
| risk_on | 210 | 55.2% | 47.6% | 54.8% |
| transition | 203 | 61.6% | 48.8% | 61.1% |

这说明当前事件定义更像“深回撤后的修复/reclaim”候选，而不是完整覆盖所有大赢家生命周期。risk-on/transition 里的赢家可能更多是浅回撤、平台延续、相对强度持续后的 breakout，不一定会经过 60d trailing low + EMA60 reclaim 这条路径。

### 5.6 split denominator 还受到 PIT universe 大小影响

04 的 target denominator 不是全 A，而是 01 冻结的 PIT large-cap executable universe。这个 universe 不是 top-N 固定数量，而是固定市值阈值：主板 `total_market_cap_cny > 50bn`，创业板 `> 20bn`。因此早期 market-cap universe 天然更小，train 的 raw episode count 偏少有一部分来自分母偏小。

基于 01 的 `daily_universe_counts.csv`，用 `sum(member_count) / 252` 近似 universe-years：

| year | avg daily universe | universe-years | target episodes | episodes / 100 universe-years |
|:--|--:|--:|--:|--:|
| 2017 | 91.5 | 88.6 | 0 | 0.0 |
| 2018 | 91.4 | 88.1 | 39 | 44.3 |
| 2019 | 110.1 | 106.6 | 47 | 44.1 |
| 2020 | 151.6 | 146.2 | 107 | 73.2 |
| 2021 | 213.9 | 206.3 | 92 | 44.6 |
| 2022 | 227.4 | 218.3 | 109 | 49.9 |
| 2023 | 266.0 | 255.4 | 60 | 23.5 |
| 2024 | 268.5 | 257.9 | 178 | 69.0 |
| 2025 | 346.0 | 333.6 | 234 | 70.1 |

按 split 聚合后：

| period | episodes | avg daily universe | universe-years | episodes / 100 universe-years |
|:--|--:|--:|--:|--:|
| train config 2017-2021 | 285 | 131.6 | 635.8 | 44.8 |
| train effective low-years 2018-2021 | 285 | 141.7 | 547.2 | 52.1 |
| validation 2022-2023 | 169 | 246.7 | 473.8 | 35.7 |
| robustness 2024-2025 | 412 | 307.3 | 591.5 | 69.7 |

这个结果支持两个判断：

1. train 原始数量 `285` 看起来少，确实受早期 universe 小影响。2018 平均 universe 只有 `91.4`，2025 已经到 `346.0`，约为 2018 的 `3.8x`。
2. 但 universe size 不能解释全部差异。按 universe-years 归一化后，train 并不低于 validation，反而高于 validation；真正偏高的是 robustness，`69.7 / 100 universe-years`，明显高于 train config 的 `44.8` 和 validation 的 `35.7`。

因此，后续报告和建模不能只按 episode count 看 split 平衡；更合理的是同时报告 `episode count`、`universe-years`、`episodes / 100 universe-years`。对于训练集，问题不是“单位 universe 下太少”，而是固定市值 universe 的早期规模小，导致 raw event-positive 样本绝对数偏少。

### 5.7 如果坚持当前 universe，稳定 split 结果很难

如果继续使用当前 fixed-market-cap PIT universe，并继续按当前 train / validation / robustness 三段切分，要求同一个 event generator 或 downstream primary/meta model 在三段上都稳定、漂亮，预期并不现实。

这不是说结果数学上不可能，而是当前设置同时引入了三类非平稳性：

1. **机会集规模非平稳**：2018 平均 daily universe 为 `91.4`，2025 为 `346.0`，同一事件规则面对的候选股票池规模差异接近 `3.8x`。
2. **big-winner incidence 非平稳**：按 universe-years 归一化后，robustness 仍有 `69.7 / 100 universe-years`，高于 train config 的 `44.8` 和 validation 的 `35.7`。
3. **event-level label 分布非平稳**：setup-inclusive density-kept event 的 +50 positive rate 在 train / validation / robustness 分别为 `11.7% / 6.4% / 21.5%`。

因此，当前 fixed-cap universe 更适合做“绝对大市值股票中的生命周期诊断”，不适合直接要求跨年份机会集均衡的 supervised event learning。04 当前 recall 低的主因仍是 event architecture / density 设计，但 universe/split 会放大 train 样本少、validation 压力大、robustness 偏强的问题。

### 5.8 Universe 与切分重设建议

若目标转向后续 primary/meta modeling，更合理的 universe 是 PIT top-N，而不是固定市值阈值。建议新增一个并行 universe，不覆盖当前 fixed-cap baseline：

```text
universe_v1_topn_400_100:
  main board: daily PIT total_market_cap top 400
  ChiNext: daily PIT total_market_cap top 100
  total target: about 500 names per day
```

执行细节应保持 PIT：

1. 先做 eligibility，再排名：listed、非 ST、非停牌、有 next-open 可执行、满足最小历史长度。
2. 排名信息使用 `same-day close observed` 的 total market cap，membership 从下一交易日生效。
3. 若某天某 bucket 不足配额，取全部并记录 `quota_fill_rate`。
4. 保留 board quota，避免主板大市值股票挤掉 ChiNext 成长股。
5. 加轻量 liquidity floor，例如 20d amount / turnover 下限，避免 top-N 中出现不可交易或成交太薄的边缘样本。
6. 保留当前 fixed-cap universe 作为 sensitivity baseline，用于回答“绝对大市值口径下是否仍成立”。

数据集切分建议分两层。

第一层保留一个主时间切分，用于最终叙事和 holdout：

| role | calendar |
|:--|:--|
| train | 2017-2021 |
| validation | 2022-2023 |
| final robustness / holdout | 2024-2025 |

但所有 event label 看未来 120d，所以 split 边界必须加 purge / embargo。至少应在 split 边界前后排除或隔离 `120` 个 trading sessions，避免一个 event 的 forward label、episode high、first-50 touch 与另一个 split 交叉。

第二层增加 walk-forward diagnostics，用于判断规则是否只适配某个 regime：

| fold | train window | validation window |
|:--|:--|:--|
| F1 | 2017-2019 | 2020 |
| F2 | 2017-2020 | 2021 |
| F3 | 2018-2021 | 2022 |
| F4 | 2019-2022 | 2023 |

`2024-2025` 应作为最终 holdout，不参与 threshold / rule selection。每个 fold 都应同时报告：

```text
episode count
universe-years = sum(daily_member_count) / 252
episodes / 100 universe-years
event count
event-positive rate
any-event recall
+50 bridge recall
density loss
```

这样才能区分三件事：事件结构是否真的有 recall、universe 分母是否稳定、以及模型是否只是吃到了某个年份或 regime 的 beta。

这个 universe / split 问题改变了实验顺序。不能把 multi-channel 04.1 当成直接下一步，因为当前 04 的 denominator 来自 fixed-cap universe；如果 universe 改了，02 的 reverse lifecycle denominator、duration distribution、EMA60 reclaim occurrence、S3/S6 sequence dominance 都需要先重新冻结。否则 04.1 仍然是在旧 opportunity set 上修补事件结构。

### 5.9 根因排序

按可操作性排序，recall 低的主因是：

1. **最终 event channel 与 setup context 没拆开**：E0 是 context，但当前作为 event 与 E1/E2/E4 共用 union density。
2. **20-session earliest-wins density 对 low-axis 不友好**：pre-low E0 抢占簇后，low 后的真正 actionable event 被折叠。
3. **E1/E2/E4 的 family 生成依赖同一 seed/reclaim 链**：它们高度共线，不能提供独立 episode coverage。
4. **event-anchored +50 basis 比 episode-low basis 更严**：尤其对 fast/medium winner，event t0 稍晚就会丢掉 +50 label。
5. **raw pattern 偏 repair/reclaim**：risk-on/transition 的浅回撤或延续型 winner 覆盖不足。
6. **split raw count 受固定市值 PIT universe 尺寸影响**：train 早期 universe 小，导致绝对 episode/event-positive 样本数偏少；但 normalized incidence 显示 robustness 仍是单独偏高的近年 regime。
7. **当前 split 不足以支持单一稳定结论**：需要 top-N universe 对照、purge/embargo、walk-forward diagnostics 和 final holdout 分离。

因此 04 的技术修正方向仍然是 channel architecture，但它不应是立即下一个实验。更合理的顺序是：先基于 01 建立 top-N PIT universe，再在新 universe 上重跑 02，最后才决定是否重写 04 的 candidate generator。

## 6. 如何解读当前 +50 Precision

当前 setup-inclusive density-kept event 的 event-anchored +50 precision 是：

| split | 120d complete | +50 positive | precision |
|:--|--:|--:|--:|
| train | 1,922 | 225 | 11.7% |
| validation | 2,203 | 140 | 6.4% |
| robustness | 1,864 | 400 | 21.5% |
| all | 5,989 | 765 | 12.8% |

这个 precision 对 primary candidate generator 来说不一定致命，因为 primary 这一层本来就是高 recall、低 precision，precision 可以留给 meta layer。

更大的问题是：**即使不要求高 precision，只问 target episode 是否被一个未来还能 +50 的 event 捕获，before-first 也只有 35.2%**。这已经不是“候选池很宽但噪声大”，而是“候选池仍然漏掉太多真正 +50 event”。

## 7. 研究判断

当前 04 的方向是对的：它应该找 event，不是做 primary model，更不是直接交易信号。但当前 union/canonical 结构不适合 high recall，而且当前 fixed-cap universe / split 设计已经足以影响 denominator 与 split 稳定性。

因此本报告的研究判断应拆成两层：

1. **04 层面的技术判断**：E0 应作为 setup context，不应进入与 E1/E2/E4 同一个 union density；E1/E2/E4 应作为独立 event channels，各自做 density；episode-level recall 应聚合多通道命中，而不是强行压成单一 setup-inclusive canonical event。
2. **实验路线判断**：不要直接进入 04.1。下一步应先建立 top-N 400/100 PIT universe，并在新 universe 上重跑 02 reverse lifecycle profile。只有当新的 02 denominator 与 lifecycle sequence 仍支持修复/持续性画像时，才值得重写 04 candidate generator。
3. **诊断口径保留**：`+50 bridge recall` 仍应成为后续 04 rerun 的核心 diagnostic，但它必须基于新 02 冻结 denominator 重新计算。
4. **long bucket 需要复核**：当前 02 显示 long bucket 占 63.6%，低点到高点中位约 110 个交易日；但这个比例可能会随 top-N universe 改变，不能直接继承到下一版 04。

## 8. 下一步建议

建议不要把下一版实验写成 04.1 candidate generator。更合适的实验序列是：

```text
Next experiment:
Build a new PIT top-N universe based on 01:
  main board top 400 by same-day close-observed total market cap
  ChiNext top 100 by same-day close-observed total market cap
  membership usable from next trading session
  keep fixed-cap universe as baseline/sensitivity

Following experiment:
Rerun 02 reverse lifecycle profile on the new top-N universe:
  rebuild target big-winner episode denominator
  report episode count, universe-years, and episodes / 100 universe-years
  rerun lifecycle sequence dominance and split/regime diagnostics
  freeze the new 02 manifest before any 04 rerun

Only after that:
Revisit 04 candidate generator on the new 02 denominator:
  E0 as setup context only
  E1/E2/E4/E5 or new continuation anchors as independent event channels
  evaluate any-event recall and +50 bridge recall
```

新的 top-N universe 实验应至少要求：

```text
daily target universe close to 500 when enough eligible names exist
quota_fill_rate reported by board/year
PIT membership uses close-observed rank and next-session usability
no latest-only market-cap leakage
daily member count, universe-years, and board mix reported by year
overlap with fixed-cap universe reported as sensitivity
```

新的 02 rerun 应至少要求：

```text
target episodes reported by split/year/regime/duration bucket
universe-normalized incidence reported
EMA60 reclaim occurrence rerun
S3/S6 sequence dominance rerun
walk-forward fold diagnostics reported
2024-2025 final holdout not used for threshold or rule selection
```

结论：**04 当前 +50 recall 偏低，但直接继续做 04.1 不合适。下一步应先参照 01 建立 top-N 400/100 PIT universe；再在新 universe 上重跑 02 reverse lifecycle profile，重新冻结 denominator 与生命周期画像；之后才决定如何重写 04 candidate generator。**
