# Big Winner Path-Archetype 只读统计 Profiling 报告

decision: `big_winner_archetype_profiling_statistics_complete`

## 0. 结论摘要

本次 profiling 在 PIT executable universe 内完成，主分母为 09A 中 `event_big_winner_120d_label = true` 且 `horizon_complete_120d = true`、并能在 `pit_largecap_main_chinext` 中用 `instrument + trade_open_date` 匹配的 winner。最终 PIT-filtered profiling_scope 有 3075 个 winner，qfq forward path 覆盖率为 1.0000，`winner_basis_mismatch_rate = 0.0000`，因此统计口径完整。

最重要的修正是 regime 口径：`path_regime_state` 优先使用 09A `episode_regime_bucket`，若缺失则用同一行的 `event_regime_bucket` 回填。本次 3075 个 PIT winner 中，2384 行来自 episode regime，691 行使用 event fallback，占 22.47%；`unresolved_missing = 0`。因此主表只保留 `risk_on / risk_off / transition` 三类 regime，不再把可分类 winner 错放到 missing bucket。

核心发现：

1. big winner 并不是单一快涨形态。`day_to_target` 中位数为 58 个交易 session，p90 为 107；只有 11.87% 在 20 日内达到 +50%，25.04% 落在 90-120 日区间。
2. risk regime 的差异主要体现在 risk_on：risk_on winner 到达 +50% 更慢、target 前回撤更深。risk_on `day_to_target` p50 为 65，高于 risk_off 的 56 和 transition 的 52；risk_on `max_drawdown_to_target` p50 为 -18.03%，深于 risk_off 的 -15.80%。
3. split drift 中最明显的是 gap/open-return 风格迁移。train vs robustness 在 `max_gap_open_return_to_target` 上 KS=0.2713，是所有迁移读数中最大；robustness 的 gap 更强，train 更弱。
4. 10C rejected injury winners 更集中在 shakeout / volatile chop / gap-event seed 上，而不是 late bloomer 或 early momentum。全量 injury_scope 中 105 个 10C rejected winners，shakeout bucket 吸收 58 个，injury concentration lift=0.2529。
5. E1-missed 与 shakeout 的关系最强：shakeout bucket 中 P(E1_missed|bucket)=0.5627，Jaccard=0.2987。bridge_winner 与 gap/event-driven 的重合最高：Jaccard=0.4566，P(bridge|bucket)=0.7641。
6. 本报告仍然只支持 readout，不支持冻结 archetype。原因是 seed flags 是 Appendix A 先验，且多个 bucket 大量重叠：20.10% winner 没有任何 seed flag，41.98% 只有一个，37.92% 同时命中两个或更多。

## 1. 如何阅读本报告

### 1.1 Population 与 denominator

| population | denominator | 用途 | 本次样本数 |
|---|---:|---|---:|
| raw 09A winner candidate | 09A winner label true 且 120d horizon complete | PIT 过滤前候选池 | 7187 |
| profiling_scope | raw 09A winner candidate inner join PIT executable universe | Q1/Q2 path 分布、split/regime migration、seed readout | 3075 |
| non-PIT excluded winner | raw 09A winner candidate 未匹配 PIT universe | 只进入 exclusion audit，不进入主统计 | 4112 |
| raw 10A injury winner | 10A default injury scope 中 winner | PIT 过滤前 injury 候选池 | 2647 |
| PIT-filtered injury_scope | raw 10A injury winner 回连到 PIT-filtered 09A profiling row | Q3/Q4 injury concentration、E1/bridge alignment | 1092 |
| injury non-PIT excluded | raw 10A injury winner 无法回连 PIT profiling row | 只进入 exclusion audit | 1555 |

PIT 过滤很强：09A winner 中 57.21% 被排除，10A injury winner 中 58.75% 被排除。后续所有主统计都以 PIT-filtered row 为分母，不能把非 PIT rows 混回 `all`。

### 1.2 Reporting dimensions

| dimension | 取值 | 含义 |
|---|---|---|
| `split` | `all / train / validation / robustness` | 时间或 OOS 分层。`all` 是全量 PIT winner 主读数；其它 split 用来观察迁移，不用于选阈值。 |
| `path_regime_state` | `all / risk_on / risk_off / transition` | path 主 regime axis。`all` 为总分母；三类 regime 用于比较市场状态下的 winner path 差异。 |
| `path_regime_source` | `episode_regime_bucket / event_regime_bucket_fallback` | regime 来源审计。fallback 只是 provenance，不是新 regime。 |
| `reporting_view` | `split_only / regime_only / split_regime` | `split_only` 固定 regime=all；`regime_only` 固定 split=all；`split_regime` 同时切 split 与 regime。 |
| `power_flag` | `ok / low_power` | cell 样本量是否足够写观察。low_power cell 不能解释为结构性结论。 |

