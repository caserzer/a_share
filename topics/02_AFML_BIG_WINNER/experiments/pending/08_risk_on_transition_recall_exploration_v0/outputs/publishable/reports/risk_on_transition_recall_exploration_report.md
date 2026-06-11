# Risk-on / Transition Recall 修复探索 V0

## 结论

本轮 08 实验的最终决策是：

`risk_on_transition_recall_exploration_density_blocked`

这不是因为没有增量召回。相反，新候选族在 `risk_on` / `transition` missed episode 上确实找到了补充信号；但推荐 union 未通过 graduation gate：

1. `density_gate` 未通过：selected union 的绝对密度很低，但 T4 单一 family 占 selected union 事件密度的 `70.9%`，超过 `35%` family share gate。
2. `bridge_gate` 未通过：selected union 的 bridge-positive recall 显著低于 E1-only baseline，最差 split/regime 差值为 `-27.6 pct`。

因此，08 的有效结论应是：

- T4 / T7 可以作为 09 meta-label 或 rejector 的候选特征来源继续保留。
- 当前 selected union 不能作为下一阶段的推荐事件入口。
- all-new candidate union 证明“可找回大量 missed episodes”，但密度过高，只能作为候选池或研究线索，不能直接继承为事件 union。

## 运行概览

| item | value |
| --- | ---: |
| final decision | `risk_on_transition_recall_exploration_density_blocked` |
| target episodes | 2,493 |
| 06 evaluated instrument-days | 912,851 |
| candidate event instances | 238,679 |
| candidate canonical events | 90,576 |
| selected canonical events | 2,063 |
| E1-only canonical events | 6,820 |
| selected / E1 canonical count ratio | 0.3025x |
| selected density full denominator | 0.5695 events / instrument-year |
| selected density p95 nonzero instrument-year | 2.0 |
| selected next-open executable rate | 99.5% |
| selected 120d label completeness | 99.5% |
| validation risk_on denominator | 22 |

Selected variants:

| variant | family status | mechanism |
| --- | --- | --- |
| `T4_entropy_compression_then_directional_expansion__event_regime_gated` | runnable_existing_data | compression break |
| `T7_board_relative_strength_break__event_regime_gated` | fallback_variant | board/style relative strength |

## Baseline 与问题定位

08 没有从 07 full union 继续扩张，而是从 07 canonical / instance artifacts 重放 E1-only baseline，并把新的 risk-on / transition family 作为独立候选生成，最后再 link 回 06 冻结 denominator。

E1-only baseline 重算与 07 report 对齐：

| metric | recomputed | reported reference | difference | status |
| --- | ---: | ---: | ---: | --- |
| canonical events | 6,820 | 6,820 | 0 | match |
| before-first-50 any recall | 71.12% | 71.10% | +0.02 pct | rounding |
| before-first-50 bridge recall | 32.56% | 32.60% | -0.04 pct | rounding |

E1-only 的核心短板集中在 `risk_on` / `transition`：

| split | regime | E1 captured | denominator | E1 recall |
| --- | --- | ---: | ---: | ---: |
| train | risk_on | 142 | 225 | 63.1% |
| train | transition | 189 | 304 | 62.2% |
| validation | risk_on | 9 | 22 | 40.9% |
| validation | transition | 57 | 81 | 70.4% |
| robustness | risk_on | 89 | 181 | 49.2% |
| robustness | transition | 40 | 100 | 40.0% |

`validation risk_on` 只有 22 个 denominator episode，报告中只作为 sample-small diagnostic，不作为单独 hard gate。

## Family Capability

08 共声明 16 个 family：

| status | count |
| --- | ---: |
| runnable_existing_data | 9 |
| family_data_blocked | 3 |
| fallback_variant | 2 |
| diagnostic_only | 2 |

完整执行状态：

