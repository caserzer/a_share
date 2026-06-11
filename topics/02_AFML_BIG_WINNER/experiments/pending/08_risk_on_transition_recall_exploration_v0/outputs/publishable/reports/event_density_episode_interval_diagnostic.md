# Event Density Episode-Interval Diagnostic

## 结论

这份补充统计把 event density 的口径从“按股票/年份的事件频率”切换为“一个 big-winner episode 内部的事件触发间隔”。在这个口径下，R 系列 union 的密度问题更清楚：它不是简单地“全年事件太多”，而是在同一个 episode 的 `before_first_50pct` 窗口内反复触发。

核心结果：

1. `07_E1_canonical_triggered` 很稀疏。全样本 episode 内事件数均值 `0.80`、中位数 `1`、top 10% 仍只有 `1` 个事件；只有 `223 / 2493` 个 episode 出现两个及以上 E1 event。
2. `08_R_core_union_event_regime_gated` 在 episode 内明显密集。全样本 episode 内事件数均值 `4.69`、中位数 `5`、top 10% 为 `8` 个事件；`2160 / 2493` 个 episode 出现两个及以上 R gated event。
3. `risk_on` 中这个现象更直接：R gated 在 `risk_on` episode 内事件数均值 `5.27`、中位数 `5`、top 10% 为 `9` 个事件；相邻触发间隔中位数只有 `4` 个交易日，low 10% 间隔为 `1` 个交易日。
4. 因此，R 系列 density 的主要问题不是覆盖太广，而是同一 episode 内重复触发太密。后续压缩应优先考虑 episode-level de-dup、cooldown、每 episode top-k、或按 episode 内 first/highest-score event 保留，而不是只用全局 density ratio 砍事件。

## 统计口径

Source artifacts：

| artifact | usage |
| --- | --- |
| `07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv` | 07 E1 与 07 full union canonical events |
| `08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_capture.parquet` | 08 frozen episode denominator 与 `before_first_50pct` window |
| `08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz` | 08 R-series event instances |

Episode denominator：

- `candidate_scope_id = 07_e1_only`
- `window = before_first_50pct`
- `any_event_denominator_included = true`
- denominator episode count = `2493`

Event scopes：

| scope | definition | canonicalized event count |
| --- | --- | ---: |
| `07_E1_canonical_triggered` | 07 canonical events whose `triggered_channels` contains `E1_early_ema60_repair` | 6,820 |
| `07_full_recommended_union` | 07 canonical events with `channel_id = E_union_topn_multichannel_recommended` | 15,161 |
| `08_R_core_union_all_variants` | R1/R2/R6/R7/R8 all variants, de-duplicated by `instrument,event_t0_pos` | 61,960 |
| `08_R_core_union_event_regime_gated` | R1/R2/R6/R7/R8 `event_regime_gated`, de-duplicated by `instrument,event_t0_pos` | 47,929 |

统计方法：

1. 对每个 episode，取同一 `instrument` 上落在 `[window_start_pos, window_end_pos]` 内的 event。
2. 按 `event_t0_pos` 排序后统计 episode 内 `event_count`。
3. 如果 episode 内至少有两个 event，则计算相邻 event 的 `event_t0_pos` 差值，单位为交易日。
4. `top 10%` 使用 p90 cutoff；`low 10%` 使用 p10 cutoff。对间隔额外列出 `top10_mean` / `low10_mean`，即 cutoff 外尾部样本的均值。

## 全样本 Episode-Level Density

| scope | episodes | with event | with >=2 events | event mean | event median | event low10 | event top10 | gap samples | gap mean td | gap median td | gap low10 cutoff | gap top10 cutoff | gap low10 mean | gap top10 mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `07_E1_canonical_triggered` | 2,493 | 1,773 | 223 | 0.80 | 1 | 0 | 1 | 228 | 51.30 | 53 | 22 | 78.3 | 16.58 | 87.61 |
| `07_full_recommended_union` | 2,493 | 1,796 | 1,422 | 1.78 | 2 | 0 | 3 | 2,633 | 12.32 | 9 | 5 | 16 | 4.94 | 39.32 |
| `08_R_core_union_all_variants` | 2,493 | 2,386 | 2,277 | 6.17 | 6 | 2 | 11 | 13,008 | 8.06 | 4 | 1 | 21 | 1.00 | 34.57 |
| `08_R_core_union_event_regime_gated` | 2,493 | 2,320 | 2,160 | 4.69 | 5 | 1 | 8 | 9,367 | 9.61 | 4 | 1 | 26 | 1.00 | 42.04 |

Interpretation：