### 1.3 Path metrics 与单位

所有 path metrics 都来自 qfq daily bars，`d=1` 是 `trade_open_date` 后第一个交易 session。`trade_open_price` 是 qfq open，winner target 是从 labels.yaml 读取的 `winner_120.right_tail_threshold_pct = 0.50`。

| metric | 含义 | 解释方式 |
|---|---|---|
| `day_to_target` | 首次达到 +50% high-return 的交易 session | 越小表示 winner 更快兑现。 |
| `day_to_confirm` | 首次达到 confirm upper barrier +12% 的交易 session | 用于观察早期确认速度。 |
| `deepest_pre_target_ret_low` | 到达 +50% 之前，以入场 open 为基准的最低 low-return | 越负表示 target 前 shakeout 越深。 |
| `max_drawdown_to_target` | target 前从 running high 到 low 的最大回撤 | 衡量 winner path 内部回吐压力。 |
| `deepest_ret_low_20` | 前 20 session 最低 low-return | 对应 early shakeout 条件。 |
| `max_single_day_close_return_to_target` | target 前最大单日 close return | 衡量单日点火强度。 |
| `max_gap_open_return_to_target` | target 前最大 open gap return | 衡量跳空/事件驱动强度。 |
| `limit_like_up_day_count_to_target` | target 前接近涨停的日数，按 board proxy 判断 | 衡量连续强势或涨停链。 |
| `mfe_*_recomputed` | 20/60/120 session high-return 最大值 | forward favorable excursion。 |
| `mae_*_recomputed` | 20/60/120 session low-return 最小值 | forward adverse excursion。 |

### 1.4 Injury / alignment 指标

| metric | 含义 |
|---|---|
| `injury_rate` | bucket 内 10C rejected winner / bucket winner |
| `share_of_injury` | bucket 吸收的 rejected winners 占全部 rejected winners 的比例 |
| `share_of_winner` | bucket winner 占 injury_scope winner 的比例 |
| `injury_concentration_lift` | `share_of_injury - share_of_winner`；正数表示 rejected winners 在该 bucket 超配 |
| `jaccard` | bucket 与 E1/bridge target 的交并比 |
| `phi` | 2x2 association coefficient |
| `P(target|bucket)` | bucket 内 target 发生率 |
| `P(bucket|target)` | target 样本中落入 bucket 的比例 |

## 2. 数据覆盖与输入质量

| item | value |
|---|---:|
| PIT universe rows | 470682 |
| PIT unique join keys | 470682 |
| PIT duplicate join keys | 0 |
| PIT missing join keys | 0 |
| raw 09A rows | 41937 |
| raw 09A winner candidates | 7187 |
| PIT-filtered profiling winners | 3075 |
| non-PIT winner exclusions | 4112 |
| raw 10A rows | 200250 |
| raw 10A injury winners | 2647 |
| PIT-filtered injury winners | 1092 |
| injury non-PIT exclusions | 1555 |
| qfq source kind | 3075 / 3075 from `qfq_dir` |
| board proxy status | 3075 / 3075 `ok` |
| board buckets | main_board 1964, chinext_star 1108, st 3 |

所有 3075 个 PIT winner 都有可解析 120-session qfq path；所有 path metric 的 missing_rate 都是 0。ST / board limit proxy 也全部可评估。逐日 path 以 qfq daily bars 为权威来源。

## 3. Regime fallback 审计

| path_regime_source | winner_n | rate |
|---|---:|---:|
| episode_regime_bucket | 2384 | 0.7753 |
| event_regime_bucket_fallback | 691 | 0.2247 |

`event_regime_bucket_fallback` 主要落在 risk_on：691 个 fallback 中，685 个为 risk_on，6 个为 risk_off，0 个为 transition。若不做 fallback，这 691 个 winner 会进入 missing bucket，risk_on 分布会被严重低估。

