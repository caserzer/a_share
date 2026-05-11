# EP4 R01 V2 高召回 Probe / Fail-Fast 实验报告

- 实验阶段：`ep4_r01_high_recall_probe_fail_fast_v2_money_rps5_boll20_high10_seed`
- 输出目录：`ep4/outputs/r01_high_recall_probe_fail_fast_v2_money_rps5_boll20_high10_seed`
- 生成时间：`2026-05-11T13:35:39.949118+00:00`
- Final decision / 最终决策：`stop_ep4_r01_path`
- validator 口径：schema/artifact 通过；fail-closed validator 因硬门失败而失败
- phase boundary：无训练、无加仓、无组合 sizing、无动态 ATR/state/trailing exit

## 1. 实验定义

本次 V2 固定 candidate seed 为五条件交集：

```text
money_ratio20_gt_1_0
AND money_ratio5_gt_2_0
AND rps5_gt_50
AND boll20_pct_b_gt_1_0
AND close_near_high10_gt_0
```

操作定义：

```text
money_ratio20_T = money_T / mean(money, T-20..T-1)
money_ratio5_T  = money_T / mean(money, T-5..T-1)
rps5_T          = percentile_rank(close_T / close_T-5 - 1)
boll20_pct_b_T  = (close_T - boll20_lower_T) / (boll20_upper_T - boll20_lower_T)
close_near_high10_T = close_T >= max(close, T-10..T-1)
```

当前 fail-fast 规则：

```text
entry = T+1 open
检查 T+1..T+10
若 close < seed_day_low，次日开盘退出
若 close < breakout_reference，次日开盘退出
若 close < pivot_low_10d，次日开盘退出
若 T+10 close < entry_price，次日开盘退出
否则 H20 自然退出
```

本次 V2 也把 matched-random baseline 降为 audit-only。`random_baseline_reliability_status` 仍报告，但不再作为 hard gate。

## 2. 核心结论

本轮结果不能进入 R02。原因不是 recall-cost 失败，也不是 fail-fast 成本控制失败，而是：

1. seed-day density 在 train 和 validation 仍超过 V2 下调后的日级密度上限。
2. validation 的 1 日延迟 matched-delay no-harm 仍失败，说明即时买入相对 T+1 延迟买入仍有追高劣势。
3. matched-random 仍不可靠，但现在只是 audit-only，不再决定 stop。

正向证据也很明确：

- validation recall 从 EP2 的 `17 / 158 = 10.76%` 提升到 `39 / 158 = 24.68%`。
- robustness recall 从 EP2 的 `47 / 241 = 19.50%` 提升到 `75 / 241 = 31.12%`。
- validation 新增捕获 big winner `33` 个，丢失 `6` 个，净新增 `27` 个。
- validation 每新增一个 big winner 的增量亏损为 `3.42R`，低于上限 `5R`。
- validation 每新增一个 big winner 的增量暴露天数为 `215.78`，低于上限 `250`。
- fail-fast 相比 no-fail-fast 明显降低亏损和持仓时间：validation 失败 seed 平均亏损降低 `0.0896R`，中位持仓天数从 `22` 降到 `11`。

因此，本轮不是“方向完全无效”，而是“当前 seed 仍偏密、即时入场仍偏早，尚不足以通过 R01 hard gate”。

## 3. Reference Windows

| split | effective reference window | big winner count | unique instruments | forward return p50 |
|:--|:--|--:|--:|--:|
| train | 2017-07-04..2021-12-31 | 446 | 205 | 0.5453 |
| validation | 2022-01-01..2023-12-31 | 158 | 127 | 0.5293 |
| robustness | 2024-01-01..2025-10-31 | 241 | 170 | 0.5357 |

robustness 的 effective end 是 `2025-10-31`，因为本地数据到 `2026-04-30`，需要保留 120 trading days forward window。

## 4. Seed Density

| split | family | eligible stock-days | executable seed-days | seed episodes | seed-day rate | episode rate | seed-day vs EP2 | episode vs EP2 |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|
| train | candidate | 179135 | 3161 | 2087 | 0.017646 | 2.9857 | 2.7511 | 1.8164 |
| train | EP2 bridge | 179135 | 1149 | 1149 | 0.006414 | 1.6438 | 1.0000 | 1.0000 |
| validation | candidate | 107845 | 1622 | 1070 | 0.015040 | 2.3884 | 3.0489 | 2.0113 |
| validation | EP2 bridge | 107845 | 532 | 532 | 0.004933 | 1.1875 | 1.0000 | 1.0000 |
| robustness | candidate | 108406 | 1761 | 1167 | 0.016244 | 2.6644 | 2.4873 | 1.6483 |
| robustness | EP2 bridge | 108406 | 708 | 708 | 0.006531 | 1.6164 | 1.0000 | 1.0000 |