| family | status | fallback_of | executed | selected_variant | event_count |
| --- | --- | --- | ---: | --- | ---: |
| R1 relative strength breakout | runnable_existing_data |  | true |  | 31,385 |
| R2 near high volume expansion | runnable_existing_data |  | true |  | 20,279 |
| R3 VCP breakout | runnable_existing_data |  | true |  | 16,276 |
| R4 industry breadth expansion | family_data_blocked |  | false |  | 0 |
| R5 growth/small style confirmation | diagnostic_only |  | true |  | 4,087 |
| R6 market breadth thrust | runnable_existing_data |  | true |  | 35,958 |
| R7 cross-sectional momentum rank jump | runnable_existing_data |  | true |  | 21,773 |
| R8 persistent distance above EMA | runnable_existing_data |  | true |  | 26,777 |
| T1 stock-vs-industry CUSUM break | family_data_blocked |  | false |  | 0 |
| T2 industry-vs-market CUSUM break | family_data_blocked |  | false |  | 0 |
| T3 style rotation break | diagnostic_only |  | true |  | 1,259 |
| T4 entropy compression directional expansion | runnable_existing_data |  | true | event_regime_gated | 3,121 |
| T5 volume regime shift | runnable_existing_data |  | true |  | 27,500 |
| T6 stock-vs-market CUSUM break | fallback_variant | T1 | true |  | 24,311 |
| T7 board relative strength break | fallback_variant | T2 | true | event_regime_gated | 1,259 |
| T8 volatility contraction break | runnable_existing_data |  | true |  | 24,694 |

输入契约结论：

| feature domain | PIT available | coverage | policy |
| --- | ---: | ---: | --- |
| industry | false | 0.0% | R4 / T1 / T2 blocked |
| style_proxy_board | true | 100.0% | board/style family 只作为 diagnostic 或 fallback |
| market_breadth | true | 100.0% | R6 是 market-breadth substitute，不冒充 industry |

## Candidate Frontier

selected union 使用 train-only selection，最终保留 T4 gated 与 T7 gated。高 recall 的 dense families 没有进入 selected union。

| candidate | selected | train risk_on inc | train transition inc | robustness risk_on inc | robustness transition inc | density vs E1 | events | 120d big-winner rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T4 gated | true | 4.9 pct | 6.9 pct | 4.4 pct | 0.0 pct | 0.2145x | 1,463 | 22.2% |
| T7 gated | true | 1.8 pct | 1.3 pct | 0.6 pct | 2.0 pct | 0.0922x | 629 | 19.3% |
| all-new candidate union | false | 36.4 pct | 37.2 pct | 49.2 pct | 16.0 pct | 13.2809x | 90,576 | 19.1% |
| T6 all variants | false | 35.6 pct | 35.9 pct | 37.0 pct | 7.0 pct | 2.1567x | 14,709 | 19.1% |
| R1 all variants | false | 34.7 pct | 36.5 pct | 40.9 pct | 9.0 pct | 2.7182x | 18,538 | 18.9% |
| R6 all variants | false | 34.7 pct | 35.9 pct | 42.5 pct | 7.0 pct | 3.2219x | 21,973 | 19.5% |
| R2 all variants | false | 33.3 pct | 31.9 pct | 29.3 pct | 10.0 pct | 1.6305x | 11,120 | 18.3% |
| R8 all variants | false | 32.9 pct | 34.9 pct | 35.4 pct | 8.0 pct | 2.2054x | 15,041 | 19.1% |

关键洞察：

- all-new union 的 recall 很强，但密度是 E1 的 `13.28x`，事件数 90,576，不能作为可执行候选 union。
- R1/R6/T6/T5/R8 等大族贡献很高，但都太密；这些更像“宽候选池”而不是 low-density entry signal。
- T4 是当前低密度组合的主要贡献者；T7 的边际贡献较小，且与 board/style diagnostic 高度重合。

## Selected Union Recall

selected union 在 before-first-50pct window 下的增量召回如下：