| split | path_regime_state | episode source | event fallback | total |
|---|---:|---:|---:|---:|
| train | risk_on | 173 | 215 | 388 |
| train | risk_off | 437 | 3 | 440 |
| train | transition | 252 | 0 | 252 |
| validation | risk_on | 6 | 47 | 53 |
| validation | risk_off | 139 | 3 | 142 |
| validation | transition | 39 | 0 | 39 |
| robustness | risk_on | 404 | 423 | 827 |
| robustness | risk_off | 811 | 0 | 811 |
| robustness | transition | 123 | 0 | 123 |

解释：validation risk_on 只有 53 个 winner，其中 47 个来自 event fallback；如果保留旧逻辑，validation risk_on 几乎会被抽空。这会直接改变不同 regime 下 big winner 的形态结论。因此 fallback 不是 cosmetic fix，而是分布口径修复。

## 4. 主样本结构

### 4.1 Split × regime winner count

| split | risk_on | risk_off | transition | total |
|---|---:|---:|---:|---:|
| train | 388 | 440 | 252 | 1080 |
| validation | 53 | 142 | 39 | 234 |
| robustness | 827 | 811 | 123 | 1761 |

### 4.2 Regime 总分布

| path_regime_state | winner_n | rate |
|---|---:|---:|
| risk_off | 1393 | 0.4530 |
| risk_on | 1268 | 0.4124 |
| transition | 414 | 0.1346 |

risk_off 与 risk_on 样本量接近，transition 明显更小。validation 总量只有 234，且 validation risk_on / transition 分别只有 53 / 39，因此这些 joint cells 只能作为观察。

## 5. 全量 path 分布

| metric | mean | p25 | p50 | p75 | p90 | p95 | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| day_to_confirm | 21.55 | 5.00 | 13.00 | 30.00 | 57.00 | 73.00 | 1.00 | 118.00 |
| day_to_target | 60.62 | 32.00 | 58.00 | 90.00 | 107.00 | 114.00 | 2.00 | 120.00 |
| deepest_pre_target_ret_low | -0.0700 | -0.1095 | -0.0567 | -0.0199 | 0.0064 | 0.0281 | -0.4310 | 0.2604 |
| max_drawdown_to_target | -0.1811 | -0.2223 | -0.1675 | -0.1293 | -0.1054 | -0.0928 | -0.4789 | 0.0000 |
| deepest_ret_low_20 | -0.0589 | -0.0913 | -0.0488 | -0.0165 | 0.0102 | 0.0320 | -0.4158 | 0.2594 |
| max_single_day_close_return_to_target | 0.1199 | 0.0998 | 0.1002 | 0.1446 | 0.1999 | 0.2001 | 0.0448 | 0.3749 |
| max_gap_open_return_to_target | 0.0614 | 0.0352 | 0.0499 | 0.0756 | 0.1001 | 0.1384 | 0.0004 | 0.3559 |
| limit_like_up_day_count_to_target | 1.2039 | 0.00 | 1.00 | 2.00 | 3.00 | 4.00 | 0.00 | 9.00 |
| mfe_20_recomputed | 0.2375 | 0.0822 | 0.1726 | 0.3305 | 0.5331 | 0.6426 | -0.0980 | 1.7247 |
| mfe_60_recomputed | 0.5738 | 0.2869 | 0.5067 | 0.6956 | 1.0698 | 1.4475 | -0.0535 | 3.5116 |
| mfe_120_recomputed | 0.9685 | 0.6034 | 0.7694 | 1.0884 | 1.6095 | 2.1467 | 0.5000 | 4.9372 |
| mae_20_recomputed | -0.0595 | -0.0913 | -0.0488 | -0.0165 | 0.0100 | 0.0305 | -0.4158 | 0.2155 |
| mae_60_recomputed | -0.0726 | -0.1112 | -0.0576 | -0.0219 | 0.0039 | 0.0236 | -0.4495 | 0.2155 |
| mae_120_recomputed | -0.0795 | -0.1219 | -0.0623 | -0.0241 | 0.0017 | 0.0198 | -0.5753 | 0.2155 |

### 5.1 Day-to-target histogram

| day_to_target bin | winner_n | rate |
|---|---:|---:|
| [0,20) | 365 | 0.1187 |
| [20,40) | 635 | 0.2065 |
| [40,60) | 559 | 0.1818 |
| [60,90) | 746 | 0.2426 |
| [90,120) | 770 | 0.2504 |

Insight：winner 的兑现速度呈长尾。真正 20 日内迅速达到 +50% 的只占 11.87%；90 日后才达到 target 的占 25.04%。因此如果后续 archetype 只围绕“快速点火”设计，会漏掉相当一部分 late realization winners。

### 5.2 Pre-target drawdown histogram

