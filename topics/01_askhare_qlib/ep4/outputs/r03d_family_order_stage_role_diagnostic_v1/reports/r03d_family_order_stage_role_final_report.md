# R03d Family 出现顺序与 Stage Role 诊断最终报告

## 1. 核心结论

- final_decision: `stage_role_only_no_order_increment`
- prefix_order_incremental: `insufficient_denominator`
- pair_order_incremental: `no_increment`
- last_added_family_incremental: `insufficient_denominator`
- validation status: `passed`, 40/40 checks passed

我的判断是：R03d 没有证实“family 出现顺序”本身能提供可复用的 entry / add edge；但它证实了 7 个 family 在 episode lifecycle 里有明确的阶段角色。这个阶段角色主要解释 seed-anchor 的 episode 状态，而不是 fresh-anchor 进入后的剩余收益。

更具体地说：

1. `early_confirmation` / `late_continuation` 对 seed-anchor 的 `P_good - P_bad` 提升非常明显，例如 `price_trend` late continuation 的 seed edge 为 +63.44 pp，`momentum_rps` late continuation 为 +59.69 pp，`volatility_band` late continuation 为 +57.86 pp。
2. 同一批 stage-role 在 fresh-anchor 上仍然普遍是负 edge，`fresh_P_bad` 大多在 58%~65%，`fresh_P_good` 大多在 33%~39%。所以它们像是“已跑出来的 episode 状态标签”，不是“等到该 family 再入场”的 alpha。
3. prefix order 加入 price-state 后 denominator 迅速塌缩，validation 只有 34/666 个 sufficient buckets。pair order 虽然 denominator 够，但 validation 的 fresh big-winner weighted abs lift 只有 0.76 pp，weighted signed lift 约为 0。last-added family 只有 validation 2 个 sufficient buckets，无法解释。
4. survival conditioning 不是坏事，可以理解为 probe lifecycle 的自然过滤。但 R03d 要回答的是 survived 之后 `kth/order/family` 是否还有增量 edge，答案是否定的。

因此，本实验应收敛为：保留 stage-role 作为持仓状态和后续诊断协变量；不要把 family order、ordered prefix、last-added family 写成 entry / add / position sizing 规则。

## 2. 数据口径与审计

本次报告只更新 markdown 报告，不更新 runner / validator / config。结构化产物来自：

- `r03d_family_position_summary.csv`
- `r03d_next_family_given_prefix_summary.csv`
- `r03d_pair_order_asymmetry_summary.csv`
- `r03d_last_added_family_price_conditioned_summary.csv`
- `r03d_order_explanatory_power_comparison.csv`
- `r03d_order_split_stability_audit.csv`
- `r03d_denominator_and_survival_audit.csv`
- cache panel: `r03d_stage_role_panel.parquet`, `r03d_order_transition_candidate_panel.parquet`

重要口径说明：自动生成的 `r03d_stage_role_summary.csv` 在 stage-role 计数上存在重复计数迹象，例如 all split 的 `range_breakout / probe_candidate` 行为 16,980，而去重后的 seed-stage count 为 8,490。为了避免把重复计数写进研究结论，本报告的 stage-role 细表以 `r03d_stage_role_panel.parquet` 去重后按同一 stage-role 规则重新聚合；order explanatory power、pair order、last-added family 等决策表仍直接引用对应 CSV。

manifest row counts:

| artifact | row_count |
|:--|--:|
| seed episodes | 11,003 |
| fresh steps | 12,302 |
| stage role panel rows | 77,021 |
| transition candidate rows | 74,305 |
| pair order rows | 113,908 |

## 3. Denominator 与 Survival

| split | seed episodes | first clean fresh | first clean fresh rate | failed before first clean fresh | failed rate | no clean fresh | no clean fresh rate | transition candidates | actual transitions | same-offset multi-family steps | same-offset step rate |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 5,139 | 2,851 | 55.48% | 2,227 | 43.34% | 2,288 | 44.52% | 33,302 | 9,562 | 2,239 | 40.34% |
| validation | 2,891 | 1,675 | 57.94% | 1,194 | 41.30% | 1,216 | 42.06% | 20,006 | 5,414 | 1,275 | 40.48% |
| robustness | 2,973 | 1,817 | 61.12% | 1,079 | 36.29% | 1,156 | 38.88% | 20,997 | 6,259 | 1,459 | 40.51% |
| all | 11,003 | 6,343 | 57.65% | 4,500 | 40.90% | 4,660 | 42.35% | 74,305 | 21,235 | 4,973 | 40.42% |