| split | regime | denominator | E1 captured | candidate captured | E1 + candidate captured | incremental captures | incremental recall | unique not in E1/E2/E3/E6 | earlier vs E1 | better basis vs E1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | risk_on | 428 | 240 | 88 | 266 | 26 | 6.1 pct | 24 | 5 | 9 |
| all | transition | 485 | 286 | 89 | 313 | 27 | 5.6 pct | 27 | 4 | 6 |
| train | risk_on | 225 | 142 | 49 | 157 | 15 | 6.7 pct | 13 | 3 | 3 |
| train | transition | 304 | 189 | 70 | 214 | 25 | 8.2 pct | 25 | 2 | 4 |
| validation | risk_on | 22 | 9 | 3 | 11 | 2 | 9.1 pct | 2 | 0 | 1 |
| validation | transition | 81 | 57 | 7 | 57 | 0 | 0.0 pct | 0 | 2 | 2 |
| robustness | risk_on | 181 | 89 | 36 | 98 | 9 | 5.0 pct | 9 | 2 | 5 |
| robustness | transition | 100 | 40 | 12 | 42 | 2 | 2.0 pct | 2 | 0 | 0 |

按 family 拆开看：

| variant | split | regime | denominator | incremental captures | incremental recall | unique not in E1/E2/E3/E6 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| T4 gated | train | risk_on | 225 | 11 | 4.9 pct | 10 |
| T4 gated | train | transition | 304 | 21 | 6.9 pct | 21 |
| T4 gated | validation | risk_on | 22 | 2 | 9.1 pct | 2 |
| T4 gated | validation | transition | 81 | 0 | 0.0 pct | 0 |
| T4 gated | robustness | risk_on | 181 | 8 | 4.4 pct | 8 |
| T4 gated | robustness | transition | 100 | 0 | 0.0 pct | 0 |
| T7 gated | train | risk_on | 225 | 4 | 1.8 pct | 3 |
| T7 gated | train | transition | 304 | 4 | 1.3 pct | 4 |
| T7 gated | validation | risk_on | 22 | 0 | 0.0 pct | 0 |
| T7 gated | validation | transition | 81 | 0 | 0.0 pct | 0 |
| T7 gated | robustness | risk_on | 181 | 1 | 0.6 pct | 1 |
| T7 gated | robustness | transition | 100 | 2 | 2.0 pct | 2 |

解释：

- selected union 在 train + robustness 合计 missed capture count 为 51，满足 recall count 分支。
- robustness risk_on 最大增量为 5.0 pct，没有达到 8 pct hard recall threshold。
- transition 的 robustness 增量只有 2.0 pct，说明 selected union 对 transition 的 out-of-sample 支撑偏弱。

## Density Gate

headline density 使用 full evaluated denominator；event-regime-gated eligible denominator 只作为诊断。

| scope | events | full density | gated eligible density | density vs E1 full | density vs same gated | p95 events/IPY | share of selected union | share gate | density drag |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 07 E1-only | 6,820 | 1.8827 | 1.8827 | 1.0000x | 1.0000x | 3 |  | pass | false |
| 07 full union | 15,161 | 4.1853 | 4.1853 | 2.2230x | 2.2230x | 7 |  | pass | false |
| all-new candidate union | 90,576 | 25.0042 | 25.0042 | 13.2809x | 13.2809x | 33 |  | pass | false |
| T4 gated | 1,463 | 0.4039 | 0.5554 | 0.2145x | 0.2966x | 2 | 70.9% | fail | false |
| T7 gated | 629 | 0.1736 | 0.2388 | 0.0922x | 0.1275x | 2 | 30.5% | pass | false |
| selected union | 2,063 | 0.5695 | 0.5695 | 0.3025x | 0.3025x | 2 | 100.0% | pass | false |

密度结论要分两层看：

- selected union 的绝对密度并不高，只有 E1 的 `0.3025x`，p95 也只有 2。
- 但 family share gate 失败，因为 T4 占 selected union 事件密度的 `70.9%`，超过 `35%` 上限。

这说明当前 selected union 不是“多机制低密度组合”，而是一个 T4-dominated setup，再加少量 T7 board fallback。

## Bridge / Label Gate

bridge-positive recall 是 selected union 最大的硬伤。selected union 的 bridge recall 全部显著低于 E1-only，而 all-new union 反而很强。