| deepest_pre_target_ret_low bin | winner_n | rate |
|---|---:|---:|
| [-1,-0.3) | 44 | 0.0143 |
| [-0.3,-0.2) | 182 | 0.0592 |
| [-0.2,-0.12) | 438 | 0.1424 |
| [-0.12,-0.08) | 441 | 0.1434 |
| [-0.08,-0.04) | 736 | 0.2393 |
| [-0.04,0) | 834 | 0.2712 |
| [0,0.5) | 400 | 0.1301 |

Insight：target 前有相当多 winner 经历过明显回撤。以 failure lower -8% 看，`deepest_pre_target_ret_low <= -0.08` 的样本为 1105 / 3075 = 35.93%。这说明“触及 failure-like drawdown 但后来成为 winner”的路径不是边缘现象。

## 6. Split 维度读数

| split | winner_n | day_to_target p50 | day_to_target p90 | deepest_pre_target_ret_low p50 | max_drawdown_to_target p50 | max_gap_open_return_to_target p50 |
|---|---:|---:|---:|---:|---:|---:|
| all | 3075 | 58.00 | 107.00 | -0.0567 | -0.1675 | 0.0499 |
| train | 1080 | 60.00 | 110.00 | -0.0591 | -0.1665 | 0.0413 |
| validation | 234 | 56.00 | 101.00 | -0.0388 | -0.1578 | 0.0430 |
| robustness | 1761 | 58.00 | 105.00 | -0.0556 | -0.1705 | 0.0563 |

Split 之间的 `day_to_target` 并没有剧烈漂移，p50 都在 56-60 之间。最大的 split 风格差异来自 gap/open-return：robustness 的 `max_gap_open_return_to_target` p50=5.63%，高于 train 的 4.13%。style migration 中 train vs robustness 的 gap KS=0.2713，是全表最大读数。

## 7. Regime 维度读数

| regime | winner_n | day_to_target p50 | day_to_target p90 | deepest_pre_target_ret_low p50 | max_drawdown_to_target p50 | max_gap_open_return_to_target p50 |
|---|---:|---:|---:|---:|---:|---:|
| all | 3075 | 58.00 | 107.00 | -0.0567 | -0.1675 | 0.0499 |
| risk_on | 1268 | 65.00 | 111.00 | -0.0722 | -0.1803 | 0.0511 |
| risk_off | 1393 | 56.00 | 103.00 | -0.0426 | -0.1580 | 0.0493 |
| transition | 414 | 52.00 | 104.00 | -0.0595 | -0.1595 | 0.0478 |

Risk-on winner 的特征不是更快，而是“更慢且更能承受深回撤”：`day_to_target` p50 比 risk_off 高 9 天，`deepest_pre_target_ret_low` p50 深 2.96 pct，`max_drawdown_to_target` p50 深 2.23 pct。risk_on vs risk_off 在 `deepest_pre_target_ret_low` 上 KS=0.2275、standardized mean delta=-0.6101，是 regime pairwise 中最强差异。

Transition 的样本量较小但仍满足 power floor。它的 `day_to_target` p50=52，快于 risk_on/risk_off；但 transition 本身是 residual regime，后续若要做机制归因，需要进一步拆成 sub-regime。

## 8. Split × regime 细分读数

| split | regime | winner_n | day_to_target p50 | day_to_target p90 | max_drawdown_to_target p50 | max_gap_open_return_to_target p50 | power |
|---|---|---:|---:|---:|---:|---:|---|
| train | risk_on | 388 | 72.00 | 113.00 | -0.1783 | 0.0422 | ok |
| train | risk_off | 440 | 58.00 | 110.00 | -0.1581 | 0.0413 | ok |
| train | transition | 252 | 48.00 | 101.00 | -0.1561 | 0.0405 | ok |
| validation | risk_on | 53 | 36.00 | 59.00 | -0.1785 | 0.0402 | low_power |
| validation | risk_off | 142 | 74.00 | 102.90 | -0.1372 | 0.0504 | ok |
| validation | transition | 39 | 61.00 | 104.00 | -0.1646 | 0.0485 | low_power |
| robustness | risk_on | 827 | 64.00 | 110.00 | -0.1806 | 0.0565 | ok |
| robustness | risk_off | 811 | 52.00 | 96.00 | -0.1624 | 0.0549 | ok |
| robustness | transition | 123 | 66.00 | 106.00 | -0.1690 | 0.0696 | ok |