这个 denominator 说明两件事：

1. 约 40.9% seed 在第一根 clean fresh 前已经失败，这个 survival conditioning 可以视为 probe 过滤的一部分，而不一定是坏事。
2. 但如果研究目标是“等后续 family 出现再加仓或入场”，就必须在 survived 子集里证明 fresh-anchor 或 remaining-path 有增量。R03d 没做到。

另一个关键事实是 same-offset multi-family step rate 稳定在约 40%。大量 family 是同一 offset 同时出现，天然削弱了“严格先后顺序”的可辨识度。

## 4. Family 首次出现阶段

| family | seed count | fresh_1 | fresh_2 | fresh_3 | fresh_4plus | fresh total | not observed | seed rate | fresh rate | not observed rate |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| range_breakout | 8,490 | 1,166 | 255 | 18 | 0 | 1,439 | 1,074 | 77.16% | 13.08% | 9.76% |
| volume_money | 4,339 | 1,790 | 933 | 325 | 76 | 3,124 | 3,540 | 39.43% | 28.39% | 32.17% |
| pullback_drawdown | 3,369 | 2,662 | 693 | 274 | 79 | 3,708 | 3,926 | 30.62% | 33.70% | 35.68% |
| price_trend | 3,708 | 1,282 | 789 | 381 | 157 | 2,609 | 4,686 | 33.70% | 23.71% | 42.59% |
| momentum_rps | 3,266 | 1,890 | 730 | 357 | 156 | 3,133 | 4,604 | 29.68% | 28.47% | 41.84% |
| volatility_band | 2,992 | 1,703 | 1,181 | 455 | 120 | 3,459 | 4,552 | 27.19% | 31.44% | 41.37% |
| oscillator | 2,387 | 1,810 | 1,365 | 469 | 119 | 3,763 | 4,853 | 21.69% | 34.20% | 44.11% |

直观分工比较清楚：

- `range_breakout` 是最典型的 seed/probe family，77.16% 的 seed episode 在 seed 阶段已经出现。
- `oscillator`、`volatility_band`、`pullback_drawdown` 更常作为 fresh 阶段的补充信息出现，fresh rate 分别为 34.20%、31.44%、33.70%。
- `price_trend`、`momentum_rps` 既有 seed 角色，也常在较后阶段作为 continuation / 已上涨状态的确认。

这支持“family 有 stage role”的方向，但还不能支持“顺序有可交易增量”。

## 5. Stage Role 详细结果

### 5.1 Probe Candidate

probe candidate 是 seed 阶段或很早出现的 family。它不是一个正 edge 入场规则：所有 family 的 seed edge 仍为负，基本接近 R02 single-family baseline 的坏路径占优形态。

| family | episode_count | seed_P_good | seed_P_bad | seed edge |
|:--|--:|--:|--:|--:|
| range_breakout | 8,490 | 35.77% | 60.77% | -25.00 pp |
| volume_money | 4,339 | 34.53% | 62.71% | -28.19 pp |
| volatility_band | 2,992 | 36.16% | 61.31% | -25.15 pp |
| oscillator | 2,387 | 36.64% | 60.36% | -23.73 pp |
| pullback_drawdown | 3,369 | 34.28% | 64.57% | -30.28 pp |
| momentum_rps | 3,266 | 33.39% | 65.24% | -31.86 pp |
| price_trend | 3,708 | 34.06% | 64.65% | -30.59 pp |

这说明“第一个 family 是什么”本身没有把单信号负 edge 反转成正 edge。probe 的价值在于后续观察，而不是 seed 当下直接下注。

### 5.2 Early Confirmation 与 Late Continuation

