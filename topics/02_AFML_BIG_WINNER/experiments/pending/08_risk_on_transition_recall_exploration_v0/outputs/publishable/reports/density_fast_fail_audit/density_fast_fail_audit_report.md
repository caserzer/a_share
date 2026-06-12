# 10d 密度 / Fast-Fail 审计报告

最终决策：`density_fast_fail_audit_partial_source_complete`

本报告只回答一个问题：把 07 / 08 候选事件都放到同一个“可执行事件日 + 10 个交易日窗口”口径下看，哪些候选池是真的过密，哪些只是 episode-window 里看起来事件很多。结论是：E1 在 10d 口径下确实很稀疏；R 系列单个 family 并不拥挤，但 R1/R2/R6/R7/R8 合并后的 R-core union 出现严重的同票同窗口拥挤。T4/T7 selected union 不拥挤，但 fast-fail 明显偏高。

本次输入 gate 通过，`input_failures = 0`，共检查 26 个输入。event-level labels 和 episode capture 本地源存在；但 full event-to-episode replay membership 不存在，R-series compression arms 也没有可审计的 selected-event membership。因此 retention 只能报告 pre-replay capture，不输出 oracle non-fast-fail replay；R compression arms 只能作为 aggregate frontier 行，不能进入 event-level rolling 10d、gap、uniqueness、fast-fail 或 hard-gate 判断。

## 口径

本实验冻结三个不同的密度概念，不能混用：

| 概念 | 本报告用途 | 是否可作为 hard gate |
| --- | --- | --- |
| full-denominator density | 全样本 instrument-year 事件密度，用于跨 scope 粗粒度比较 | 否，只能辅助解释 |
| rolling 10d executable density | 同 instrument / 同 candidate scope，在 `[event_window_anchor_pos, event_window_anchor_pos + 10]` 内的事件拥挤度 | 可以触发 diagnostic alert，但本实验不做直接入场决策 |
| episode-window density | 冻结 winner episode 内的事件数，用于解释 recall overlap | 否，episode window 不是 t0 可见信息 |

`event_window_anchor_pos` 是本报告的核心时间锚点：可执行事件用 next-open `trade_open_pos`；不可执行事件保留在审计分母中，但用 `event_t0_pos` fallback，并标记为 non-executable audit row。rolling duplicate 使用 ex-self 计数，不把 anchor event 自己当作重复。

## 一页结论

1. `07_E1_only` 在 10d 口径下非常稀疏：6820 个事件，rolling 10d duplicate rate 只有 0.19%，同票相邻事件间隔中位数 104 个交易日，10d uniqueness p10 = 1.00。E1 的问题不是过密，而是覆盖不足。
2. `07_full_union` 比 E1 明显更密：15161 个事件，rolling 10d duplicate rate 29.60%，相邻间隔中位数 15 天，10d uniqueness p10 = 0.727。07 全量 union 已经出现可执行时间拥挤。
3. `08_selected_T4_T7_union` 不是过密问题：2063 个事件，rolling 10d duplicate rate 3.73%，相邻间隔中位数 167 天，10d uniqueness p10 = 1.00。它的问题是 fast-fail 偏高：10d fast-fail 35.19%，20d false-repair 39.07%。
4. R 系列的关键不是单 family 过密，而是 cross-family union 过密。R1/R2/R6/R7/R8 单独看 rolling 10d duplicate rate 均为 0.00%，但 `08_R_core_event_regime_gated` 合并后达到 57.83%，相邻间隔中位数 7 天，10d uniqueness p10 = 0.364，low-uniqueness share = 36.55%。
5. R-family 的 pre-replay episode capture 很强，但不能直接证明可交易。R6 all-split any recall 88.25%、bridge recall 38.99%；R1 any recall 85.28%、bridge recall 33.84%。这些是候选生成价值，不是入场支持，因为 post-replay filter 需要 event-to-episode membership。
6. R compression arms 里有低密度候选，例如 `consensus_family_count__min3` 只有 3094 个事件、density 是 E1 的 0.45 倍、p95 = 2。但这些 arms 当前都是 aggregate-only，没有 selected-event membership，不能作为下一步硬 gate 的直接输入。