- E1 的 episode 内触发非常稀疏。即使 top 10% episode，也通常只有 1 个 E1 event；E1 的 gap 样本只有 228 个，因为绝大多数 episode 根本没有两个 E1 event。
- 07 full union 把 episode 内事件数提高到中位数 2、top 10% 3，间隔中位数降到 9 个交易日。
- R all variants / R gated 则进入高重复触发区间。R gated 的中位 episode 有 5 个 event，top 10% episode 有 8 个 event，间隔中位数只有 4 个交易日。
- R gated 相比 R all variants 已经减少了一部分事件，但没有改变 episode 内高频触发结构；它降低了事件数量，却仍保留了很短的 episode 内间隔。

## 按 Market Regime 拆分

| scope | regime | episodes | with event | with >=2 events | event mean | event median | event low10 | event top10 | gap samples | gap mean td | gap median td | gap low10 cutoff | gap top10 cutoff | gap low10 mean | gap top10 mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `07_E1_canonical_triggered` | risk_off | 1,580 | 1,247 | 147 | 0.88 | 1 | 0 | 1 | 151 | 53.56 | 57 | 24 | 78 | 17.12 | 86.67 |
| `07_E1_canonical_triggered` | risk_on | 428 | 240 | 26 | 0.62 | 1 | 0 | 1 | 27 | 48.11 | 42 | 19.6 | 83.6 | 12.67 | 87.33 |
| `07_E1_canonical_triggered` | transition | 485 | 286 | 50 | 0.69 | 1 | 0 | 2 | 50 | 46.20 | 40 | 21 | 77 | 18.33 | 82.50 |
| `07_full_recommended_union` | risk_off | 1,580 | 1,263 | 973 | 1.93 | 2 | 0 | 3 | 1,788 | 12.38 | 9 | 5 | 16 | 4.93 | 40.26 |
| `07_full_recommended_union` | risk_on | 428 | 244 | 203 | 1.40 | 1 | 0 | 3 | 354 | 11.92 | 9.5 | 5 | 15 | 4.96 | 21.82 |
| `07_full_recommended_union` | transition | 485 | 289 | 246 | 1.61 | 2 | 0 | 3 | 491 | 12.38 | 10 | 5 | 16 | 4.98 | 38.31 |
| `08_R_core_union_all_variants` | risk_off | 1,580 | 1,539 | 1,462 | 6.35 | 6 | 2 | 11 | 8,491 | 8.11 | 4 | 1 | 21 | 1.00 | 34.69 |
| `08_R_core_union_all_variants` | risk_on | 428 | 415 | 395 | 5.92 | 6 | 2 | 10 | 2,119 | 7.98 | 4 | 1 | 21 | 1.00 | 34.16 |
| `08_R_core_union_all_variants` | transition | 485 | 432 | 420 | 5.84 | 6 | 0 | 10 | 2,398 | 7.92 | 4 | 1 | 20 | 1.00 | 34.14 |
| `08_R_core_union_event_regime_gated` | risk_off | 1,580 | 1,476 | 1,351 | 4.45 | 4 | 1 | 8 | 5,548 | 10.10 | 4 | 1 | 28 | 1.00 | 43.68 |
| `08_R_core_union_event_regime_gated` | risk_on | 428 | 414 | 393 | 5.27 | 5 | 2 | 9 | 1,843 | 8.90 | 4 | 1 | 23.8 | 1.00 | 39.51 |
| `08_R_core_union_event_regime_gated` | transition | 485 | 430 | 416 | 4.96 | 5 | 0 | 9 | 1,976 | 8.89 | 4 | 1 | 24 | 1.00 | 39.43 |

Interpretation：

- R gated 的 episode 内高密度不是 risk_off 独有问题；在 `risk_on` 与 `transition` 中同样存在。
- `risk_on` 中 E1 的 before-first-50pct 覆盖偏弱：只有 `240 / 428` 个 episode 有 E1 event，且只有 `26 / 428` 个 episode 有两个及以上 E1 event。
- `risk_on` 中 R gated 几乎覆盖所有 episode：`414 / 428` 有事件，`393 / 428` 有两个及以上事件。这解释了 R 系列为什么有强 recall，但也解释了为什么直接 union 会造成密度压力。
- `risk_on` 的 R gated 事件数均值 `5.27` 高于 risk_off 的 `4.45`，说明 R 系列在目标 regime 上不是偶然变密，而是系统性地多次触发。

## Risk-On 按 Split 拆分