| family | stage_role | count | median wait return | up 10%+ share | seed_P_good | seed_P_bad | seed edge | fresh_P_good | fresh_P_bad | fresh edge | fresh BW |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| momentum_rps | early_confirmation | 1,890 | 3.97% | 8.68% | 63.61% | 35.06% | +28.54 pp | 32.80% | 65.19% | -32.39 pp | 12.70% |
| momentum_rps | late_continuation | 1,243 | 6.52% | 21.16% | 78.69% | 19.00% | +59.69 pp | 34.68% | 62.27% | -27.59 pp | 8.63% |
| oscillator | early_confirmation | 1,810 | 3.66% | 11.55% | 66.27% | 29.23% | +37.04 pp | 38.93% | 56.65% | -17.72 pp | 9.50% |
| oscillator | late_continuation | 1,834 | 6.18% | 24.97% | 75.14% | 21.12% | +54.02 pp | 36.19% | 60.21% | -24.01 pp | 9.86% |
| price_trend | early_confirmation | 1,282 | 5.61% | 12.95% | 74.34% | 24.39% | +49.95 pp | 35.90% | 61.83% | -25.94 pp | 13.27% |
| price_trend | late_continuation | 1,327 | 7.14% | 21.48% | 80.72% | 17.29% | +63.44 pp | 36.95% | 60.34% | -23.39 pp | 9.51% |
| pullback_drawdown | early_confirmation | 2,662 | 3.36% | 6.61% | 58.60% | 39.18% | +19.42 pp | 34.12% | 64.03% | -29.91 pp | 12.19% |
| pullback_drawdown | late_continuation | 1,046 | 5.57% | 11.19% | 74.85% | 21.86% | +53.00 pp | 37.77% | 58.15% | -20.38 pp | 6.88% |
| range_breakout | early_confirmation | 1,166 | 2.95% | 6.86% | 58.13% | 39.18% | +18.95 pp | 36.26% | 60.93% | -24.68 pp | 12.90% |
| range_breakout | late_continuation | 273 | 5.34% | 16.85% | 72.69% | 25.55% | +47.14 pp | 37.27% | 60.45% | -23.18 pp | 13.36% |
| volatility_band | early_confirmation | 1,703 | 3.87% | 10.86% | 63.91% | 30.50% | +33.41 pp | 36.78% | 58.75% | -21.97 pp | 10.10% |
| volatility_band | late_continuation | 1,636 | 6.35% | 22.68% | 77.32% | 19.46% | +57.86 pp | 36.60% | 60.95% | -24.35 pp | 11.39% |
| volume_money | early_confirmation | 1,790 | 2.35% | 7.60% | 59.15% | 35.00% | +24.15 pp | 39.22% | 56.66% | -17.44 pp | 9.54% |
| volume_money | late_continuation | 1,258 | 6.23% | 26.15% | 75.15% | 21.84% | +53.30 pp | 36.48% | 60.64% | -24.16 pp | 11.04% |

这张表是 R03d 最重要的结果。每个 family 到了 early/late 阶段后，seed-anchor 口径几乎都从负 edge 变成强正 edge；但 fresh-anchor 口径仍然是负 edge。也就是说，后续 family 的出现确实说明原 episode 已经“活过来”或“正在延续”，但它没有说明在后续 family 出现时再入场可以取得同等 edge。

这也解释了为什么 R03b/R03c 里 seed-anchor 看起来会改善：改善主要来自 survival + wait-return + episode 已经进入好状态，而不是 fresh signal 本身在 entry anchor 上变强。

### 5.3 Lagging Price-State Proxy

| family | count | median wait return | up 10%+ share | seed edge | fresh edge | fresh BW |
|:--|--:|--:|--:|--:|--:|--:|
| oscillator | 119 | 10.74% | 56.30% | +80.95 pp | -29.41 pp | 13.86% |
| volatility_band | 120 | 11.43% | 60.83% | +77.67 pp | -40.59 pp | 14.00% |
| volume_money | 76 | 12.51% | 61.84% | +82.35 pp | -21.21 pp | 12.70% |

lagging price-state proxy 的 seed edge 很高，但它的定义本身已经包含较强 wait-return / price-state 条件，且 count 小。它更像“涨了一段以后才出现的滞后确认”，不适合作为新增入场证据。

## 6. Order Explanatory Power