## 核心 Scope 数据

| scope | events | density / inst-year | p95 | roll10 dup | roll20 dup | gap median | uniq p10 | fast-fail 10d | false-repair 20d | alert |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 07_E1_only | 6820 | 1.883 | 4.70 | 0.19% | 1.95% | 104 | 1.000 | 14.52% | 20.62% | no alert |
| 07_E1_plus_E3 | 10257 | 2.832 | 7.20 | 0.63% | 34.37% | 52 | 1.000 | 15.67% | 22.26% | no alert |
| 07_full_union | 15161 | 4.185 | 10.85 | 29.60% | 55.66% | 15 | 0.727 | 16.33% | 23.13% | diagnostic |
| 08_selected_T4_T7_union | 2063 | 0.570 | 1.53 | 3.73% | 4.46% | 167 | 1.000 | 35.19% | 39.07% | no alert |
| 08_T4_gated | 1463 | 0.404 | 0.87 | 0.00% | 0.55% | 240 | 1.000 | 32.85% | 38.07% | no alert |
| 08_T7_gated | 629 | 0.174 | 0.42 | 0.00% | 0.00% | 211.5 | 1.000 | 40.58% | 42.13% | no alert |
| 08_R_core_event_regime_gated | 47914 | 13.227 | 38.12 | 57.83% | 71.14% | 7 | 0.364 | 24.20% | 31.11% | diagnostic |
| 08_R1_event_regime_gated | 14363 | 3.965 | 10.87 | 0.00% | 12.67% | 47 | 1.000 | 26.61% | 33.49% | no alert |
| 08_R2_event_regime_gated | 9537 | 2.633 | 7.00 | 0.00% | 2.45% | 77 | 1.000 | 23.75% | 29.16% | no alert |
| 08_R6_event_regime_gated | 16204 | 4.473 | 12.23 | 0.00% | 5.99% | 44 | 1.000 | 23.19% | 30.30% | no alert |
| 08_R7_event_regime_gated | 9786 | 2.702 | 7.00 | 0.00% | 0.35% | 70 | 1.000 | 23.30% | 29.62% | no alert |
| 08_R8_event_regime_gated | 12896 | 3.560 | 9.88 | 0.00% | 20.94% | 43 | 1.000 | 26.33% | 33.70% | no alert |

这张表给出最重要的结构性洞察：R-core union 的拥挤不是来自某一个 family 自己重复触发，而是来自不同 R family 在同一只票、相近 execution anchor 上同时触发。也就是说，下一步压缩不应该只做 family 内阈值，而应该做 cross-family de-overlap、instrument-day top-k、cooldown 或 ranker。

## Adjacent Gap 与 Uniqueness

| scope | gap sample | gap p10 | gap median | gap p90 | gap < 10d | concurrency mean | concurrency p95 | uniqueness mean | uniqueness p10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 07_E1_only | 5755 | 38 | 104 | 213.6 | 0.17% | 1.002 | 1.0 | 0.999 | 1.000 |
| 07_full_union | 14069 | 5 | 15 | 141 | 30.11% | 1.298 | 2.0 | 0.869 | 0.727 |
| 08_selected_T4_T7_union | 1141 | 27 | 167 | 696 | 6.66% | 1.037 | 1.0 | 0.975 | 1.000 |
| 08_R_core_event_regime_gated | 46483 | 1 | 7 | 60 | 57.64% | 1.872 | 4.0 | 0.615 | 0.364 |
| 08_R1_event_regime_gated | 12957 | 20 | 47 | 161 | 0.00% | 1.000 | 1.0 | 1.000 | 1.000 |
| 08_R2_event_regime_gated | 8269 | 23 | 77 | 214.2 | 0.00% | 1.000 | 1.0 | 1.000 | 1.000 |
| 08_R6_event_regime_gated | 14820 | 21 | 44 | 134 | 0.00% | 1.000 | 1.0 | 1.000 | 1.000 |
| 08_R7_event_regime_gated | 8579 | 33 | 70 | 196 | 0.00% | 1.000 | 1.0 | 1.000 | 1.000 |
| 08_R8_event_regime_gated | 11512 | 20 | 43 | 187 | 0.00% | 1.000 | 1.0 | 1.000 | 1.000 |