| split | regime | selected bridge | E1 bridge | selected - E1 | all-new bridge |
| --- | --- | ---: | ---: | ---: | ---: |
| train | risk_on | 6.2% | 28.9% | -22.7 pct | 60.4% |
| train | transition | 8.6% | 32.0% | -23.5 pct | 64.8% |
| validation | risk_on | 0.0% | 18.2% | -18.2 pct | 50.0% |
| validation | transition | 3.7% | 30.9% | -27.2 pct | 64.2% |
| robustness | risk_on | 7.2% | 34.8% | -27.6 pct | 79.6% |
| robustness | transition | 2.0% | 24.0% | -22.0 pct | 42.4% |

bridge exclusion 本身没有恶化：selected union 的 bridge exclusion excess vs E1 为 `0.0 pct`。问题不是 denominator 被排除，而是 selected events 在 bridge-positive label 上没有承接 E1 的 forward quality。

Label / execution quality 通过硬阈值：

| scope | events | label completeness | executable rate | 120d big-winner rate | near-winner rate | confirm 20d | failure 10d | median MFE 120d | median MAE 120d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T4 gated | 1,463 | 99.5% | 99.5% | 22.2% | 17.2% | 30.9% | 32.1% | 22.5% | -22.8% |
| T7 gated | 629 | 99.7% | 99.7% | 19.3% | 27.7% | 54.1% | 32.3% | 24.4% | -29.2% |
| selected union | 2,063 | 99.5% | 99.5% | 20.7% | 17.1% | 33.9% | 31.1% | 21.4% | -24.2% |

False-repair diagnostic：

| scope | events | false repair 10d count | false repair 10d rate | false repair 20d count | false repair 20d rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| T4 gated | 1,463 | 353 | 20.6% | 557 | 33.5% |
| T7 gated | 629 | 174 | 23.5% | 265 | 41.6% |
| selected union | 2,063 | 520 | 20.9% | 806 | 34.1% |

洞察：

- selected union 的 next-open 与 label completeness 没问题。
- 但 false-repair 10d / 20d 不低，尤其 T7 的 20d false repair rate 为 41.6%。
- 这类信号更适合进入 meta-label / rejector 特征，而不是直接提升事件入口。

## Timing / Basis

在 E1 和 selected candidate 都捕捉到的 episode 中，selected candidate 通常不是更早信号。

| regime | both captured episodes | candidate earlier by >=10 sessions | better basis count | median candidate_minus_E1 lead sessions | p25 | p75 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| risk_off | 217 | 7 | 26 | -14.0 | -53.0 | -3.0 |
| risk_on | 62 | 5 | 9 | -13.5 | -37.0 | -2.3 |
| transition | 62 | 4 | 6 | -16.0 | -41.8 | -4.3 |

口径说明：`candidate_minus_E1 lead sessions = candidate lead_time_to_first_50pct - E1 lead_time_to_first_50pct`。正数代表 candidate 更早，负数代表 candidate 更晚。

selected union 在 focus regimes 的 gate summary：

| item | value |
| --- | ---: |
| earlier by >=10 sessions count | 9 |
| better basis count | 15 |

Lead-time distribution:

| split | regime | captured episodes | median event to first +50 sessions | median event from episode low sessions |
| --- | --- | ---: | ---: | ---: |
| train | risk_on | 49 | 14.0 | 42.0 |
| train | transition | 70 | 15.5 | 35.5 |
| validation | risk_on | 3 | 10.0 | 23.0 |
| validation | transition | 7 | 18.0 | 81.0 |
| robustness | risk_on | 36 | 12.5 | 71.0 |
| robustness | transition | 12 | 2.5 | 65.5 |

洞察：

- selected events 在距离 first +50% 的时间上并不差，通常仍在 +50% 触发前。
- 但与 E1 共同捕捉的 episode 上，它们中位数更晚，不能替代 E1 作为 earlier repair basis。
- 当前价值更接近“补充 E1 missed episode 的上下文特征”，而不是“更早的 first event anchor”。

## Feature / Tag Readout

selected variants 与 07 E2/E3/E6 的同日 tag 重叠很低：

| family | events | E2 same-day tag | E3 same-day tag | E6 same-day tag | close_to_ema60 coverage | VWAP coverage | amount ratio 20d median | stock vs market 20d median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T4 gated | 1,463 | 1.6% | 0.0% | 2.5% | 100.0% | 0.0% | 1.56 | 20.9% |
| T7 gated | 629 | 2.4% | 0.0% | 4.9% | 100.0% | 0.0% | 1.79 | 7.6% |

