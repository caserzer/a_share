# Risk-on R 系列 Density Compression Patch 报告

## 1. 一页结论

patch decision: `risk_on_r_series_no_compression_candidate`

preflight decision: `risk_on_r_series_density_binding_confirmed`

selected compression arm: `none`

本 patch 只评估 R 系列作为 risk_on high-recall / high-bridge source pool 的 density compression；它不是交易信号、不是模型、不是回测。

本次结论很明确：preflight 证明 R1/R2/R6/R7/R8 的 risk_on 问题主要是 density-binding，不是 bridge-binding；但当前 deterministic compression arms 没有任何一个能同时通过 train recall、train bridge、density、p95 与 family-share guard，因此输出 `risk_on_r_series_no_compression_candidate`。这是有效实验结论，不应改用 validation / robustness 表现更好的 arm 来补救。

frontier 通过项计数：train recall `24/24`，train bridge `19/24`，density `<= 1.0x` `1/24`，p95 `<= 4` `3/24`，single-family share `<= 65%` `13/24`。瓶颈仍然集中在 density / p95 / concentration。

## 2. Preflight 复核

- family-level confirmed core families: `R1_relative_strength_breakout,R2_near_high_volume_expansion,R6_market_breadth_thrust,R7_cross_sectional_momentum_rank_jump,R8_persistent_distance_above_ema`
- variant-level confirmed core families: `R1_relative_strength_breakout,R2_near_high_volume_expansion,R6_market_breadth_thrust,R7_cross_sectional_momentum_rank_jump,R8_persistent_distance_above_ema`
- R5 negative control confirmed: `True`

| family_id | episode_split | incremental_recall_over_e1 | bridge_recall_delta_vs_e1 | density_vs_e1_full_denominator | events_per_instrument_year_p95 | density_binding_flag |
| --- | --- | --- | --- | --- | --- | --- |
| R1_relative_strength_breakout | robustness | 40.9% | 19.9% | 2.72x | 7.0 | True |
| R1_relative_strength_breakout | train | 34.7% | 14.4% | 2.72x | 7.0 | True |
| R2_near_high_volume_expansion | robustness | 29.3% | 12.7% | 1.63x | 5.0 | True |
| R2_near_high_volume_expansion | train | 33.3% | 5.8% | 1.63x | 5.0 | True |
| R5_growth_or_small_style_confirmation | robustness | 2.2% | -27.1% | 0.33x | 5.0 | False |
| R5_growth_or_small_style_confirmation | train | 4.9% | -22.7% | 0.33x | 5.0 | False |
| R6_market_breadth_thrust | robustness | 42.5% | 26.5% | 3.22x | 8.0 | True |
| R6_market_breadth_thrust | train | 34.7% | 15.3% | 3.22x | 8.0 | True |
| R7_cross_sectional_momentum_rank_jump | robustness | 38.1% | 18.3% | 1.92x | 5.0 | True |
| R7_cross_sectional_momentum_rank_jump | train | 29.8% | 7.1% | 1.92x | 5.0 | True |
| R8_persistent_distance_above_ema | robustness | 35.4% | 10.2% | 2.21x | 7.0 | True |
| R8_persistent_distance_above_ema | train | 32.9% | 6.7% | 2.21x | 7.0 | True |

R5 是关键反例：它 density 低，但 recall 与 bridge 都差，因此 low density 本身不是好信号。R1/R2/R6/R7/R8 则相反：recall 与 bridge 均为正，主要卡在 density 和 p95。

原 08 的 `train_selection_max_density_vs_e1 = 0.50` 对 risk_on R 系列有害，因为它会把这些 high-bridge R family 在 selection 前置阶段排除，只留下低 density 但 bridge 更弱的候选。

## 3. Scope 与 Source Pool

preflight 的 family all-variants 只用于诊断机制；真正实现从 candidate family variant / event level 开始。默认 source policy 是 `event_regime_gated_first`，ungated 只作为 upper bound / sensitivity。