V2 将日级密度 cap 从 `3.0 * EP2` 下调到 `2.7 * EP2`，所以当前失败变得更严格：

| split | candidate seed-day rate | active cap | utilization | status |
|:--|--:|--:|--:|:--|
| train | 0.017646 | 0.017318 | 101.89% | failed |
| validation | 0.015040 | 0.013319 | 112.92% | failed |
| robustness | 0.016244 | 0.017634 | 92.12% | passed |

发现：validation 的 seed-day count 是 EP2 的 `3.05x`，但新 cap 只允许 `2.7x`。这说明当前五条件 seed 已经比纯 money/RPS5 窄很多，但仍未达到 V2 新密度纪律。

## 5. Big Winner Recall

| split | family | reference count | captured | missed | recall | diff vs EP2 |
|:--|:--|--:|--:|--:|--:|--:|
| train | candidate | 446 | 178 | 268 | 39.91% | +15.02 pp |
| train | EP2 bridge | 446 | 111 | 335 | 24.89% | 0 |
| validation | candidate | 158 | 39 | 119 | 24.68% | +13.92 pp |
| validation | EP2 bridge | 158 | 17 | 141 | 10.76% | 0 |
| robustness | candidate | 241 | 75 | 166 | 31.12% | +11.62 pp |
| robustness | EP2 bridge | 241 | 47 | 194 | 19.50% | 0 |

发现：

- candidate 不是极高 recall seed，但相对 EP2 在三个 split 都有稳定 recall 增量。
- validation recall 只有 `24.68%`，说明五条件交集已经明显牺牲覆盖率；它更像“质量提升后的观察权入口”，不是 broad discovery seed。
- robustness recall 反而高于 validation，说明这个 seed 没有明显只在 validation 偶然有效。

## 6. Recall-Cost Tradeoff

| split | candidate failed loss R | EP2 failed loss R | added capture | lost capture | net added | loss R / added winner | exposure days / added winner | status |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| train | 321.59 | 162.15 | 95 | 33 | 62 | 2.57 | 194.37 | passed |
| validation | 175.17 | 82.83 | 33 | 6 | 27 | 3.42 | 215.78 | passed |
| robustness | 155.70 | 89.50 | 54 | 11 | 43 | 1.54 | 120.40 | passed |

关键解读：

- validation 的成本边界通过：`3.42R <= 5R`，`215.78 <= 250 days`。
- robustness 成本更好：`1.54R / added winner`，`120.40 exposure days / added winner`。
- 这支持“fail-fast 后买观察权的成本可能可控”，但不支持“当前 seed 可以直接进入 R02”，因为密度和即时入场门仍失败。

## 7. Fail-Fast 行为

| split | episodes | natural H20 | structure-only exit | exits including T+10 entry-price trigger | median holding days | mean holding days |
|:--|--:|--:|--:|--:|--:|--:|
| train | 1568 | 670 | 600 | 298 | 11 | 13.69 |
| validation | 739 | 288 | 302 | 149 | 11 | 13.01 |
| robustness | 829 | 324 | 316 | 189 | 11 | 13.14 |

validation 触发明细：

| trigger type | count |
|:--|--:|
| `natural_exit_h20` | 288 |
| `close_below_breakout_reference` | 129 |
| `close_below_seed_day_low` | 35 |
| `close_below_seed_day_low|close_below_breakout_reference` | 134 |
| `close_below_seed_day_low|close_below_breakout_reference|close_below_pivot_low_10d` | 4 |
| `t10_close_below_entry_price` | 136 |
| other trigger combinations containing T+10 | 13 |

发现：

- 新增 `T+10 close < entry_price` 非常关键。validation 中纯 T+10 退出 `136` 次，加上组合触发共 `149` 次，占 validation candidate probe episodes 的约 `20.2%`。
- 该规则把典型 holding days 从 H20 拉到中位数 `11`，这是本轮成本门能够通过的重要原因。
- fail-fast 不是只靠结构破位；T+10 的时间止损承担了大量“没有明显结构破位但观察权失败”的退出。

## 8. Fail-Fast 错误审计

| split | false reject winner | missed failure |
|:--|--:|--:|
| train | 97 | 183 |
| validation | 31 | 110 |
| robustness | 59 | 84 |