| scheme | validation sufficient | robustness sufficient | validation fresh BW abs lift | robustness fresh BW abs lift | validation path-edge abs lift | robustness path-edge abs lift | conclusion |
|:--|--:|--:|--:|--:|--:|--:|:--|
| ordered_prefix | 49/218 = 22.48% | 56/218 = 25.69% | 1.47 pp | 2.52 pp | 8.52 pp | 7.13 pp | 原始 prefix 有一些描述性分层，但 signed lift 约为 0 |
| price_state_plus_ordered_prefix | 34/666 = 5.11% | 42/660 = 6.36% | 2.15 pp | 2.95 pp | 10.90 pp | 10.37 pp | 加入 price-state 后 denominator 塌缩 |
| pair_order | 62/63 = 98.41% | 62/63 = 98.41% | 0.76 pp | 2.05 pp | 3.89 pp | 4.47 pp | denominator 足够，但增量弱，signed lift 约为 0 |
| pair_wait_state_plus_order | 131/333 = 39.34% | 141/344 = 40.99% | 1.84 pp | 2.96 pp | 6.85 pp | 7.00 pp | 加 wait state 后仍无方向性 order edge |
| kth_offset_price_state_plus_last_added_family | 4/410 = 0.98% | 4/457 = 0.88% | 4.11 pp | 5.64 pp | 22.79 pp | 21.25 pp | lift 看起来大，但 denominator 不可用 |

解释要点：

- `weighted_abs_lift_vs_parent` 不是自动可交易 edge。它可以被局部 sparse bucket、price-state、survival conditioning 放大。
- `weighted_signed_lift_vs_parent` 在这些 scheme 里都接近 0，说明没有稳定方向性。
- 真正应该看的不是“有没有某个 bucket 很高”，而是相同 parent 下 ordered 是否持续优于 unordered / price-state / wait-state。R03d 没有给出这个证据。

## 7. Prefix Order 结果

prefix candidate panel 共有 74,305 行，actual transitions 21,235 行。按 coarse prefix count 聚合后，真实发生的下一 family 并没有形成稳定正 edge。样例：

| prefix count | candidate next family | true weight | false weight | BW true | BW false | BW delta | edge true | edge false | edge delta |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 3 | volatility_band | 200.5 | 372.8 | 4.86% | 12.19% | -7.32 pp | -16.71 pp | -9.66 pp | -7.05 pp |
| 1 | momentum_rps | 129.8 | 513.5 | 12.07% | 5.43% | +6.63 pp | -24.52 pp | -7.04 pp | -17.48 pp |
| 1 | price_trend | 103.8 | 532.8 | 12.20% | 5.66% | +6.54 pp | -17.82 pp | -8.70 pp | -9.12 pp |
| 1 | pullback_drawdown | 158.2 | 442.8 | 11.06% | 4.61% | +6.45 pp | -21.71 pp | -4.89 pp | -16.81 pp |
| 2 | momentum_rps | 123.6 | 513.8 | 10.52% | 4.76% | +5.76 pp | -20.87 pp | -4.94 pp | -15.93 pp |
| 2 | pullback_drawdown | 165.6 | 424.6 | 9.18% | 4.42% | +4.76 pp | -18.36 pp | -1.88 pp | -16.47 pp |
| 2 | oscillator | 186.8 | 451.0 | 6.10% | 9.59% | -3.49 pp | -10.81 pp | -8.96 pp | -1.86 pp |
| 4plus | price_trend | 405.5 | 800.5 | 6.49% | 4.24% | +2.26 pp | -18.00 pp | -5.68 pp | -12.32 pp |

有些 candidate true 的 big-winner rate 会高于 false，但 path edge 经常更差。这个分裂很关键：如果只盯 big-winner，会误以为 order 有信息；但综合 `P_good - P_bad` 后，下一 family 的出现更多是在高波动、坏路径仍高的状态里发生。

## 8. Pair Order 结果

pair order 的好处是 denominator 足够，缺点是它仍然没有方向性增量。