| source_pool_id | family_id | variant_ids | source_event_count | scored_event_count | unscored_event_count | score_availability_status | compression_source_variant_policy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| raw_r_series_variant_pool | R1_relative_strength_breakout | event_regime_gated;ungated | 31385 | 14363 | 17022 | available;score_source_column_missing | all_runnable_variants_upper_bound |
| raw_r_series_variant_pool | R2_near_high_volume_expansion | event_regime_gated;ungated | 20279 | 0 | 20279 | core_semantic_score_unavailable | all_runnable_variants_upper_bound |
| raw_r_series_variant_pool | R6_market_breadth_thrust | event_regime_gated;ungated | 35958 | 16204 | 19754 | available;score_source_column_missing | all_runnable_variants_upper_bound |
| raw_r_series_variant_pool | R7_cross_sectional_momentum_rank_jump | event_regime_gated;ungated | 21773 | 9786 | 11987 | available;score_source_column_missing | all_runnable_variants_upper_bound |
| raw_r_series_variant_pool | R8_persistent_distance_above_ema | event_regime_gated;ungated | 26777 | 12896 | 13881 | available;score_source_column_missing | all_runnable_variants_upper_bound |
| event_regime_gated_source_pool | R1_relative_strength_breakout | event_regime_gated | 14363 | 14363 | 0 | available | event_regime_gated_first |
| event_regime_gated_source_pool | R2_near_high_volume_expansion | event_regime_gated | 9537 | 0 | 9537 | core_semantic_score_unavailable | event_regime_gated_first |
| event_regime_gated_source_pool | R6_market_breadth_thrust | event_regime_gated | 16204 | 16204 | 0 | available | event_regime_gated_first |
| event_regime_gated_source_pool | R7_cross_sectional_momentum_rank_jump | event_regime_gated | 9786 | 9786 | 0 | available | event_regime_gated_first |
| event_regime_gated_source_pool | R8_persistent_distance_above_ema | event_regime_gated | 12896 | 12896 | 0 | available | event_regime_gated_first |

raw R pool 事件数 `61960`，density `9.09x`，p95 `24.0`；event-regime-gated source pool 事件数 `47929`，density `7.03x`，p95 `20.0`。gated 起步降低了密度，但仍远高于 `<= 1.0x` gate。

## 4. Score Spec 与字段约束

当前 `cross_section_feature_panel.parquet` 冻结为 31 列：

```text
date, return_1d, return_5d, return_20d, return_60d, stock_vs_market_20d, close_to_high_60, rolling_high_60, close, market_regime_bucket, instrument, board_bucket, total_market_cap_cny, history_observed_sessions_before_usable_date, momentum_percentile_20d, momentum_percentile_60d, new_high_60_flag, up_flag, momentum_percentile_20d_lag20, evaluated_member_count, universe_up_share, universe_new_high_60_share, universe_equal_weight_return_x, universe_up_share_z, universe_up_share_change_5d, board_equal_weight_return, universe_equal_weight_return_y, board_relative_1d, board_relative_cusum_20d, board_return_20d, stock_vs_board_20d
```

本 patch 的 score spec 只使用这些 t0 可见字段。原 review 中提到但当前 panel 不可得的字段包括：`stock_vs_market_10d`、`close_to_ema60`、`close_to_ema20`、`ema60_positive_run`、`amount_ratio_20d`、`close_position_in_range`、`range_width_ratio_20d_60d`。这些字段不得被静默替代。

| family_id | score_fields | source_columns | score_status | proxy_score_used | recompute_required |
| --- | --- | --- | --- | --- | --- |
| R1_relative_strength_breakout | stock_vs_market_20d; stock_vs_board_20d; return_60d | stock_vs_market_20d; stock_vs_board_20d; return_60d | available | False | False |
| R2_near_high_volume_expansion | non_scored_volume_unavailable |  | core_semantic_score_unavailable | False | True |
| R3_vcp_breakout | close_to_high_60 | close_to_high_60 | available | True | False |
| R6_market_breadth_thrust | universe_up_share_z; universe_up_share_change_5d | universe_up_share_z; universe_up_share_change_5d | available | False | False |
| R7_cross_sectional_momentum_rank_jump | momentum_percentile_20d; momentum_percentile_20d_delta | momentum_percentile_20d; momentum_percentile_20d;momentum_percentile_20d_lag20 | available | False | False |
| R8_persistent_distance_above_ema | return_60d; momentum_percentile_60d; close_to_high_60 | return_60d; momentum_percentile_60d; close_to_high_60 | available | True | False |