Validation 的 risk_on p50=36 看起来很快，但该 cell 只有 53 个 winner，且 47 个来自 event fallback，必须作为低样本观察。更稳健的结论来自 train/robustness：risk_on 在两个大 split 中都比 risk_off 更慢、回撤更深。

## 9. Style migration 重点

| comparison | metric | winner_n | baseline_n | KS | standardized_mean_delta | p50_delta | p90_delta | power |
|---|---|---:|---:|---:|---:|---:|---:|---|
| train_vs_robustness | max_gap_open_return_to_target | 1080 | 1761 | 0.2713 | -0.4548 | -0.0150 | -0.0178 | ok |
| validation_vs_robustness | max_gap_open_return_to_target | 234 | 1761 | 0.2276 | -0.2860 | -0.0133 | -0.0102 | ok |
| risk_on_vs_risk_off | deepest_pre_target_ret_low | 1268 | 1393 | 0.2275 | -0.6101 | -0.0297 | -0.0059 | ok |
| risk_on_vs_risk_off | max_drawdown_to_target | 1268 | 1393 | 0.1710 | -0.4803 | -0.0223 | -0.0089 | ok |
| train_vs_all | max_gap_open_return_to_target | 1080 | 3075 | 0.1592 | -0.3066 | -0.0086 | -0.0072 | ok |
| validation_vs_all | max_drawdown_to_target | 234 | 3075 | 0.1358 | 0.1550 | 0.0097 | 0.0002 | ok |

迁移解释：

1. Split drift 主要是 gap 风格漂移，不是 target timing 漂移。robustness winner 的 gap/open-return 更强，train 更弱。
2. Regime drift 主要是 risk_on 的 drawdown / shakeout 风格更重。risk_on 不是简单的“涨得快”，而是“在更深 pre-target shakeout 后仍能成为 winner”。
3. Validation 的多项读数显示更浅 drawdown，但 validation 样本只有 234，不能单独冻结阈值。

## 10. Hard-failure conditioning

### 10.1 Profiling scope

| slice | winner_n | touch failure lower n | touch rate | close drawdown proxy n | close drawdown proxy rate |
|---|---:|---:|---:|---:|---:|
| all | 3075 | 1105 | 0.3593 | 1978 | 0.6433 |
| train | 1080 | 405 | 0.3750 | 718 | 0.6648 |
| validation | 234 | 66 | 0.2821 | 128 | 0.5470 |
| robustness | 1761 | 634 | 0.3600 | 1132 | 0.6428 |
| risk_on | 1268 | 599 | 0.4724 | 928 | 0.7319 |
| risk_off | 1393 | 360 | 0.2584 | 801 | 0.5750 |
| transition | 414 | 146 | 0.3527 | 249 | 0.6014 |

### 10.2 Injury scope

| split | injury winner_n | touch failure lower n | touch rate | close drawdown proxy n | close drawdown proxy rate |
|---|---:|---:|---:|---:|---:|
| all | 1092 | 385 | 0.3526 | 693 | 0.6346 |
| train | 399 | 147 | 0.3684 | 256 | 0.6416 |
| validation | 75 | 23 | 0.3067 | 38 | 0.5067 |
| robustness | 618 | 215 | 0.3479 | 399 | 0.6456 |

Insight：failure-like drawdown 在 winner population 内很常见，尤其 risk_on。由于上游 label 使用 `hard_failure_first_blocks_winner = true`，这些统计已经是在“先触发硬失败者被排除”之后的条件化读数；也就是说，真实 candidate population 中 shakeout path 的规模可能更大。本报告不能直接把这些 path 当 entry-time signal，但可以提示后续 10D 如果要修复 winner injury，不能只看“浅回撤、快速确认”的安全 winner。

## 11. Seed hypothesis readout

Seed flags 是 Appendix A 先验，只做 non-binding readout。

| seed flag | winner_n | seed_true_n | seed_true_rate |
|---|---:|---:|---:|
| seed_gap_or_event_driven_flag | 3075 | 1646 | 0.5353 |
| seed_shakeout_reversal_flag | 3075 | 927 | 0.3015 |
| seed_late_bloomer_flag | 3075 | 849 | 0.2761 |
| seed_early_momentum_flag | 3075 | 368 | 0.1197 |
| seed_volatile_chop_flag | 3075 | 338 | 0.1099 |

### 11.1 Seed overlap