| scope | split | episodes | with event | with >=2 events | event mean | event median | event low10 | event top10 | gap samples | gap mean td | gap median td | gap low10 cutoff | gap top10 cutoff | gap low10 mean | gap top10 mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `07_E1_canonical_triggered` | robustness | 181 | 89 | 11 | 0.55 | 0 | 0 | 1 | 11 | 52.73 | 48 | 37 | 82 | 35.00 | 82.00 |
| `07_E1_canonical_triggered` | train | 225 | 142 | 12 | 0.68 | 1 | 0 | 1 | 12 | 45.08 | 39 | 13 | 87.8 | 12.67 | 88.00 |
| `07_E1_canonical_triggered` | validation | 22 | 9 | 3 | 0.59 | 0 | 0 | 1.9 | 4 | 44.50 | 44.5 | 31.7 | 57.3 | 29.00 | 60.00 |
| `07_full_recommended_union` | robustness | 181 | 90 | 70 | 1.18 | 0 | 0 | 3 | 123 | 12.94 | 10 | 5 | 17 | 5.00 | 39.93 |
| `07_full_recommended_union` | train | 225 | 145 | 124 | 1.58 | 2 | 0 | 3 | 210 | 11.14 | 8 | 5 | 15 | 4.94 | 20.15 |
| `07_full_recommended_union` | validation | 22 | 9 | 9 | 1.36 | 0 | 0 | 3.9 | 21 | 13.76 | 10 | 5 | 31 | 5.00 | 36.33 |
| `08_R_core_union_all_variants` | robustness | 181 | 171 | 158 | 5.58 | 5 | 1 | 11 | 839 | 8.54 | 3 | 1 | 24 | 1.00 | 38.98 |
| `08_R_core_union_all_variants` | train | 225 | 222 | 215 | 6.15 | 6 | 2.4 | 10 | 1,161 | 7.53 | 4 | 1 | 18 | 1.00 | 29.53 |
| `08_R_core_union_all_variants` | validation | 22 | 22 | 22 | 6.41 | 7 | 3 | 9 | 119 | 8.44 | 5 | 1 | 20.2 | 1.00 | 28.00 |
| `08_R_core_union_event_regime_gated` | robustness | 181 | 171 | 157 | 4.70 | 4 | 1 | 9 | 679 | 10.29 | 4 | 1 | 34.2 | 1.00 | 49.00 |
| `08_R_core_union_event_regime_gated` | train | 225 | 221 | 214 | 5.70 | 6 | 2 | 9 | 1,061 | 8.04 | 4 | 1 | 20 | 1.00 | 32.67 |
| `08_R_core_union_event_regime_gated` | validation | 22 | 22 | 22 | 5.68 | 5 | 2.1 | 9 | 103 | 8.65 | 4 | 1 | 20.8 | 1.00 | 29.27 |

Interpretation：

- `risk_on` train 中，R gated 的中位 episode 有 6 个 event，top 10% episode 有 9 个 event，间隔中位数为 4 个交易日。
- `risk_on` robustness 中，R gated 的事件数中位数降到 4，但 top 10% 仍为 9，说明 out-of-sample 不是没有密度问题，只是高密度分布的形态不同。
- validation risk_on 只有 22 个 episode，不能作为稳定判断；但它给出的方向没有反转：R gated 对 22 个 episode 全部有事件，全部有两个及以上事件，事件数中位数为 5。

## 对 R-Series Density Compression 的含义

这个 episode-interval 统计把 R 系列问题拆得更细：

1. R 系列确实是 risk_on recall 的有效来源。它在 risk_on episode 中几乎总能触发，说明 R family 不是随机噪声。
2. 但直接 union 的形态不适合作为 entry event。一个 episode 内 5-6 次触发、相邻间隔中位数 4 天，会把同一个上涨修复过程重复打很多标签。
3. `event_regime_gated` 已经减少事件总数，但没有把 episode 内重复触发压到类似 07 full union 的水平。07 full union 在 risk_on 的事件数中位数为 1、top 10% 为 3；R gated 是中位数 5、top 10% 为 9。
4. 后续压缩应从 episode-level 控制入手，而不是只继续调 family-level density gate。

优先建议：

| priority | compression idea | reason |
| --- | --- | --- |
| P0 | per-episode cooldown after first selected R event | 直接处理相邻间隔过短的问题 |
| P0 | per-episode top-1 / top-2 by family score | 保留 R 系列强 recall，同时限制同一 episode 多次触发 |
| P1 | per-instrument rolling cooldown, e.g. 20 trading days | 可作为无 episode label 的部署近似 |
| P1 | de-duplicate same mechanism cluster inside episode | 避免 R1/R6/R7/R8 对同一修复阶段重复投票 |
| P2 | global density-ratio threshold | 只能控制全年频率，不能直接保证 episode 内不过密 |

因此，R 系列 density compression 的下一版 requirement 可以把目标从“把 density vs E1 压低”改成更贴近问题本身的 gate：

- `risk_on` episode 内 R-union event count median <= 2。
- `risk_on` episode 内 R-union event count top10 <= 4。
- 相邻 event 间隔 median >= 10 trading days，或同一 episode 内只保留 first/top-score event。
- 在上述限制下，再检查 before-first-50pct recall 与 bridge-positive recall 是否仍显著优于 E1。

这比单纯要求 `density_vs_e1 <= 1.0x` 更可执行，也更符合当前诊断看到的真实密度形态。