R-core 的 gap p10 = 1、gap median = 7、concurrency p95 = 4，说明在拥挤区域内，同一只票常常会在 10d 里收到多条 R family 信号。这会放大训练样本相关性，也会让后续 ranker 很容易学到重复事件，而不是新信息。

## Fast-Fail 分层

| scope | split / regime | events | fast-fail 10d | false-repair 20d | incomplete 10d |
| --- | --- | ---: | ---: | ---: | ---: |
| 07_E1_only | all / all | 6820 | 14.52% | 20.62% | 8 |
| 07_E1_only | all / risk_on | 2963 | 13.66% | 20.82% | 6 |
| 07_E1_only | all / transition | 1970 | 14.11% | 19.64% | 0 |
| 07_E1_only | validation / risk_on | 414 | 13.04% | 20.29% | 0 |
| 07_full_union | all / all | 15161 | 16.33% | 23.13% | 11 |
| 07_full_union | all / risk_on | 6928 | 17.03% | 25.22% | 9 |
| 08_selected_T4_T7_union | all / all | 2063 | 35.19% | 39.07% | 14 |
| 08_selected_T4_T7_union | all / risk_on | 1596 | 37.85% | 41.85% | 11 |
| 08_selected_T4_T7_union | train / risk_on | 899 | 40.31% | 44.49% | 6 |
| 08_selected_T4_T7_union | validation / risk_on | 94 | 25.53% | 36.17% | 0 |
| 08_R_core_event_regime_gated | all / all | 47914 | 24.20% | 31.11% | 65 |
| 08_R_core_event_regime_gated | all / risk_on | 30790 | 26.52% | 33.70% | 53 |
| 08_R_core_event_regime_gated | all / transition | 17124 | 20.03% | 26.45% | 12 |
| 08_R_core_event_regime_gated | train / risk_on | 16603 | 29.80% | 38.26% | 32 |
| 08_R_core_event_regime_gated | validation / risk_on | 4457 | 19.53% | 29.19% | 2 |

T4/T7 的密度很低，但 failure 率明显高于 E1 和 R-core。它不应该被当作“低密度就安全”的候选；如果进入 Experiment C，更像是需要 positive ranker / rejector 精修的高噪声低频信号。R-core 的 fast-fail 不如 T4/T7 极端，但因为样本密度大、10d 重叠高，实际训练风险更偏向样本相关性和重复信号。

## Pre-Replay Retention

本节只报告 `pre_replay_capture_only`。它来自已有 episode capture，不代表 10d fast-fail 过滤后的 retention；post-replay 字段保持空值是正确状态。

| scope | target episodes | pre any recall | pre bridge recall | E1-missed capture retention | status |
| --- | ---: | ---: | ---: | ---: | --- |
| 07_E1_only | 2493 | 71.12% | 32.56% | 0.00% | pre_replay_capture_only |
| 07_full_union | 2493 | 72.04% | 34.75% | 3.19% | pre_replay_capture_only |
| 08_selected_T4_T7_union | 2493 | 17.61% | 5.09% | 13.61% | pre_replay_capture_only |
| 08_T4_gated | 2493 | 12.03% | 3.61% | 10.56% | pre_replay_capture_only |
| 08_T7_gated | 2493 | 6.34% | 1.60% | 3.19% | pre_replay_capture_only |
| 08_R1_event_regime_gated | 2493 | 85.28% | 33.84% | 78.47% | pre_replay_capture_only |
| 08_R2_event_regime_gated | 2493 | 76.25% | 27.13% | 65.28% | pre_replay_capture_only |
| 08_R6_event_regime_gated | 2493 | 88.25% | 38.99% | 78.61% | pre_replay_capture_only |
| 08_R7_event_regime_gated | 2493 | 78.86% | 33.29% | 70.14% | pre_replay_capture_only |
| 08_R8_event_regime_gated | 2493 | 74.85% | 28.04% | 71.11% | pre_replay_capture_only |