| seed_flag_overlap_n | winner_n | overlap_count | overlap_rate |
|---:|---:|---:|---:|
| 0 | 3075 | 618 | 0.2010 |
| 1 | 3075 | 1291 | 0.4198 |
| 2 | 3075 | 734 | 0.2387 |
| 3 | 3075 | 359 | 0.1167 |
| 4 | 3075 | 73 | 0.0237 |
| 5 | 3075 | 0 | 0.0000 |

Insight：seed flags 不是互斥 taxonomy。约 37.92% winner 同时命中两个或更多 seed；另有 20.10% 一个 seed 都不命中。因此后续不能直接把这五个 seed 当成 frozen archetype 类别。需要先决定是做 multi-label taxonomy、priority assignment，还是重新聚类。

### 11.2 Seed by regime

| regime | gap/event | shakeout | late bloomer | early momentum | volatile chop |
|---|---:|---:|---:|---:|---:|
| risk_on | 0.5410 | 0.4093 | 0.3352 | 0.0946 | 0.1719 |
| risk_off | 0.5255 | 0.2089 | 0.2383 | 0.1400 | 0.0581 |
| transition | 0.5507 | 0.2826 | 0.2222 | 0.1280 | 0.0942 |

Regime insight：gap/event 在三个 regime 中都高，是广义 winner path 的主形态；真正有 regime 区分度的是 shakeout 和 volatile chop。risk_on 的 shakeout rate=40.93%，接近 risk_off 的两倍；risk_on volatile chop=17.19%，也显著高于 risk_off 的 5.81%。

## 12. 10C rejected injury concentration

PIT-filtered injury_scope 有 1092 个 winner，其中 10C full/keep_9000 rejected winners 为 105 个，整体 rejected rate 为 9.62%。

### 12.1 Rejected winner count by split × regime

| split | risk_on | risk_off | transition | total |
|---|---:|---:|---:|---:|
| train | 6 | 5 | 2 | 13 |
| validation | 7 | 7 | 4 | 18 |
| robustness | 55 | 18 | 1 | 74 |

10C injury 主要集中在 robustness，且 robustness risk_on 最多。validation 虽然 rejected rate 看起来偏高，但 total rejected 只有 18，必须低 power 处理。

### 12.2 Seed buckets

| seed bucket | bucket winner_n | injured_n | injury_rate | share_of_injury | share_of_winner | lift |
|---|---:|---:|---:|---:|---:|---:|
| seed_shakeout_reversal_flag | 327 | 58 | 0.1774 | 0.5524 | 0.2995 | 0.2529 |
| seed_volatile_chop_flag | 122 | 32 | 0.2623 | 0.3048 | 0.1117 | 0.1930 |
| seed_gap_or_event_driven_flag | 585 | 76 | 0.1299 | 0.7238 | 0.5357 | 0.1881 |
| seed_late_bloomer_flag | 299 | 20 | 0.0669 | 0.1905 | 0.2738 | -0.0833 |
| seed_early_momentum_flag | 134 | 4 | 0.0299 | 0.0381 | 0.1227 | -0.0846 |

Interpretation：10C 的 winner injury 不是均匀分布的。它更容易伤到经历较大回撤、波动震荡、或 gap/event-driven 的 winner；对 late bloomer 和 early momentum 的伤害反而低配。后续如果做 10D repair，应优先问“如何保留 risk_on shakeout / volatile winners”，而不是泛化地放松所有 rejected candidates。

### 12.3 Metric bins with highest lift

| metric bin | bucket | bucket winner_n | injured_n | injury_rate | lift | power |
|---|---|---:|---:|---:|---:|---|
| max_drawdown_to_target | [-0.3,-0.2) | 263 | 48 | 0.1825 | 0.2163 | ok |
| max_gap_open_return_to_target | [0.04,0.08) | 482 | 65 | 0.1349 | 0.1777 | ok |
| deepest_pre_target_ret_low | [-0.2,-0.12) | 153 | 25 | 0.1634 | 0.0980 | ok |
| day_to_target | [0,20) | 126 | 22 | 0.1746 | 0.0941 | ok |
| limit_like_up_day_count_to_target | [1,2) | 283 | 37 | 0.1307 | 0.0932 | ok |

Metric-bin insight：highest-lift injury bucket 是 `max_drawdown_to_target` 在 -30% 到 -20% 之间，而不是最极端尾部。极端尾部也有高 injury_rate，但样本量低 power。更可操作的修复域可能是“中重度 drawdown + 仍能完成 winner”的中间区域。

## 13. E1 / bridge alignment

### 13.1 E1-missed alignment