| asymmetry_status | bucket rows | episode sum | median episode count | mean fresh BW | mean fresh P_good | mean fresh P_bad |
|:--|--:|--:|--:|--:|--:|--:|
| same_offset_only | 21 | 54,559 | 2,484 | 12.89% | 36.17% | 61.55% |
| candidate_order_asymmetry | 29 | 40,646 | 1,254 | 11.19% | 35.04% | 62.57% |
| no_material_asymmetry | 12 | 18,650 | 1,292 | 10.93% | 35.55% | 61.67% |
| insufficient_pair_denominator | 1 | 53 | 53 | 15.56% | 42.22% | 53.33% |

方向差最大的 pair 也没有形成一致的 path-edge 方向：

| unordered pair | A before B count | B before A count | BW A before B | BW B before A | BW delta | path-edge delta |
|:--|--:|--:|--:|--:|--:|--:|
| price_trend \| volatility_band | 1,083 | 912 | 16.30% | 6.17% | +10.13 pp | -16.32 pp |
| momentum_rps \| volatility_band | 1,225 | 1,258 | 16.16% | 7.15% | +9.01 pp | -7.54 pp |
| pullback_drawdown \| volatility_band | 1,502 | 1,440 | 14.43% | 6.39% | +8.04 pp | -9.95 pp |
| price_trend \| range_breakout | 334 | 2,152 | 17.58% | 10.41% | +7.17 pp | -9.03 pp |
| momentum_rps \| oscillator | 1,390 | 1,143 | 14.00% | 7.88% | +6.12 pp | +1.21 pp |
| price_trend \| volume_money | 983 | 1,464 | 14.21% | 8.69% | +5.52 pp | -3.70 pp |
| momentum_rps \| range_breakout | 531 | 2,582 | 15.38% | 10.23% | +5.15 pp | +7.08 pp |
| momentum_rps \| volume_money | 1,254 | 1,861 | 14.00% | 8.86% | +5.14 pp | +6.43 pp |

这张表不能被解读成 pair-order alpha。原因是：

- 大量 pair 是 same-offset-only，严格先后顺序不可观察。
- 若只看 BW delta，有些方向看起来不错；但对应 path-edge delta 经常为负，说明坏路径风险没有同步改善。
- `pair_order` 的 validation fresh BW abs lift 只有 0.76 pp，robustness 2.05 pp；在 wait-state parent 下仍然没有 signed lift。

## 9. Last-Added Family

last-added family 的 denominator 不支持结论。

| split | sufficient buckets | thin buckets |
|:--|--:|--:|
| train | 6 | 1,201 |
| validation | 2 | 825 |
| robustness | 2 | 965 |
| all | 17 | 1,650 |

all split 中 sufficient 的 cell 主要集中在第 1 根 fresh、t3_t5、up_0_5pct 这类早期状态，不足以证明 last-added family 本身有独立作用：

| kth | offset bucket | wait bucket | last-added family set | fresh steps | fresh BW | fresh P_good | fresh P_bad |
|--:|:--|:--|:--|--:|--:|--:|--:|
| 1 | t3_t5 | up_0_5pct | pullback_drawdown | 536 | 14.06% | 30.77% | 67.65% |
| 1 | t3_t5 | up_0_5pct | momentum_rps \| pullback_drawdown | 401 | 10.93% | 38.92% | 58.23% |
| 1 | t3_t5 | up_0_5pct | range_breakout | 225 | 10.22% | 36.84% | 61.05% |
| 1 | t6_t10 | up_0_5pct | volume_money | 220 | 8.05% | 40.12% | 55.81% |
| 1 | t3_t5 | down_or_flat | pullback_drawdown | 175 | 9.42% | 35.97% | 61.87% |
| 1 | t3_t5 | up_0_5pct | volatility_band | 169 | 6.20% | 31.54% | 60.77% |
| 1 | t3_t5 | up_0_5pct | momentum_rps | 168 | 12.12% | 26.28% | 71.53% |
| 1 | t3_t5 | up_0_5pct | volume_money | 158 | 10.24% | 41.86% | 50.39% |
| 1 | t3_t5 | up_0_5pct | oscillator | 142 | 5.45% | 46.96% | 46.09% |
| 2 | t11_t20 | up_0_5pct | volume_money | 137 | 5.77% | 32.69% | 62.50% |

这个方向应该停止在 descriptive level。继续从完整 last-added family set 里找 pattern，统计上会非常稀疏。