洞察：

- T4/T7 不是简单复刻 E2/E3/E6 的同日 tag。
- 但 VWAP coverage 为 0，说明这些信号不能依赖 VWAP quality 来过滤，需要用成交额、range、false-repair、forward label 等替代质量特征。
- T7 的 board relative CUSUM 中位数为 0.0695，符合 board-level fallback 语义，但它与 T3 style rotation 几乎完全重合，独立性不足。

## Overlap / Cluster

高风险 overlap 说明 selected families 不是完全独立机制：

| pair | selected-side overlap rate | other-side overlap rate | jaccard | same-day overlap | same-episode different-day |
| --- | ---: | ---: | ---: | ---: | ---: |
| T4 gated vs R3 all variants | 68.3% | 14.0% | 13.1% | 10 | 201 |
| T4 gated vs T8 all variants | 88.3% | 13.1% | 12.9% | 87 | 261 |
| T7 gated vs R5 all variants | 99.4% | 35.1% | 35.0% | 183 | 128 |
| T7 gated vs T3 event-regime gated | 100.0% | 100.0% | 100.0% | 629 | 0 |

Cluster summary:

| cluster | all risk_on inc | all transition inc | robustness risk_on inc | robustness transition inc |
| --- | ---: | ---: | ---: | ---: |
| relative_strength_cluster | 40.7 pct | 30.1 pct | 44.2 pct | 10.0 pct |
| breadth_cluster | 39.3 pct | 28.5 pct | 42.5 pct | 7.0 pct |
| volume_regime_cluster | 36.9 pct | 28.2 pct | 39.8 pct | 12.0 pct |
| compression_break_cluster | 35.3 pct | 28.5 pct | 37.0 pct | 14.0 pct |
| persistent_trend_cluster | 35.0 pct | 28.0 pct | 35.4 pct | 8.0 pct |
| volume_high_breakout_cluster | 32.7 pct | 25.8 pct | 29.3 pct | 10.0 pct |
| board_style_cluster | 4.0 pct | 4.3 pct | 2.2 pct | 2.0 pct |

Selected union cluster ablation:

| removed cluster | all risk_on inc after ablation | all transition inc after ablation | robustness risk_on inc after ablation | robustness transition inc after ablation |
| --- | ---: | ---: | ---: | ---: |
| board_style_cluster | 4.9 pct | 4.3 pct | 4.4 pct | 0.0 pct |
| compression_break_cluster | 1.2 pct | 1.2 pct | 0.6 pct | 2.0 pct |

解释：

- selected union 的主要增量来自 compression_break_cluster，也就是 T4。
- 去掉 T4 后，只剩 T7 的 board/style contribution，增量很小。
- 去掉 T7 后，T4 仍保留主要 risk_on contribution，但 transition robustness 归零。

## Ungated vs Event-Regime-Gated

event-regime gating 的价值主要是降低密度，而不是显著提升 precision。

| family | ungated density vs E1 | gated density vs E1 | selected |
| --- | ---: | ---: | ---: |
| T4 | 0.2726x | 0.2145x | gated |
| T7 | 0.1736x | 0.0922x | gated |
| T6 | 1.9848x | 1.5799x | no |
| R1 | 2.4959x | 2.1060x | no |
| R6 | 2.8965x | 2.3760x | no |

洞察：

- gating 把 T7 density 减半左右，因此 T7 gated 成为可讨论的低密度 fallback。
- T6/R1/R6 即使 gating 后仍然偏密，不能作为 selected union 入口。

## Artifact / Manifest Integrity

本次 report 对齐的是 full run artifact：

| artifact | row count |
| --- | ---: |
| `candidate_family_event_instances.csv` | 238,679 |
| `candidate_family_canonical_events.csv` | 90,576 |
| `candidate_family_incremental_recall_over_e1.csv` | 3,936 |
| `candidate_family_bridge_exclusion_audit.csv` | 4,128 |
| `candidate_family_density_summary.csv` | 43 |
| `candidate_family_lead_time_distribution.csv` | 3,014 |
| `candidate_family_feature_snapshot_summary.csv` | 26 |
| local candidate labels parquet | 331,318 |
| local candidate capture parquet | 857,592 |