validation 错误样本均值：

| error type | count | mean return R | median return R | mean loss R | median loss R | median initial risk pct |
|:--|--:|--:|--:|--:|--:|--:|
| false_reject_winner | 31 | -0.331 | -0.338 | 0.331 | 0.338 | 0.045 |
| missed_failure | 110 | -0.287 | -0.243 | 0.287 | 0.243 | 0.038 |

解释：

- false reject winner 表示 fail-fast 退出后，该 seed 仍对应 primary big winner 参考事件。这是 fail-fast 的机会成本。
- missed failure 表示 fail-fast 没能提前处理的失败观察权，最终仍表现为负。
- validation 里 false reject winner `31` 个，不算低；这提示 T+10 时间止损虽然降低暴露，但可能切掉一部分后续 winner 的早期波动。

## 9. Matched Baselines

validation 与 no-fail-fast 对比：

| baseline | mean R diff | p05 R diff | failed loss R diff | failed holding days diff |
|:--|--:|--:|--:|--:|
| same seed no fail-fast H20 | +0.0499 | +0.6434 | -0.0896 | -11 |

validation 与 same-fail-fast 延迟入场对比：

| baseline | candidate mean R | baseline mean R | diff | threshold | status |
|:--|--:|--:|--:|--:|:--|
| delay 1d same fail-fast | -0.1275 | -0.1204 | -0.00713 | -0.0055 | failed |
| delay 3d same fail-fast | -0.1275 | -0.1242 | -0.00332 | -0.0050 | passed |

1 日延迟失败的补充证据：

| metric | candidate | delay 1d | diff |
|:--|--:|--:|--:|
| p05 return R | -0.5840 | -0.5458 | -0.0381 |
| failed seed average loss R | 0.2506 | 0.2355 | +0.0151 |
| failed seed median holding days | 11 | 11 | 0 |

发现：

- fail-fast 相比 no-fail-fast 是明确有效的。
- 但即时 entry 相比延迟 1 日仍略差，且差在 mean、p05 和 failed loss 三个方向都一致。
- 这说明 seed 触发日可能仍带有“冲高确认当天偏热”的问题。R01 当前不应把这个 entry timing 视为已经通过。

## 10. Matched-Random Reliability / Audit

matched-random 已按 V2 requirement 降为 audit-only。当前 reliability 仍失败，但不再是 hard gate。

| split | baseline | failed buckets | passed buckets |
|:--|:--|--:|--:|
| train | no fail-fast random | 409 | 12 |
| train | same fail-fast random | 409 | 12 |
| validation | no fail-fast random | 297 | 4 |
| validation | same fail-fast random | 297 | 4 |
| robustness | no fail-fast random | 274 | 4 |
| robustness | same fail-fast random | 274 | 4 |

validation bucket eligible rate：

| baseline | bucket count | mean | min | p25 | median | p75 | max |
|:--|--:|--:|--:|--:|--:|--:|--:|
| no fail-fast random | 301 | 0.2396 | 0.0000 | 0.1450 | 0.2244 | 0.3275 | 0.7050 |
| same fail-fast random | 301 | 0.2397 | 0.0000 | 0.1450 | 0.2244 | 0.3275 | 0.7050 |

解读：

- random baseline 不是输赢问题，而是“随机对照样本经过 valid stop / risk distance / executable 过滤后太稀”。
- 它不能支持 go，也不能作为 stop 的 hard reason。
- 这个结果更像说明：结构化 fail-fast 的 random 对照需要重新设计，不能拿全随机 stock-day 直接套同一结构 stop 口径。

## 11. R-Unit 与风险距离

candidate validation 的 risk distribution：

| probe budget | initial risk p05 | median initial risk | initial risk p95 | return R p01 | return R p99 | failed seed avg loss R |
|:--|--:|--:|--:|--:|--:|--:|
| 0.10R | 0.0221 | 0.0393 | 0.0855 | -0.3084 | 0.6537 | 0.1007 |
| 0.25R | 0.0221 | 0.0393 | 0.0855 | -0.7710 | 1.6342 | 0.2517 |
| 0.50R | 0.0221 | 0.0393 | 0.0855 | -1.5420 | 3.2683 | 0.5034 |

发现：

- candidate 的 initial risk median 约 `3.93%`，处于 `[2%, 12%]` 风险距离约束内。
- probe budget 对 R 分布是线性缩放；当前结论主要来自价格路径和 stop 结构，不来自资金权重优化。
- near-risk-floor extreme loss share 为 `3.59%`，没有显示损失改善主要由 2% 风险下限附近的异常样本驱动。