R8 的 EMA-distance 原始字段不可得，因此显式使用 `return_60d` / `momentum_percentile_60d` / `close_to_high_60` 作为 proxy，并在 score spec 中标记 `proxy_score_used = true` 与 `missing_semantic_feature = ema_distance`。

R2 的核心语义是 near-high volume expansion，但当前 feature panel 没有 amount / volume 强度字段，因此 R2 默认是 non-scored core family。R2-only canonical events 采用 `unscored_canonical_policy = retain_and_audit`：不参与 score 排序，但保留并计入 density / recall / bridge / overlap audit，禁止 silent drop。

R2 单 family arm 的审计读数：canonical events `9537`，unscored canonical events `9537`，unscored density share `100.0%`，train recall `32.9%`，train bridge delta `4.4%`，robustness recall `28.7%`，robustness bridge delta `7.7%`。它 recall 有价值，但 train bridge delta 低于 `+5 pct`，且 density / family-share 仍不过。

## 5. Compression Frontier

train-only selection 使用 train risk_on evidence；validation / robustness 是 read-only support/block，不参与换 arm。

### 5.1 Selection Score Top Arms

| compression_arm_id | event_count | density_vs_e1_full_denominator | events_per_instrument_year_p95 | single_family_density_share_max | train_risk_on_incremental_recall_over_e1 | train_risk_on_bridge_recall_delta_vs_e1 | robustness_risk_on_incremental_recall_over_e1 | robustness_risk_on_bridge_recall_delta_vs_e1 | failure_reason | selection_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_family_best_variant__R2_near_high_volume_expansion | 9537 | 1.40 | 4.00 | 100.0% | 32.9% | 4.4% | 28.7% | 7.7% | train_bridge;density;family_share_65 | 0.37 |
| single_family_best_variant__R7_cross_sectional_momentum_rank_jump | 9786 | 1.43 | 4.00 | 100.0% | 29.3% | 6.7% | 38.1% | 11.6% | density;family_share_65 | 0.28 |
| consensus_family_count__min3 | 3094 | 0.45 | 2.00 | 90.4% | 12.9% | -17.7% | 12.2% | -16.0% | train_bridge;family_share_65 | -0.32 |
| family_score_quantile_cut__q0975 | 10992 | 1.61 | 5.00 | 86.8% | 32.9% | 5.3% | 29.3% | 12.7% | density;p95;family_share_65 | -1.02 |
| consensus_family_count__min2 | 11007 | 1.61 | 5.00 | 67.0% | 30.7% | 6.5% | 34.3% | 9.9% | density;p95;family_share_65 | -1.05 |
| market_day_top_percentile__top5pct | 8734 | 1.28 | 5.00 | 73.7% | 23.6% | -4.9% | 24.9% | 0.7% | train_bridge;density;p95;family_share_65 | -1.05 |
| family_score_quantile_cut__q095 | 11773 | 1.73 | 5.00 | 81.0% | 32.9% | 5.3% | 30.4% | 14.4% | density;p95;family_share_65 | -1.25 |
| cooldown_after_selected_event__40d | 13954 | 2.05 | 5.00 | 44.4% | 31.1% | 15.6% | 38.1% | 21.3% | density;p95 | -1.54 |
| market_day_top_percentile__top10pct | 10846 | 1.59 | 6.00 | 62.0% | 25.3% | -2.7% | 29.8% | 5.2% | train_bridge;density;p95 | -2.53 |
| single_family_best_variant__R8_persistent_distance_above_ema | 12896 | 1.89 | 6.00 | 100.0% | 32.9% | 6.2% | 35.4% | 9.1% | density;p95;family_share_65 | -2.55 |

### 5.2 最接近 Density Gate 的 Arms