| seed bucket | n11 bucket & E1 | Jaccard | phi | P(E1|bucket) | P(bucket|E1) |
|---|---:|---:|---:|---:|---:|
| seed_shakeout_reversal_flag | 184 | 0.2987 | 0.1709 | 0.5627 | 0.3890 |
| seed_gap_or_event_driven_flag | 233 | 0.2824 | -0.0756 | 0.3983 | 0.4926 |
| seed_late_bloomer_flag | 149 | 0.2392 | 0.0808 | 0.4983 | 0.3150 |
| seed_volatile_chop_flag | 70 | 0.1333 | 0.1006 | 0.5738 | 0.1480 |
| seed_early_momentum_flag | 43 | 0.0762 | -0.0847 | 0.3209 | 0.0909 |

E1 insight：shakeout 对 E1-missed 的解释质量最好，phi 也为正。gap/event 的 Jaccard 高是因为 bucket 大，但 phi 为负，说明它不是一个干净的 E1-missed discriminator。volatile chop 的 P(E1|bucket) 高达 57.38%，但覆盖只有 14.80%。

### 13.2 Bridge alignment

| seed bucket | n11 bucket & bridge | Jaccard | phi | P(bridge|bucket) | P(bucket|bridge) |
|---|---:|---:|---:|---:|---:|
| seed_gap_or_event_driven_flag | 447 | 0.4566 | -0.0154 | 0.7641 | 0.5315 |
| seed_late_bloomer_flag | 207 | 0.2219 | -0.1136 | 0.6923 | 0.2461 |
| seed_shakeout_reversal_flag | 205 | 0.2129 | -0.2226 | 0.6269 | 0.2438 |
| seed_early_momentum_flag | 124 | 0.1457 | 0.1380 | 0.9254 | 0.1474 |
| seed_volatile_chop_flag | 71 | 0.0796 | -0.1586 | 0.5820 | 0.0844 |

Bridge insight：gap/event-driven 覆盖 bridge_winner 的比例最高，P(bucket|bridge)=53.15%。early momentum 的 P(bridge|bucket)=92.54%，但 bucket 小，只覆盖 14.74% 的 bridge。bridge 对齐更像“确认后继续走强”的覆盖问题，而 E1-missed 更接近 shakeout / volatile 的保护问题。

Regime caveat：risk_off 与 transition 的 bridge alignment 中多个 seed 的 P(bridge|bucket)=1.0，说明这些 regime 的 injury_scope bridge target 几乎不具备分辨力；不要据此得出 seed 完美预测 bridge 的结论。

## 14. Correlation structure

| metric_x | metric_y | Spearman corr |
|---|---|---:|
| deepest_ret_low_20 | mae_20_recomputed | 0.9999 |
| deepest_pre_target_ret_low | mae_60_recomputed | 0.9605 |
| mae_60_recomputed | mae_120_recomputed | 0.9471 |
| deepest_pre_target_ret_low | deepest_ret_low_20 | 0.9384 |
| day_to_target | mfe_60_recomputed | -0.8417 |
| day_to_confirm | mfe_20_recomputed | -0.8157 |
| day_to_target | mfe_20_recomputed | -0.6246 |

Correlation insight：多个 drawdown / MAE metrics 高度冗余，后续冻结 archetype 时不应把 `deepest_ret_low_20`、`mae_20`、`deepest_pre_target_ret_low`、`mae_60` 全部当独立维度。timing 与 early MFE 强负相关，这是 winner 定义和 target timing 的自然结果。更有增量的信息维度可能是 gap/limit intensity、risk regime、以及 drawdown depth 的组合。

## 15. Path basis reconciliation

逐日 path 以 qfq daily bars 为权威。aggregate scalar 只在上游提供时做对账。本次 09A/10A 不提供 `mfe_20d / mfe_60d / mfe_120d / mae_*`，10C 只提供 `mfe_20d`。

| source | scalar | provided | comparable_n | abs_diff_mean | abs_diff_p95 | mismatch_tol | mismatch_n | mismatch_rate | status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 10C_scores | mfe_20d | true | 1092 | 0.0014 | 0.0097 | 0.0200 | 26 | 0.0238 | non_blocking_downstream_scalar_readout |
| 09A/10A/10C other scalars | mae_20/60/120, mfe_60/120 | false | 0 | NA | NA | 0.0200 | 0 | NA | not_provided_non_blocking |

