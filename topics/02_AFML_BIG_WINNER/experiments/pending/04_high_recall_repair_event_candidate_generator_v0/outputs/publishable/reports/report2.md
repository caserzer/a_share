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

## 5. 如何解读当前 +50 Precision

当前 setup-inclusive density-kept event 的 event-anchored +50 precision 是：

| split | 120d complete | +50 positive | precision |
|:--|--:|--:|--:|
| train | 1,922 | 225 | 11.7% |
| validation | 2,203 | 140 | 6.4% |
| robustness | 1,864 | 400 | 21.5% |
| all | 5,989 | 765 | 12.8% |

这个 precision 对 primary candidate generator 来说不一定致命，因为 primary 这一层本来就是高 recall、低 precision，precision 可以留给 meta layer。

更大的问题是：**即使不要求高 precision，只问 target episode 是否被一个未来还能 +50 的 event 捕获，before-first 也只有 35.2%**。这已经不是“候选池很宽但噪声大”，而是“候选池仍然漏掉太多真正 +50 event”。

## 6. 研究判断

当前 04 的方向是对的：它应该找 event，不是做 primary model，更不是直接交易信号。但当前 union/canonical 结构不适合 high recall。

最关键的修正方向不是继续加过滤，而是拆通道：

1. E0 作为 setup context，不应进入与 E1/E2/E4 同一个 union density。
2. E1/E2/E4 应作为独立 event channels，各自做 density。
3. episode-level recall 应聚合多通道命中，而不是强行压成单一 setup-inclusive canonical event。
4. `+50 bridge recall` 应成为 05 或 04.1 的核心 diagnostic：既看 any-event recall，也看 captured event 自身是否仍有 +50 upside。
5. 对 long bucket 应单独保留更长候选窗口，因为 02 显示 long bucket 占 63.6%，低点到高点中位约 110 个交易日。

## 7. 下一步建议

建议下一版实验目标写成：

```text
Build a multi-channel high-recall event candidate pool:
E0 is setup context only.
E1/E2/E4 are independent event channels.
Recall is evaluated both episode-anchored and +50 event-anchored bridge recall.
Density is controlled per channel before episode-level union.
```

成功标准不应只看 low+30 或 before-first any-event recall，还应要求：

```text
before-first-50pct any-event recall >= 0.70
before-first-50pct +50 bridge recall materially above current 35.2%
density loss from channel-level dedup must be explicitly bounded
```

结论：**04 当前 +50 recall 偏低；主要原因是 E0 与后续修复/质量事件在同一 union density 中竞争，导致 high-recall 候选池被过度折叠。下一步应做 multi-channel candidate generator，而不是继续收紧过滤。**