| compression_arm_id | event_count | density_vs_e1_full_denominator | events_per_instrument_year_p95 | single_family_density_share_max | train_risk_on_incremental_recall_over_e1 | train_risk_on_bridge_recall_delta_vs_e1 | failure_reason | selection_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| consensus_family_count__min3 | 3094 | 0.45 | 2.00 | 90.4% | 12.9% | -17.7% | train_bridge;family_share_65 | -0.32 |
| market_day_top_percentile__top5pct | 8734 | 1.28 | 5.00 | 73.7% | 23.6% | -4.9% | train_bridge;density;p95;family_share_65 | -1.05 |
| single_family_best_variant__R2_near_high_volume_expansion | 9537 | 1.40 | 4.00 | 100.0% | 32.9% | 4.4% | train_bridge;density;family_share_65 | 0.37 |
| single_family_best_variant__R7_cross_sectional_momentum_rank_jump | 9786 | 1.43 | 4.00 | 100.0% | 29.3% | 6.7% | density;family_share_65 | 0.28 |
| market_day_top_percentile__top10pct | 10846 | 1.59 | 6.00 | 62.0% | 25.3% | -2.7% | train_bridge;density;p95 | -2.53 |
| family_score_quantile_cut__q0975 | 10992 | 1.61 | 5.00 | 86.8% | 32.9% | 5.3% | density;p95;family_share_65 | -1.02 |
| consensus_family_count__min2 | 11007 | 1.61 | 5.00 | 67.0% | 30.7% | 6.5% | density;p95;family_share_65 | -1.05 |
| family_score_quantile_cut__q095 | 11773 | 1.73 | 5.00 | 81.0% | 32.9% | 5.3% | density;p95;family_share_65 | -1.25 |

### 5.3 Failure Distribution

| failure_reason | arm_count |
| --- | --- |
| density;p95 | 11 |
| density;p95;family_share_65 | 7 |
| train_bridge;density;p95 | 2 |
| density;family_share_65 | 1 |
| train_bridge;density;family_share_65 | 1 |
| train_bridge;family_share_65 | 1 |
| train_bridge;density;p95;family_share_65 | 1 |

唯一通过 `density <= 1.0x` 的 `consensus_family_count__min3` 把 density 压到 `0.45x`、p95 压到 `2.0`，但 train bridge delta 为 `-17.7 pct`，说明简单共振过滤会压坏 bridge quality。多数保持 bridge 的 arms 仍然 density / p95 过高。

## 6. Selected Pool

| metric | value |
|---|---:|
| train risk_on incremental recall | NA |
| robustness risk_on incremental recall | NA |
| train risk_on bridge delta | NA |
| robustness risk_on bridge delta | NA |
| density vs E1 | NAx |
| p95 events / instrument-year | NA |
| single-family density share max | NA |
| downstream 35 pct family-share pass | `False` |
| label completeness | NA |
| next-open executable | NA |
| unscored canonical events | 0 |

当前没有 selected compressed pool，因此 `risk_on_r_series_compressed_canonical_events.csv` 和 `risk_on_r_series_selected_compressed_variants.csv` 只有 schema / 空结果，可审计地表示没有 train-pass arm。selected event count = `0`。

validation risk_on denominator 小于 `30` 时只作 diagnostic。本次没有 selected arm，因此 validation / robustness 不触发 support；frontier 中仍保留所有 arms 的 read-only validation / robustness metrics。

## 7. Gate 解释与后续方向

`risk_on_r_series_density_still_blocked`、`risk_on_r_series_bridge_degraded_blocked`、`risk_on_r_series_overfit_blocked` 和本次的 `risk_on_r_series_no_compression_candidate` 都是可接受实验结论。它们说明当前 deterministic compression 还没有找到“保留 R 系列 high bridge，同时把 density 压到 1.0x 以下”的切法。

`single_family_density_share <= 65%` 是本 patch 的 meta-label feature-source concentration guard，不等于 downstream direct-entry union 的 35% family-share gate。frontier 中 `downstream_entry_family_share_35pct_pass` 仍作为 read-only diagnostic 输出；若未来某 arm 只在 35%-65% 之间通过，本 patch 只能支持它作为 meta-label feature source，不能直接作为 09 entry union。