`07_E1_plus_E3` 与 `08_R_core_event_regime_gated` 当前没有对应 capture scope，标记为 `scope_capture_not_available`。这不影响 10d density / fast-fail audit，但阻断了这两个 scope 的 pre-replay episode recall 表达。

risk_on 分层里，R-family 的 pre-replay capture 更能说明为什么 R 系列值得继续研究：

| scope | split | risk_on episodes | pre any recall | pre bridge recall | E1-missed retention |
| --- | --- | ---: | ---: | ---: | ---: |
| 07_E1_only | train | 225 | 63.11% | 28.89% | 0.00% |
| 07_E1_only | robustness | 181 | 49.17% | 34.81% | 0.00% |
| 08_selected_T4_T7_union | train | 225 | 21.78% | 6.22% | 18.07% |
| 08_R1_event_regime_gated | train | 225 | 96.00% | 42.86% | 92.77% |
| 08_R2_event_regime_gated | train | 225 | 87.11% | 33.33% | 89.16% |
| 08_R6_event_regime_gated | train | 225 | 96.44% | 43.30% | 93.98% |
| 08_R7_event_regime_gated | train | 225 | 89.33% | 35.56% | 79.52% |
| 08_R8_event_regime_gated | train | 225 | 88.00% | 35.11% | 89.16% |

解读：R families 的 episode capture 很强，特别是 R1/R6；但它们进入 executable 10d 口径后会在 R-core union 层面高度重叠。因此 B/C 的问题不是“有没有 recall”，而是“如何在保留 recall 的同时避免同票 10d 多次重复入场”。

## R-Series Compression Arms

所有 R compression arms 当前都是 `aggregate_frontier_only_no_event_membership`。下表只用于方向判断，不允许作为 event-level hard gate。

| compression arm | events | density / inst-year | p95 | density vs E1 |
| --- | ---: | ---: | ---: | ---: |
| consensus_family_count__min3 | 3094 | 0.854 | 2 | 0.45x |
| market_day_top_percentile__top5pct | 8734 | 2.411 | 5 | 1.28x |
| single_family_best_variant__R2_near_high_volume_expansion | 9537 | 2.633 | 4 | 1.40x |
| single_family_best_variant__R7_cross_sectional_momentum_rank_jump | 9786 | 2.702 | 4 | 1.43x |
| market_day_top_percentile__top10pct | 10846 | 2.994 | 6 | 1.59x |
| family_score_quantile_cut__q0975 | 10992 | 3.034 | 5 | 1.61x |
| consensus_family_count__min2 | 11007 | 3.039 | 5 | 1.61x |
| family_score_quantile_cut__q095 | 11773 | 3.250 | 5 | 1.73x |
| family_score_quantile_cut__q09 | 13634 | 3.764 | 6 | 2.00x |
| cooldown_after_selected_event__40d | 13954 | 3.852 | 5 | 2.05x |
| raw_r_series_variant_pool | 61960 | 17.105 | 24 | 9.09x |
| event_regime_gated_only | 47929 | 13.231 | 20 | 7.03x |
| overlap_deconcentration | 47929 | 13.231 | 20 | 7.03x |

`consensus_family_count__min3` 是最有趣的方向：它比 E1 更低密度，同时理论上要求多 family 共振；但在没有 event membership 的情况下，它只是 aggregate hypothesis。若要进入 Experiment C，第一步必须重建 selected-event membership，并验证 canonical_event_count 与 frontier 表一致。

## Gate 与可重构性

| 项目 | 结果 |
| --- | --- |
| input gate | pass |
| 可重构 event membership scope | 12 |
| aggregate-only R compression arms | 24 |
| diagnostic alert scope | `07_full_union`, `08_R_core_event_regime_gated` |
| hard gate blocked | no |
| event-level labels | available |
| episode capture | available |
| R compression membership | not reconstructable in this run |