`run_manifest.json` 已记录输出路径、hash、row count、column schema。报告更新后需同步 report hash，避免 manifest drift。

## Findings

1. **08 确认了 risk_on / transition missed episode 可以被非 E1 family 补充。**
   selected union 在 all risk_on / transition 分别增加 26 / 27 个 E1 missed captures；在 train risk_on / transition 分别增加 15 / 25 个；robustness risk_on / transition 分别增加 9 / 2 个。

2. **当前 selected union 不能进入 09 作为推荐事件入口。**
   它没有通过 density family-share gate 和 bridge gate。绝对密度低不是充分条件；T4 占比 70.9% 使 union 机制过于单一。

3. **bridge gate 是最关键的否决证据。**
   selected union 的 bridge recall 在所有 focus split/regime 上都低于 E1，robustness risk_on 差距达到 -27.6 pct。它捕捉到一些 missed episode，但这些 event 不够像“可桥接到大赢家路径”的正向 anchor。

4. **all-new union 说明信号空间存在，但必须被强约束压缩。**
   all-new union 在 robustness risk_on 增量达到 49.2 pct，bridge recall 达到 79.6%，但 density 是 E1 的 13.28x。这个结果适合指导 feature mining，不适合直接形成 union。

5. **T4 是本轮最有价值但仍需拆解的 family。**
   T4 gated 的 120d big-winner rate 为 22.2%，高于 selected union 平均 20.7%，且贡献了主要增量。但它和 R3/T8 episode-level overlap 较高，需要在下一阶段拆出“真正独立于 VCP/volatility contraction 的 entropy compression”。

6. **T7 目前更像 board/style duplicate，而不是独立 alpha。**
   T7 gated 与 T3 event-regime-gated overlap 为 100%，与 R5 all variants overlap 也很高。它可以作为 board-style context feature，但不能单独声称发现了独立 transition mechanism。

7. **timing/basis 不支持“更早替代 E1”。**
   在 E1 和 selected candidate 都捕捉的 risk_on / transition episode 上，candidate median lead 差值为 -13.5 / -16 sessions，说明 selected candidate 往往晚于 E1。

8. **label/execution 质量不是瓶颈。**
   selected union 的 next-open executable rate 与 label completeness 都是 99.5%，但 false repair 20d rate 为 34.1%，需要进入 rejector 设计。

## Insight

08 的核心洞察是：
**risk_on / transition 的 missed recall 问题不是“找不到事件”，而是“找到的事件太密、太同质、且低密度版本的 bridge quality 不够”。**

也就是说，下一阶段不应简单扩大 candidate union，而应把 08 的结果拆成两层：

1. **候选池层**：保留 all-new / high recall families 作为 feature mining universe，尤其是 T4、T6、R1、R6、T8 这些能大幅覆盖 missed episode 的机制。
2. **筛选层**：用 meta-label / rejector 严格压缩事件密度，并把 false repair、bridge-positive、board/style overlap、same-day duplicate、lead-time basis 作为核心特征。

如果 09 继续推进，建议不要把 selected union 当作 entry contract，而是把 T4 gated 和 T7 gated 标记为：

- `candidate_feature_supported`
- `event_union_not_supported`
- `needs_bridge_positive_ranker`
- `needs_density_share_deconcentration`

当前最可操作的研究方向：

1. 对 T4 做 de-overlap：拆分与 R3/T8 重合的 compression cases，找出真正独立的 entropy-compression transition。
2. 对 T7 降级为 board/style context tag：不要作为独立 event family 计数，避免和 T3/R5 重复。
3. 对高 recall 高密度族做二阶段筛选：先从 all-new union 中学习哪些事件具备 bridge-positive forward profile，再回压 density。
4. 把 false-repair 10d / 20d、MAE、amount expansion、range position、market regime、board concentration 纳入 rejector。

本实验不是交易信号、不是模型、不是回测；所有 event-anchored +50% / 120d forward label 只用于候选事件评估，不参与事件触发。