与 `requirement_patch_regime_specific_unions.md` 的关系：regime-specific union patch 是消融诊断，回答 risk_on / transition 分开选是否改变结论；本 patch 是 risk_on P0 主线。对 risk_on R 系列，下一阶段重点不是再换 regime selection，而是在 high-bridge R-series 候选池上做更有监督边界的 density compression / ranker，例如 bridge-positive ranker 或显式 amount/volume recompute 后的 R2 score。

## 8. 深度发现：为什么这次没有 train-pass arm

### 8.1 event-regime-gated 只降低密度，不改变 binding constraint

按 variant-level spot check 看，`event_regime_gated` 确实比 all-variants 更干净，但它没有把任何核心 R family 压到可直接使用的 density 区间。

| family | split | gated incremental recall | gated bridge delta | gated density vs E1 | gated p95 | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| R1 | train | 34.2% | +14.0% | 2.11x | 6 | bridge 很强，density 仍过高 |
| R1 | robustness | 40.9% | +14.4% | 2.11x | 6 | robustness 不坍塌 |
| R6 | train | 34.7% | +14.4% | 2.38x | 6 | bridge 很强，density 仍过高 |
| R6 | robustness | 42.5% | +22.1% | 2.38x | 6 | risk_on 最强 source family |
| R7 | train | 29.3% | +6.7% | 1.43x | 4 | 最接近可用，但 single-family concentration 100% |
| R7 | robustness | 38.1% | +11.6% | 1.43x | 4 | out-of-sample bridge 仍为正 |
| R8 | train | 32.9% | +6.2% | 1.89x | 6 | recall 高，density/p95 不过 |
| R8 | robustness | 35.4% | +9.1% | 1.89x | 6 | bridge 没坏，但不够稀疏 |
| R2 | train | 32.9% | +4.4% | 1.40x | 4 | recall 高，但 train bridge 稍低于 +5 pct |
| R2 | robustness | 28.7% | +7.7% | 1.40x | 4 | robustness bridge 通过，但 R2 当前不可 score |
| R5 | train | 4.9% | -22.7% | 0.28x | 4 | negative control：低密度但低质量 |
| R5 | robustness | 2.2% | -27.1% | 0.28x | 4 | 证明“低密度 != 好信号” |

这张表把核心机制拆清楚了：`event_regime_gated` 对 R 系列是必要但远远不充分。它保留了 high bridge，同时只把密度从 raw R pool 的 `9.09x` 压到 gated source pool 的 `7.03x`；要进入下一阶段，还需要再压约 85% 的 canonical events，且不能把 bridge-positive coverage 一起压掉。

### 8.2 Compression frontier 的真正两难

当前 deterministic arms 可以分成两类失败：

1. 保留 bridge 的 arms 仍然过密。
2. 真正压低 density 的 arms 会损坏 bridge。

| arm | event count | density vs E1 | p95 | train recall | train bridge delta | robustness bridge delta | 主要失败 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| raw_r_series_variant_pool | 61,960 | 9.09x | 24 | 36.0% | +20.0% | +35.7% | density / p95 |
| event_regime_gated_only | 47,929 | 7.03x | 20 | 35.6% | +19.6% | +32.4% | density / p95 |
| cooldown_after_selected_event__40d | 13,954 | 2.05x | 5 | 31.1% | +15.6% | +21.3% | density / p95 |
| family_score_quantile_cut__q0975 | 10,992 | 1.61x | 5 | 32.9% | +5.3% | +12.7% | density / p95 / family share |
| consensus_family_count__min2 | 11,007 | 1.61x | 5 | 30.7% | +6.5% | +9.9% | density / p95 / family share |
| R7 single-family | 9,786 | 1.43x | 4 | 29.3% | +6.7% | +11.6% | density / family share |
| R2 single-family | 9,537 | 1.40x | 4 | 32.9% | +4.4% | +7.7% | train bridge / density / family share |
| market_day_top_percentile__top5pct | 8,734 | 1.28x | 5 | 23.6% | -4.9% | +0.7% | bridge / density / p95 / family share |
| consensus_family_count__min3 | 3,094 | 0.45x | 2 | 12.9% | -17.7% | -16.0% | bridge / family share |