Interpretation：10C `mfe_20d` 与 qfq recompute 基本一致，p95 差异低于 1 pct，超过 2 pct tolerance 的 26 行只作为 downstream scalar readout，不影响主 path。其它 scalar 未提供，符合“若上游提供则对账”的条件，不构成 blocking issue。

## 16. Findings and implications

### Finding 1: PIT universe 过滤改变了研究分母

原始 09A winner candidate 有 7187 个，但 PIT-filtered 后只有 3075 个。57.21% 的 raw winners 不进入主统计。这不是数据损失 bug，而是本需求的可执行 universe 约束。所有后续结论都只对 `pit_largecap_main_chinext` 内可执行 winner 有效。

### Finding 2: Regime fallback 是必须的分布修复

691 个 PIT winner 的 episode regime 缺失但 event regime 可用，占 22.47%。这些 fallback 几乎都属于 risk_on。如果不回填，risk_on winner 会被系统性低估，尤其 validation risk_on 会从 53 个变成 6 个。现在 residual missing 为 0，regime 分布可以正常解释。

### Finding 3: risk_on winner 更像“深回撤后兑现”，不是“无回撤快涨”

risk_on 的 target timing 更慢，pre-target drawdown 更深，hard-failure-like touch rate 更高。risk_on touch failure lower rate=47.24%，risk_off 只有 25.84%。这提示后续 winner-safe rejector 不能把 risk_on 深回撤简单判为坏样本。

### Finding 4: 10C injury 集中在可解释的 path 区域

10C rejected winners 超配于 shakeout reversal、volatile chop、gap/event-driven，以及 `max_drawdown_to_target` 在 -30% 到 -20% 的 bucket。这个结果支持后续 10D 从“保护中重度 drawdown 后仍成为 winner 的样本”入手，而不是无差别放宽 10C。

### Finding 5: seed flags 是诊断工具，不是 taxonomy

seed flags 大量重叠，且 20.10% winner 没有任何 seed。当前 seed 更适合描述机制候选，而不是作为互斥 archetype。若要冻结 archetype，应先做：

1. multi-label vs priority-label 的设计选择；
2. drawdown / gap / timing 三类维度的冗余压缩；
3. split × regime low-power cell 的稳定性审计；
4. 明确哪些变量在 t0 可见，哪些只能用于 post-hoc profiling。

### Finding 6: validation split 不能单独驱动阈值

validation 只有 234 个 winner，validation risk_on 只有 53 个，transition 只有 39 个。虽然 validation 有一些快 target、浅 drawdown 的读数，但 low-power cell 不应驱动阈值或 archetype freezing。

## 17. Recommended next steps

1. 10D 若要修复 winner injury，优先围绕 risk_on shakeout / volatile / medium-drawdown bucket 做保护性 readout，不要从全局阈值放松开始。
2. 如果要冻结 archetype v1，先做冗余压缩：drawdown family、timing family、gap/limit family 各选少数代表维度。
3. 对 transition 做 sub-regime taxonomy audit。当前 transition 是 residual bucket，不能直接解释为一个机制。
4. 保留 `path_regime_source` 审计字段。未来若 episode membership 覆盖改善，应比较 episode-source 与 event-fallback rows 的 path 分布，避免 fallback 引入来源偏差。
5. 任何 t0 rejector / entry logic 都不能直接使用本报告的 forward path metrics；这些 metrics 只能用于 label repair、post-hoc profiling 和后续可见特征设计。

## 18. 产物索引

| artifact | 内容 |
|---|---|
| `path_metric_distribution.csv` | 384 行 split/regime/reporting_view × metric 分布统计 |
| `path_metric_histogram.csv` | 核心 metrics 的 histogram bins |
| `path_style_migration_readout.csv` | split/regime pairwise KS、PSI、quantile delta |
| `hard_failure_conditioning_calibration.csv` | failure-like drawdown conditioning |
| `seed_hypothesis_readout.csv` | non-binding seed flag 分布 |
| `seed_flag_overlap_by_reporting_view.csv` | seed flag overlap 结构 |
| `injury_concentration_by_bucket.csv` | 10C rejected winner concentration |
| `bucket_e1_alignment_2x2.csv` | seed bucket 与 E1/bridge 的 2x2 对齐 |
| `pit_universe_scope_audit.csv` | PIT universe 过滤、regime source fallback、exclusion audit |
| `path_basis_reconciliation_audit.csv` | qfq recompute 与上游 aggregate scalar 对账 |
| `winner_path_metrics.parquet` | 行级 PIT-filtered winner path metrics，本报告所有统计的事实来源 |