本实验没有返回 direct-entry support decision。`diagnostic_alert` 说明需要压缩或去重，不等价于策略不可用；`hard_gate_not_failed_by_audit` 也不等价于可直接交易。

## Findings And Insight

**Finding 1：E1 在 10d 口径下是稀疏基准，不是过密问题。**
E1 的 rolling 10d duplicate rate 只有 0.19%，相邻 gap median 104 天，uniqueness p10 = 1.00。这个结果支持“E1 太稀疏，不能单独解决 recall”的判断，但不支持“E1 需要密度压缩”。E1 更适合作为低拥挤 baseline。

**Finding 2：07 full union 的拥挤已经可见，但还不是 R-core 级别。**
07 full union 的 rolling 10d duplicate rate 29.60%，gap median 15 天，说明简单扩展 E1+其他 07 channel 会显著增加样本重叠。它比 E1 recall 更广，但会带来更高事件相关性。

**Finding 3：T4/T7 的主要问题是质量，不是密度。**
T4/T7 selected union 的 density 只有 E1 的 0.30x，rolling 10d duplicate rate 3.73%，但 fast-fail 10d 达到 35.19%。这类信号如果继续使用，优先方向不是 cooldown，而是质量过滤、regime gating 或 positive ranker。

**Finding 4：R-core 的核心问题是 cross-family collision。**
单个 R family 的 rolling 10d duplicate rate 都是 0.00%，但合并后 R-core 达到 57.83%。这说明 family 内事件已经稀疏化，真正的拥挤来自不同机制对同一只票在同一 10d 窗口内重复确认。B/C 应该把 instrument-window de-overlap 放在 family 选择之后，而不是只调单 family 阈值。

**Finding 5：R family 有很强 episode capture，但必须先变成可执行的稀疏事件。**
R1/R6 在 risk_on train 上 pre any recall 分别为 96.00% / 96.44%，pre bridge recall 分别为 42.86% / 43.30%。这说明 R 系列有增量候选价值；但 R-core union 的 10d uniqueness p10 只有 0.364，会污染后续 ranker 的样本独立性。

**Finding 6：compression arms 的方向有价值，但证据层级仍是 aggregate。**
`consensus_family_count__min3`、`market_day_top_percentile__top5pct`、`family_score_quantile_cut__q0975` 等 arm 看起来能降低密度；但没有 selected-event membership，就不能计算真实 rolling 10d、gap、uniqueness 和 fast-fail。下一步如果使用这些 arm，必须先补 event membership artifact。

## 对 Experiments B / C 的建议

1. Experiment B 的 regime-family matrix 不应把 R-core union 作为单一可交易候选；它应把 R1/R2/R6/R7/R8 分开评估，并报告 family 间同票 10d collision。
2. Experiment C 的 positive ranker 应把 `event_window_anchor_pos` 作为排序后的去重基准：同 instrument 10d 内只保留最高分事件，或至少输出 top-k / cooldown sensitivity。
3. T4/T7 若进入 C，应作为低密度但高 fast-fail 的质量过滤对象，而不是 recall 扩展主力。
4. R compression arm 若要进入 C，优先重建 `consensus_family_count__min3`、`market_day_top_percentile__top5pct`、`family_score_quantile_cut__q0975` 的 selected-event membership，因为它们的 aggregate density 明显低于 raw R pool。
5. downstream 不应使用 episode-window density 或 fast-fail oracle label 作为 t0 entry feature。`failure_10_label` / `false_repair_10d` 只能用于 audit、rejector target 或 post-hoc readout。

## Source Pointers

本报告基于以下当前产物：

- `candidate_10d_density_summary.csv`
- `candidate_10d_fast_fail_readout.csv`
- `candidate_adjacent_event_gap_diagnostic.csv`
- `candidate_10d_uniqueness_diagnostic.csv`
- `candidate_10d_retention_by_split_regime.csv`
- `candidate_density_caliber_crosswalk.csv`
- `candidate_scope_reconstructability_audit.csv`
- `density_fast_fail_audit_manifest.json`