最关键的对比是 `cooldown_after_selected_event__40d` 与 `consensus_family_count__min3`：

- `cooldown_40d` 保留了 train bridge +15.6 pct、robustness bridge +21.3 pct，但 density 仍有 2.05x，p95 仍是 5。
- `consensus_min3` 把 density 压到 0.45x、p95 压到 2，但 train bridge 变成 -17.7 pct。

因此当前结果不是“threshold 不够 aggressive”，而是“aggressive 的 deterministic filter 选错了要保留的事件”。这正是后续需要 supervised / bridge-positive ranker 的原因。

### 8.3 R2 当前是 density floor，不是可排序 alpha

R2 的核心语义是 near-high volume expansion，但当前 frozen panel 没有 amount / volume 字段，所以实现正确地把 R2 标为 non-scored，并对 R2-only canonical events 采用 `retain_and_audit`。这个策略避免了 silent drop，但也带来一个副作用：score-dependent arms 里 R2 形成一个很硬的 density floor。

| arm | event count | unscored canonical events | unscored share | density vs E1 | train bridge delta | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| R2 single-family | 9,537 | 9,537 | 100.0% | 1.40x | +4.4% | R2 自身已经超过 density gate |
| family_score_quantile_cut__q0975 | 10,992 | 9,233 | 84.0% | 1.61x | +5.3% | 高分 cut 主要剩 R2 unscored floor |
| family_score_quantile_cut__q095 | 11,773 | 9,077 | 77.1% | 1.73x | +5.3% | score cut 越严，R2 占比越高 |
| market_day_top_percentile__top5pct | 8,734 | 6,040 | 69.2% | 1.28x | -4.9% | market-day top pct 也压不掉 R2 floor |
| event_regime_gated_only | 47,929 | 6,040 | 12.6% | 7.03x | +19.6% | R2 不是唯一密度源，但在 score arms 中变成主导残留 |

这解释了一个容易误读的现象：`family_score_quantile_cut__q0975` 看起来已经很激进，但 density 仍有 1.61x，因为它不是在所有 family 上等比例压缩；R1/R6/R7/R8 的 scored events 被大量切掉后，R2 unscored events 被 retain-and-audit 留了下来，导致 remaining pool 更集中、更难通过 family-share gate。

对 R2 的下一步不能是用 `close_to_high_60` 冒充 volume expansion score；更合理的路径只有两条：

1. patch-local 从 source artifacts 重算 amount / volume expansion 字段，并在 manifest 中记录 `recomputed_from_source_artifacts = true`。
2. 继续把 R2 当 non-scored core family，但给它单独的 family budget / cooldown / bridge-positive gate，而不是让它无条件进入所有 score-dependent arms。

### 8.4 Label quality 不是这次失败原因

label 与 execution 质量整体很好，失败不是因为 label coverage 或 next-open 可执行性不足。

| arm | label completeness | next-open executable | event_big_winner_120d rate | density vs E1 | failure |
| --- | ---: | ---: | ---: | ---: | --- |
| consensus_family_count__min3 | 99.35% | 99.35% | 19.55% | 0.45x | bridge / family share |
| family_score_quantile_cut__q08 | 99.65% | 99.67% | 18.34% | 2.61x | density / p95 |
| market_day_top_percentile__top10pct | 99.61% | 99.67% | 18.09% | 1.59x | bridge / density / p95 |
| consensus_family_count__min2 | 99.60% | 99.64% | 17.97% | 1.61x | density / p95 / family share |
| R7 single-family | 99.67% | 99.81% | 17.04% | 1.43x | density / family share |

这里有一个重要 insight：`event_big_winner_120d_rate` 高不等于 episode-level bridge recall 好。`consensus_min3` 的 event-level big-winner rate 最高，但 bridge delta 明显为负；说明它保留的是“更像 big winner 的事件”，但没有覆盖足够多的 target episodes / bridge-positive opportunities。后续 ranker 的优化目标应优先是 bridge-positive episode coverage，而不是单纯 event-level precision。

### 8.5 validation 只能作为提示，不能作为选择依据