## 12. Gate Evidence

当前失败项：

| gate | split | value | threshold | hard gate | interpretation |
|:--|:--|--:|--:|:--|:--|
| seed_density_day_cap | train | 0.017646 | 0.017318 | true | 日级触发密度略超 V2 cap |
| seed_density_day_cap | validation | 0.015040 | 0.013319 | true | validation 日级密度超过 V2 cap 约 12.9% |
| matched_delay_1d_mean_no_harm | validation | -0.007128 | -0.0055 | true | 即时 entry 比 1 日延迟 entry 差，超过容忍线 |
| random_baseline_reliability_status | validation | failed | passed | false | audit-only；不能作为 go 证据，也不造成 stop |

已通过的重要 hard gates：

- authority inputs passed。
- no validation threshold selection。
- validation / robustness recall no-harm passed。
- validation cost vs no-fail-fast passed。
- validation holding days vs no-fail-fast passed。
- validation p05 vs no-fail-fast passed。
- matched-delay reliability passed。
- matched-delay 3d mean no-harm passed。
- validation added capture、net capture、recall-cost score、loss bound、exposure bound 全部 passed。

## 13. 主要发现

1. **T+10 entry-price fail-fast 是有效补丁。**
   它让 validation 中位持仓天数降到 `11`，并让 exposure bound 通过。没有这条时间止损，fail-fast 更像“结构破位止损”，对横盘失败样本覆盖不足。

2. **当前 seed 是“较窄的质量入口”，不是 high-recall discovery seed。**
   validation recall `24.68%`，robustness recall `31.12%`，相对 EP2 有增量，但远低于早期 pre60 条件搜索中的 broad coverage。

3. **成本控制比 entry timing 更健康。**
   validation recall-cost、loss bound、exposure bound 都过；失败集中在 density 和 1d matched-delay。

4. **即时买入仍偏早。**
   delay 1d 的 same-fail-fast mean R 比即时买入好 `0.00713R`，且 p05 和 failed loss 也更好。这不像随机噪声单点，而像 seed 触发日存在短线过热。

5. **random baseline 当前只适合做诊断，不适合做 hard gate。**
   validation random eligible rate 中位数仅 `22.44%`，比较结果受结构 stop eligibility 影响过大。

## 14. 猜测与待验证方向

以下是基于本次数据的假设，不是已证明结论：

1. **T 日突破确认后，T+1 open 可能仍有追高溢价。**
   1 日延迟更好，说明入场点可能需要从“信号后次日开盘”改成“信号后等待一天、或等待回踩不破、或使用更保守的执行价格”。

2. **密度失败可能来自行情集中的放量突破日。**
   train 和 validation 的 seed-day cap 失败，但 episode cap 通过，说明问题更偏向日级触发聚集，而不是全年 episode 完全失控。

3. **五条件 seed 的结构条件可能仍不够区分真突破与短线冲高。**
   `boll20_pct_b > 1` 和 10 日新高会捕捉强动量，但也容易捕捉短期拉升末端。matched-delay 1d 失败支持这个猜测。

4. **fail-fast 还有 false reject winner 风险。**
   validation false reject winner `31` 个。T+10 规则降低成本，但可能切掉一部分右尾。这需要后续在 R02 前独立审计“被 T+10 切掉后又成 winner”的样本。

5. **random baseline 需要结构化 random，而不是全随机 stock-day。**
   如果未来仍要 random baseline，可考虑只从“同样具备 valid structure stop 且 risk distance 合格”的 stock-day 池抽样；否则 random eligible rate 太低，比较没有解释力。

## 15. R02 Handoff / 当前结论

本轮 V2 不应进入 R02。最小理由是：

```text
hard failed gates:
  seed_density_day_cap on train
  seed_density_day_cap on validation
  matched_delay_1d_mean_no_harm on validation
```

但本轮也不应被解读为 seed / fail-fast 方向失败。更准确的结论是：

```text
五条件 seed + T+10 fail-fast 已经让观察权成本进入可讨论区间；
但 seed 仍偏密，且 T+1 open 即时买入仍有短线过热问题。
下一步若继续，应优先研究 entry timing / trigger density，而不是继续加强 fail-fast。
```

R02 不应在当前 `stop_ep4_r01_path` 决策下启动；需要新的 requirement 明确是继续调 seed density、改 entry timing，还是把本路径归档为 cost-control diagnostic sleeve。