## 10. 研究发现

### 10.1 7 个 family 有阶段角色，但阶段角色不等于顺序 alpha

`range_breakout` 更像 probe family；`oscillator`、`volatility_band`、`pullback_drawdown` 常在 fresh 阶段出现；`price_trend` 和 `momentum_rps` 的 late continuation 对 seed-anchor 状态很强。但这些都是 lifecycle 信息，不是 fresh-entry 信息。

核心证据是同一行里 seed edge 与 fresh edge 的反向分裂：late continuation 的 seed edge 往往 +50 pp 以上，但 fresh edge 仍是 -20 pp 到 -28 pp 左右。换句话说，后续 family 出现时，原 episode 已经变好了；但从该点重新买入，坏路径仍然占优。

### 10.2 Survival 是 probe filter，不是本实验的失败点

40.9% seed 在第一根 clean fresh 前失败，这可以被解释成第一阶段 probe 的过滤效果。真正的问题不是“survival bias 太强所以不能看”，而是：在 survive 之后，kth/order/family 是否还能提供边际 edge。

R03d 的答案是没有。stage-role 可以解释“为什么活下来的 episode 看起来更好”，但 order 本身没有通过 price-state / wait-state parent 的增量检验。

### 10.3 Big winner 与 path quality 会分裂，不能只看 BW

prefix 和 pair 表里都能看到局部 BW delta 为正的例子，例如 `price_trend | volatility_band` 的 A-before-B BW 比 B-before-A 高 10.13 pp。但同一行 path-edge delta 是 -16.32 pp。这类信号不能被升级为 entry rule，因为它更像“上行尾部和坏路径风险同时放大”。

后续如果继续看 sequence，只能用 reward-adjusted 或 path-risk-adjusted 指标，而不能用 raw big-winner rate 单独筛选。

### 10.4 Family order 的最大问题是可观察顺序不稳定

same-offset multi-family step rate 约 40%，same-offset pair count 54,559，高于 candidate_order_asymmetry 的 episode sum 40,646。大量 family 是同时出现，不是先后出现。完整 ordered prefix 进一步拆分后，price-state-aware denominator 只有 5%~6% sufficient buckets。

这意味着 order pattern 的有效独立样本远少于表面 pair rows。继续增加 prefix 长度，只会更稀疏。

## 11. 我的独立判断

这条 R03d 路线的结论不是“family 信息无用”，而是“family 顺序不应作为 entry/add 维度”。更合理的落点是：

1. seed/probe 阶段：`range_breakout`、`volume_money`、`oscillator` 等仍可作为单 family probe 候选，但必须叠加 entry timing / price-risk gate；单 family 本身仍是负 edge。
2. hold-state 阶段：`price_trend`、`momentum_rps`、`volatility_band` 的 late continuation 可以作为“episode 已进入较强状态”的描述变量，用于持仓监控或退出延后，不应用于 fresh-entry 加仓。
3. sequence/order 阶段：ordered prefix、pair direction、last-added family 都不值得进入 formal validation。当前 evidence 已足够支持停止这条 order-alpha 搜索。
4. 后续研究预算应转向两个更窄的问题：一是 single-family + entry timing 的可执行入场质量；二是 has-fresh / late-continuation 作为 hold/exit state 的剩余价值，而不是作为新增买点。

一句话总结：R03d 给出了一个干净的负面结果。7 个 family 的出现阶段有解释力，但解释的是 episode 已经活下来并上涨后的状态；family 出现顺序没有在 fresh-anchor 上提供稳定、可复用、可交易的增量 edge。

## 12. 解释边界

- 本实验只评估 family order 与 stage role 的描述性和增量解释力，不输出 entry / add / position sizing 规则。
- seed-anchor improvement = episode selection / survival / wait-return / state evidence。
- fresh-anchor improvement = possible remaining-path information。
- ordered <= unordered 表示没有顺序信息。
- ordered <= kth_offset_price_state / pair_wait_state / price_state_plus_unordered_prefix 表示 order 信息被 price-state 或 wait-state proxy 吸收。
- 除非后续实验明确支持 `supported_order_incremental_edge`，否则不得把 family order 写成可交易 alpha。