validation risk_on 的 denominator 只有 22，所有 validation 结果都应保持 diagnostic。

| arm | validation denominator | validation incremental captures | validation incremental recall |
| --- | ---: | ---: | ---: |
| raw_r_series_variant_pool | 22 | 13 | 59.1% |
| event_regime_gated_only | 22 | 13 | 59.1% |
| consensus_family_count__min2 | 22 | 13 | 59.1% |
| R2 single-family | 22 | 12 | 54.5% |
| family_score_quantile_cut__q0975 | 22 | 12 | 54.5% |
| cooldown_after_selected_event__40d | 22 | 12 | 54.5% |
| R7 single-family | 22 | 11 | 50.0% |
| market_day_top_percentile__top5pct | 22 | 8 | 36.4% |
| consensus_family_count__min3 | 22 | 6 | 27.3% |

这些数字可以说明某些 arms 没有在 validation 上立刻坍塌，但不能用来调 threshold。当前 report 的结论仍以 train-only selection + robustness support/block 为准。

## 9. 研究结论与下一步 patch 建议

### 9.1 最重要结论

对 risk_on R 系列，问题已经被进一步收窄：

```text
R 系列不是没有 recall，也不是 bridge quality 差；
问题是 high-bridge events 太密，而且简单 deterministic compression 无法保留正确的 bridge-positive 子集。
```

因此，本 patch 的失败不是负面结果，而是把研究方向从“找不找 R family”推进到“怎样在 R family 内部做 event selection”。

### 9.2 当前最接近可用的两个候选

1. `R7 single-family`：density 1.43x，p95 4，train bridge +6.7 pct，robustness bridge +11.6 pct。它最接近 density / p95 gate，但 single-family share 100%，不能作为 direct entry union。可作为 future meta-label feature source 或 family-budget ranker 的主成分。
2. `cooldown_after_selected_event__40d`：bridge 最稳定，train bridge +15.6 pct、robustness bridge +21.3 pct，但 density 仍 2.05x、p95 5。说明“时间去重”方向有效，但需要叠加 score/ranker，不足以单独通过。

### 9.3 不建议继续加简单阈值

继续在 `score_quantile`、`market_day_top_pct`、`consensus_count` 上扫更多阈值，大概率收益有限：

- `score_quantile` 越严，R2 unscored share 越高，family concentration 变差。
- `market_day_top_pct` 会降低密度，但 bridge 在 train 上已经转负。
- `consensus_count` 能压 density，但损坏 bridge-positive coverage。

这三类行为都指向同一个结论：当前 score 不是 bridge-positive ordering 的充分统计量。

### 9.4 推荐的新 patch 方向

下一份 patch 建议不要再做 regime-specific selection，也不要只扩大 deterministic grid。更有价值的是：

1. 构建 `risk_on_r_series_bridge_positive_ranker`，目标是 bridge-positive episode coverage，而不是 event-level 120d big-winner precision。
2. 从 `event_regime_gated` R1/R6/R7/R8 起步，R2 先单独处理；若要纳入 score ranker，先补 amount / volume expansion 字段。
3. 加 family-aware budget：例如每个 market day / instrument-month 内按 family 分配 quota，避免 R2 或 R7 单族占据 65%-100%。
4. 加 time deconcentration：保留 cooldown 的思想，但不要只按时间删事件，而是用 ranker 在 cooldown bucket 内选择 bridge-positive 概率最高的事件。
5. train-only 冻结 threshold；validation denominator 仍小，只做 diagnostic；robustness 只用于 support/block。

目标 gate 可以保持当前口径：

```text
train risk_on incremental recall >= +8 pct
train risk_on bridge delta >= +5 pct
robustness risk_on incremental recall >= +8 pct
robustness risk_on bridge delta >= +5 pct
density_vs_e1 <= 1.0x
p95 <= 4
single_family_density_share <= 65% for feature source
downstream direct-entry 仍需读 35% family-share diagnostic
```

如果 ranker 仍无法同时满足这些 gate，则可以明确得到更强结论：risk_on R 系列适合作为 explanatory / diagnostic source，不适合作为下一阶段 direct candidate pool。
