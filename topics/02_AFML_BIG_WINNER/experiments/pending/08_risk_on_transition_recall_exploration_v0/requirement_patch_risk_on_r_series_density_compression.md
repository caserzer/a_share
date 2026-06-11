# Requirement Patch: Risk-on R-series Density Compression

## 1. 背景与结论复核

当前 08 full run 的 selected joint union 选择了低 density 的 T4 / T7，但被 density family-share 与 bridge gate 否决。进一步拆开 `risk_on` 的 R 系列 artifact 后，结论更具体：

```text
对 risk_on 的 R 系列，除 R5 外，主要 binding constraint 是 density；
不是 recall 不足，也不是 bridge quality 不足。
```

本 patch 是一个新的 post-run / extension experiment，目标不是重新做 regime-specific union selection，而是专门回答：

```text
能否保留 R1/R6/R7/R8/R2 的高 recall + 高 bridge quality，
同时用二阶段 density compression / ranker 把事件密度压到可接受范围？
```

这是一个强假设实验：如果从 2x-3x E1 的 R-series source pool 压到 `<= 1.0x` E1 后，recall 或 bridge 明显坍塌，`risk_on_r_series_density_still_blocked`、`risk_on_r_series_bridge_degraded_blocked` 或 `risk_on_r_series_overfit_blocked` 都是有效结论。实现不得为了得到 supported decision 而使用 validation / robustness 反复调 threshold。

本 patch 不替代原 08 full run，也不覆盖 `requirement_patch_regime_specific_unions.md`。两者定位不同：

1. `requirement_patch_regime_specific_unions.md` 是 diagnostic / ablation，回答 risk_on 和 transition 分开选是否改变结论。
2. 本 patch 是 risk_on P0 主线，直接处理 R 系列“高质量但过密”的问题。

## 2. 已复核 evidence

以下数据来自当前 08 publishable artifacts：

1. `candidate_family_incremental_recall_over_e1.csv`
2. `candidate_family_bridge_positive_recall.csv`
3. `candidate_family_density_summary.csv`

口径：

```text
candidate_scope_type == candidate_family
variant_id == all_variants
market_regime_bucket == risk_on
window == before_first_50pct
split in {train, robustness}
bridge metric_basis == bridge_positive_event
```

### 2.1 R-series family-level evidence

| family | split | incremental recall over E1 | bridge recall | E1 bridge | bridge delta | density vs E1 | p95 events/IPY |
|---|---|---:|---:|---:|---:|---:|---:|
| R1 relative strength breakout | train | 34.7 pct | 43.3% | 28.9% | +14.4 pct | 2.72x | 7 |
| R6 market breadth thrust | train | 34.7 pct | 44.2% | 28.9% | +15.3 pct | 3.22x | 8 |
| R2 near-high volume expansion | train | 33.3 pct | 34.7% | 28.9% | +5.8 pct | 1.63x | 5 |
| R8 persistent distance above EMA | train | 32.9 pct | 35.6% | 28.9% | +6.7 pct | 2.21x | 7 |
| R7 cross-sectional momentum rank jump | train | 29.8 pct | 36.0% | 28.9% | +7.1 pct | 1.92x | 5 |
| R3 VCP breakout | train | 20.4 pct | 29.3% | 28.9% | +0.4 pct | 1.35x | 4 |
| R5 growth / small style confirmation | train | 4.9 pct | 6.2% | 28.9% | -22.7 pct | 0.33x | 5 |
| R6 market breadth thrust | robustness | 42.5 pct | 61.3% | 34.8% | +26.5 pct | 3.22x | 8 |
| R1 relative strength breakout | robustness | 40.9 pct | 54.7% | 34.8% | +19.9 pct | 2.72x | 7 |
| R7 cross-sectional momentum rank jump | robustness | 38.1 pct | 53.1% | 34.8% | +18.3 pct | 1.92x | 5 |
| R8 persistent distance above EMA | robustness | 35.4 pct | 45.0% | 34.8% | +10.2 pct | 2.21x | 7 |
| R2 near-high volume expansion | robustness | 29.3 pct | 47.5% | 34.8% | +12.7 pct | 1.63x | 5 |
| R3 VCP breakout | robustness | 20.4 pct | 40.6% | 34.8% | +5.7 pct | 1.35x | 4 |
| R5 growth / small style confirmation | robustness | 2.2 pct | 7.7% | 34.8% | -27.1 pct | 0.33x | 5 |

解释：

1. R1 / R6 / R7 / R8 / R2 在 risk_on 上同时满足 recall gate 与 bridge gate。
2. R3 recall 较低但仍明显为正，bridge 不差；它可以作为 optional support family。
3. R5 是反例：density 很低，但 recall 和 bridge 都差，必须默认排除或仅 diagnostic。
4. 现有 `train_selection_max_density_vs_e1 = 0.50` 会系统性排除 R1/R6/R7/R8/R2/R3，仅保留低 density 但低 bridge-quality 的 T4/T7 类候选。

### 2.2 Scope 粒度说明

§2.1 使用 `candidate_family__all_variants` 是为了回答 family-level 机制问题。实现时不得直接把 all-variants family 当作 entry union。真正可构建的 source pool 必须落到：

```text
candidate_scope_type == candidate_family_variant
```

并在 event level 做 density compression。

当前 variant-level 事实同样支持本 patch：

1. R1 / R6 / R7 / R8 / R2 的 ungated 与 event-regime-gated variants 在 `risk_on robustness` 上均有大幅正增量 recall。
2. event-regime-gated variant 能降低部分 density，但仍普遍高于 E1 的 1.4x 至 2.4x，不能直接通过 density gate。
3. 因此下一步不是再加一道简单 event-regime gate，而是做二阶段 event-level compression / ranker。

## 3. 本 patch 的目标

新增独立 experiment：

```text
08 risk-on R-series density compression patch
```

必须产出一个或多个：

```text
risk_on_r_series_compressed_candidate_pool
```

核心要求：

1. 以 R1/R6/R7/R8/R2 为默认 high-bridge source families。
2. R3 可作为 optional support family，但不得替代 R1/R6 主体。
3. R5 默认排除；若输出，必须标记为 diagnostic-only negative control。
4. selection / compression threshold 只能使用 train risk_on evidence。
5. validation / robustness 只做 read-only evaluation，不得调参。
6. 不得按 target episode membership 过滤 events。
7. 不得覆盖原 08 full run outputs、report、manifest。

## 4. 非目标

本 patch 不做：

1. 交易策略、组合回测、收益曲线、仓位模拟。
2. 使用 future return / MFE / first-50pct touch 构造事件。
3. 用 validation 或 robustness 调 compression threshold。
4. 直接把 R-series raw all-variants 作为 selected union。
5. 重新定义 risk_on regime。
6. 重新生成 06 denominator 或 07 baseline。
7. 用 target episode captured / missed 标签反向生成 event。

如果实现 supervised ranker，ranker 只能是候选事件筛选器，不得被报告为交易模型。

## 5. 输入与只读边界

本 patch 是 08 full run 的只读 extension。必须读取并校验：

1. `outputs/manifests/run_manifest.json`
2. `candidate_family_event_instances.csv`
3. `candidate_family_canonical_events.csv`
4. `candidate_family_incremental_recall_over_e1.csv`
5. `candidate_family_bridge_positive_recall.csv`
6. `candidate_family_bridge_exclusion_audit.csv`
7. `candidate_family_density_summary.csv`
8. `candidate_family_label_quality_readout.csv`
9. `candidate_family_false_repair_diagnostic.csv`
10. `candidate_family_overlap_matrix.csv`
11. `candidate_family_cluster_ablation.csv`
12. `candidate_vs_e1_timing_basis_comparison.csv`
13. `candidate_family_run_capability_summary.csv`
14. `regime_recall_baseline_07_e1_only.csv`
15. 当前 patch requirement 文件自身。

若需要 event-level scoring / ranker，还必须读取：

1. `outputs/local_cache/candidate_family_event_labels.parquet`
2. `outputs/local_cache/candidate_family_capture.parquet`
3. `outputs/local_cache/cross_section_feature_panel.parquet`
4. 原 08 config 与 source git revision。

以下 source 路径必须视为 read-only：

```text
outputs/publishable/tables/
outputs/publishable/reports/risk_on_transition_recall_exploration_report.md
outputs/manifests/run_manifest.json
outputs/local_cache/candidate_family_event_labels.parquet
outputs/local_cache/candidate_family_capture.parquet
outputs/local_cache/cross_section_feature_panel.parquet
```

patch 输出必须写入独立目录：

```text
outputs/publishable/tables/risk_on_r_series_density_compression/
outputs/publishable/reports/risk_on_r_series_density_compression/
outputs/manifests/risk_on_r_series_density_compression/
outputs/local_cache/risk_on_r_series_density_compression/
```

允许写入的 local cache 只能位于：

```text
outputs/local_cache/risk_on_r_series_density_compression/
```

不得改写任何 source 08 local cache 文件。manifest 必须记录 source local cache 的 input hash，以及 patch local cache 的 output hash。

### 5.1 Input gate

实现必须先执行 input gate，并输出 gate result 到 manifest。

如果以下任一条件发生，必须返回：

```text
risk_on_r_series_input_blocked
```

并且不得生成 supported decision：

1. `outputs/manifests/run_manifest.json` 不存在或 hash 不匹配。
2. 必需 publishable table 缺失。
3. 必需 publishable table 缺少 required source columns。
4. source 08 manifest 未记录对应 artifact 的 hash / row count / schema。
5. 当前 patch requirement hash 未写入 manifest。

如果 local cache 缺失：

1. deterministic arms 仍可运行，但只能使用 publishable event/canonical tables 中已有字段。
2. event-level scoring / supervised ranker arm 必须 fail closed，并写入：

```text
ranker_arm_status = ranker_input_blocked_missing_local_cache
```

3. ranker arm blocked 不得阻止 deterministic arms 完成。

Source table 字段映射必须显式记录。当前 08 publishable tables 中的 `market_regime_bucket` 在本 patch 输出中映射为：

```text
episode_regime_bucket = market_regime_bucket
```

该映射只用于 episode-level recall / bridge denominator 命名，不得替代 event `t0` 的 `event_regime_bucket`。

## 6. Preflight: density-binding proof

full compression run 之前必须先执行 preflight。preflight 不训练 ranker，不重算 events，只从 publishable tables 复核 R 系列是否满足“density binding”定义。

### 6.1 Density-binding 定义

对每个 R-series family，在 `risk_on + before_first_50pct` 上分别检查 train 与 robustness：

```text
recall_gate_pass:
  incremental_recall_over_e1 >= +8 pct

bridge_gate_pass:
  bridge_recall_delta_vs_e1 >= -3 pct

density_binding_flag:
  recall_gate_pass == true
  and bridge_gate_pass == true
  and density_vs_e1_full_denominator > 1.00
```

preflight 必须同时执行两个 scope：

1. family-level diagnostic:

```text
candidate_scope_type == candidate_family
variant_id == all_variants
```

用于证明 R-series 机制整体是 high-recall / high-bridge / high-density。

2. variant-level spot check:

```text
candidate_scope_type == candidate_family_variant
family_input_status == runnable_existing_data
```

用于证明实际可构建 source pool 中，至少有一个 variant 也满足 train 与 robustness 的 `density_binding_flag == true`。

默认 family 分组：

```text
core_density_binding_families = R1,R6,R7,R8,R2
optional_support_families = R3
excluded_negative_control = R5
```

preflight 必须返回：

```text
risk_on_r_series_density_binding_confirmed
```

当且仅当：

1. core family 中至少 4 个在 family-level diagnostic 上 train 与 robustness 都满足 `density_binding_flag == true`。
2. 这些 confirmed core family 中，至少 4 个在 variant-level spot check 上存在一个 runnable variant，在 train 与 robustness 都满足 `density_binding_flag == true`。
3. R5 被识别为 `low_density_low_quality_negative_control`，不得进入 compression source pool。
4. source 08 manifest 与 required tables hash 校验通过。

否则返回：

```text
risk_on_r_series_density_binding_not_confirmed
```

并停止 full compression run。

### 6.2 Preflight 输出

必须输出：

```text
risk_on_r_series_density_binding_preflight.csv
risk_on_r_series_density_binding_summary.json
```

`risk_on_r_series_density_binding_preflight.csv` 至少包含：

1. `candidate_scope_type`
2. `candidate_scope_id`
3. `family_id`
4. `variant_id`
5. `episode_split`
6. `source_regime_column_name`
7. `source_market_regime_bucket`
8. `episode_regime_bucket`
9. `window`
10. `incremental_recall_over_e1`
11. `bridge_recall`
12. `e1_bridge_recall`
13. `bridge_recall_delta_vs_e1`
14. `density_vs_e1_full_denominator`
15. `events_per_instrument_year_p95`
16. `recall_gate_pass`
17. `bridge_gate_pass`
18. `density_binding_flag`
19. `negative_control_flag`
20. `family_level_density_binding_flag`
21. `variant_level_spot_check_flag`
22. `variant_level_confirmed_family_flag`
23. `source_08_manifest_hash`
24. `patch_requirement_hash`

## 7. Compression source pool

默认 source pool 必须来自：

```text
candidate_scope_type == candidate_family_variant
family_id in {
  R1_relative_strength_breakout,
  R6_market_breadth_thrust,
  R7_cross_sectional_momentum_rank_jump,
  R8_persistent_distance_above_ema,
  R2_near_high_volume_expansion
}
family_input_status == runnable_existing_data
```

R3 可以作为 optional arm：

```text
R3_vcp_breakout
```

但 R3 当前 family-level train bridge delta 只有 `+0.4 pct`，低于 §9 的 train bridge gate `+5 pct`。因此 R3 预期会被 train bridge gate 淘汰；它只能作为 optional support / diagnostic family，不得要求进入 final selected compressed pool。

R5 默认不得进入 source pool。若实现输出 R5，必须满足：

```text
source_pool_role = negative_control
decision_contribution = none
```

source pool 事件 inclusion policy：

```text
先读取 source family variants 已生成的全部 event instances；
再按 instrument + event_t0_date canonicalize；
再做 train-only compression / scoring；
最后 link 到全部 06 target episodes，并按 episode_regime_bucket 评估。
```

不得在 compression 后按 target episode membership 过滤 event。

### 7.1 Score specification

所有依赖 score 的 deterministic arms 与 ranker arms 都必须读取同一份 score specification，并输出：

```text
risk_on_r_series_score_spec.csv
```

不得在代码里隐式拼接 strength score。`risk_on_r_series_score_spec.csv` 至少包含：

1. `score_spec_id`
2. `family_id`
3. `variant_id`
4. `score_field_name`
5. `source_column`
6. `source_column_required_flag`
7. `score_direction`
8. `score_transform`
9. `normalization_scope`
10. `missing_policy`
11. `tie_break_policy`
12. `feature_asof_policy`
13. `source_column_presence_status`
14. `score_availability_status`
15. `proxy_score_used`
16. `missing_semantic_feature`
17. `recompute_required_flag`
18. `recomputed_from_source_artifacts`
19. `source_08_manifest_hash`
20. `patch_requirement_hash`

默认 score fields 必须只使用 event `t0` 当天或以前可见字段，并且必须来自当前可读的 `cross_section_feature_panel.parquet` 31 列，除非显式走 patch-local recompute。当前可用 score source columns 冻结为：

```text
return_1d
return_5d
return_20d
return_60d
stock_vs_market_20d
close_to_high_60
rolling_high_60
new_high_60_flag
momentum_percentile_20d
momentum_percentile_60d
momentum_percentile_20d_lag20
universe_up_share
universe_new_high_60_share
universe_up_share_z
universe_up_share_change_5d
board_relative_1d
board_relative_cusum_20d
board_return_20d
stock_vs_board_20d
```

不得从 `candidate_family_event_labels.parquet` 的 `mfe` / `mae` / `forward_return` / bridge outcome 字段补 score；这些是 future label / outcome，只能用于 read-only label 或 evaluation。

默认 score fields 如下：

| family | default score fields |
|---|---|
| R1 | `stock_vs_market_20d`, `stock_vs_board_20d`, `return_60d` |
| R2 | non-scored by default; `amount_ratio_20d` / volume fields unavailable in current cache |
| R6 | `universe_up_share_z`, `universe_up_share_change_5d` |
| R7 | `momentum_percentile_20d`, `momentum_percentile_20d - momentum_percentile_20d_lag20` |
| R8 | proxy score: `return_60d`, `momentum_percentile_60d`, `close_to_high_60` |
| R3 optional | proxy score: `close_to_high_60` only |

R2 的定义性特征是 near-high volume expansion，但当前 feature panel 没有 `amount_*`、`volume_*` 或 turnover source column。因此：

1. R2 默认 `score_availability_status = core_semantic_score_unavailable`。
2. R2 可以进入 `raw_r_series_variant_pool`、`event_regime_gated_only`、`consensus_family_count`、`cooldown_after_selected_event` 等 non-scored arms。
3. R2 不得作为 scored contributor 进入 `family_score_quantile_cut`、`top_k_per_instrument_month`、`market_day_top_percentile` 等 score-dependent arms，除非 patch-local recompute 补齐 volume / amount score。
4. 如果 score-dependent arm 的 source pool 中存在 R2-only canonical event，必须按本节 unscored canonical event policy 处理，不得 silent drop。
5. 如果实现选择 patch-local recompute，必须满足：

```text
recomputed_from_source_artifacts = true
recomputed_feature_family = R2
recomputed_feature_columns include amount_ratio_20d or equivalent volume expansion score
```

并在 manifest 中记录 source OHLCV / amount input paths、hashes、row counts、schema、PIT policy 和 recompute code revision。

R8 的原始语义是 persistent distance above EMA，但当前 feature panel 没有 `close_to_ema20`、`close_to_ema60`、`ema60_positive_run`。因此 R8 score 必须标记：

```text
proxy_score_used = true
missing_semantic_feature = ema_distance
proxy_score_fields = return_60d,momentum_percentile_60d,close_to_high_60
```

R3 缺少 `range_width_ratio_20d_60d` 与 volume score，且当前 family-level evidence 显示 train bridge delta 只有 `+0.4 pct`，低于 §9 的 train bridge gate。R3 必须默认视为 optional support / likely-filtered family，不得影响 supported decision。

默认 score transform：

```text
per_family_train_risk_on_percentile_rank
```

即每个 family / variant 在 train risk_on source events 内单独做 percentile rank，然后用于 threshold / top-k。不得把 R1 与 R6 的 raw feature value 直接横向比较。

canonical event 多 family 触发时，默认 aggregation policy 为：

```text
canonical_score = max(per_family_variant_score)
primary_score_family = family with max score
tie_break = higher train_risk_on_bridge_delta_vs_e1, then lower density_vs_e1, then lexical family_id
```

如果某 arm 需要跨 family 排名，必须使用 `canonical_score`，并保留 `triggered_family_ids`、`per_family_variant_scores`、`primary_score_family` 作为 audit 字段。

R2-only 或其他全由 non-scored family 触发的 canonical event 必须显式处理：

```text
unscored_canonical_event_flag = true
canonical_score = null
score_rank_eligible_flag = false
unscored_canonical_policy = retain_and_audit
```

默认 policy 为 `retain_and_audit`：

1. unscored canonical event 不参与 top-percentile、top-k 或 quantile threshold 排序。
2. unscored canonical event 默认保留在 compressed pool 中，计入 event count、density、p95、recall、bridge 和 overlap evaluation。
3. `compression_reason` 必须写为 `unscored_canonical_retained`。
4. report 必须单列 unscored canonical event 的 count、density share、recall contribution 与 source family composition。
5. 如果实现选择 drop unscored canonical events，必须显式配置：

```text
unscored_canonical_policy = drop_and_audit
compression_reason = unscored_canonical_dropped
```

且该 arm 只能给出 diagnostic conclusion，不得直接产生 supported decision。

禁止在 score-dependent arm 中静默丢弃 R2-only 或其他 unscored canonical events。

如果 required score source column 缺失：

1. 依赖该 score 的 arm 必须 fail closed。
2. 不得用其他字段静默替代。
3. frontier 必须写入 `failure_reason = score_source_column_missing`。

## 8. Compression arms

实现至少要评估以下 compression arms。所有 threshold / ranker 参数只能从 train risk_on 选择。

### 8.1 Baseline arms

1. `raw_r_series_variant_pool`
   - 不压缩，只作为 high-density upper bound。
2. `event_regime_gated_only`
   - 只使用已有 event-regime-gated variants。
3. `single_family_best_variant`
   - 分别评估 R1/R6/R7/R8/R2 的最佳 variant。

### 8.2 Deterministic compression arms

deterministic compression arms 默认必须叠加在已有 `event_regime_gated` variants 之上：

```text
compression_source_variant_policy = event_regime_gated_first
```

具体规则：

1. `family_score_quantile_cut`、`consensus_family_count`、`top_k_per_instrument_month`、`cooldown_after_selected_event`、`market_day_top_percentile`、`overlap_deconcentration` 默认 source 是 R1/R6/R7/R8/R2 的 `event_regime_gated` variants。
2. `ungated` variants 只用于 `raw_r_series_variant_pool` high-density upper bound 和 optional sensitivity，不得作为 headline train-selected compression source，除非 config 显式设置 `allow_ungated_compression_source = true`。
3. 若启用 ungated compression source，manifest 与 report 必须说明该结果是 sensitivity，并单独报告与 gated-start 的 density / recall / bridge 差异。
4. 如果某 family 没有 event-regime-gated variant，才能 fallback 到 ungated variant；fallback 必须写入 `source_variant_fallback_reason`。

1. `family_score_quantile_cut`
   - 每个 family 用可观测 strength score 做 train quantile threshold。
   - 默认 quantiles：`0.70,0.80,0.90,0.95,0.975`。
2. `consensus_family_count`
   - 同一 canonical event 触发 R-series family 数量至少为 `2` 或 `3`。
3. `top_k_per_instrument_month`
   - 每个 instrument 每 21 个交易日最多保留 top `1/2/3` 个事件。
4. `cooldown_after_selected_event`
   - 同一 instrument 选中事件后 `10/20/40` 个交易日内不再保留同源事件。
5. `market_day_top_percentile`
   - 每个 trade date 只保留 score 最高的 top `5/10/20%` R-series events。
6. `overlap_deconcentration`
   - 限制同一 canonical event 的同日重复 family tags，只保留最高 rank source family，并保留 triggered family list 作为 feature。

`consensus_family_count` 与 `overlap_deconcentration` 的 philosophy 相反：

1. `consensus_family_count` 奖励多 family 同日共振。
2. `overlap_deconcentration` 去除同日多 family 重复 tag 的密度集中。

二者默认必须作为独立 arms 评估，不得组合。如果实现要组合，必须声明新的 `compression_arm_id`，并在 report 中解释组合逻辑。

`density_compression_ratio_vs_raw_r_pool` 的 raw denominator 必须固定为：

```text
raw_r_series_variant_pool =
  canonical union of runnable candidate_family_variant events
  from R1,R6,R7,R8,R2
  before any compression
```

不得使用 `candidate_family__all_variants` family diagnostic scope 作为 compression ratio denominator。all-variants 只用于 preflight diagnostic。

### 8.3 Supervised ranker arm

可选实现 supervised ranker，但必须满足：

1. label 只能来自 train split 中 event-level bridge-positive / forward label。
2. features 只能使用 event `t0` 当天或以前可见字段。
3. validation / robustness 不得用于 model selection。
4. 必须输出 feature list、missing policy、training denominator、positive rate、calibration readout。
5. 若 event-level label denominator 不足 `500` 或 positive count 不足 `50`，ranker arm 必须降级为 diagnostic-only。
6. ranker label horizon、cutoff、purge policy 必须写入 manifest。

允许模型：

```text
logistic_l1
logistic_l2
monotonic_tree_if_available
```

不得使用 deep learning 或外部非本实验数据。

ranker label boundary 必须满足：

1. 默认 ranker label target 为 source 08 event-level：

```text
ranker_label_target = bridge_positive_event_before_first_50pct
```

它对应 target episode window 的 bridge-positive recall，不等同于 event-anchored `+120d` precision。

2. `event_big_winner_120d_rate` 或等价 forward label 默认只能作为 auxiliary readout，不得与 bridge-positive label 混成一个 target。
3. 若实现单独训练 `event_big_winner_120d` diagnostic ranker arm，必须冻结：

```text
forward_label_horizon_trading_days = 120
```

且该 arm 默认只能给出 diagnostic conclusion，不能直接产生 `risk_on_r_series_density_compressed_candidate_supported_for_meta_label`。

4. train ranker 样本必须满足：

```text
event_split == train
event_label_observation_end_date <= train_label_cutoff_date
```

5. 对 `bridge_positive_event_before_first_50pct` target，`event_label_observation_end_date` 必须来自 source bridge label / capture table 的 observation end 字段；若 source 未提供可审计 end date，ranker arm 必须 blocked，不得自行套用 120d horizon。
6. 对 `event_big_winner_120d` diagnostic target，`event_label_observation_end_date` 默认按 `event_t0_date + forward_label_horizon_trading_days` 计算；若 source label table 已给出 observation end date，必须优先使用 source 字段并记录字段名。
7. label horizon 跨过 `train_label_cutoff_date` 的 train events 必须从 ranker training 中排除，不得用 partial horizon、未来填充或 validation/robustness 期间的价格补齐。
8. validation / robustness label 只用于 read-only evaluation，不得参与 threshold、model、feature、calibration 或 early stopping 选择。
9. 若无法证明 label cutoff，ranker arm 必须返回：

```text
ranker_arm_status = ranker_input_blocked_label_cutoff_unverifiable
```

deterministic arms 不得因为 ranker label cutoff 不可用而停止。

## 9. Selection objective

compression frontier 的 train-only objective 必须按以下优先级排序：

1. pass label / execution completeness:
   - `label_completeness_rate >= 0.70`
   - `next_open_executable_rate >= 0.95`
2. pass train bridge:
   - `train_risk_on_bridge_recall_delta_vs_e1 >= +5 pct`
3. pass train recall:
   - `train_risk_on_incremental_recall_over_e1 >= +8 pct`
4. density compression:
   - primary target: `density_vs_e1_full_denominator <= 1.00`
   - stretch target: `density_vs_e1_full_denominator <= 0.50`
5. avoid event concentration:
   - `events_per_instrument_year_p95 <= 4`
   - `single_family_density_share <= 65%`
6. prefer robustness-stable arms only after train selection is frozen.

`single_family_density_share <= 65%` 是本 patch 的 meta-label feature-source concentration guard，不是 09 entry-union gate。原 08 / downstream entry union 的 35% family-share gate 仍必须作为 read-only diagnostic 输出：

```text
downstream_entry_family_share_35pct_pass
```

如果 compressed pool 的 single-family share 在 `35%` 到 `65%` 之间，本 patch 可以给出 feature-source support，但报告必须明确：

```text
not_supported_as_direct_entry_union_due_to_35pct_family_share_gate
```

Selection score 必须显式写入 config / manifest。例如：

```text
selection_score =
  + 4.0 * train_bridge_recall_delta_vs_e1
  + 3.0 * train_incremental_recall_over_e1
  - 2.0 * max(density_vs_e1_full_denominator - 1.0, 0)
  - 1.0 * max(events_per_instrument_year_p95 - 4, 0)
```

如果实现改动 score weights，必须在 report 中说明。

### 9.1 Train-only selection freeze

compression selection 必须分两阶段：

1. `train_selection_stage`
   - 只使用 train risk_on metrics。
   - 按 §9 objective 与 selection score 选出唯一 `selected_compression_arm_id`。
   - 写入 `selected_by_train_only_flag = true`。
2. `read_only_evaluation_stage`
   - 在 train selection 已冻结后 join validation / robustness metrics。
   - validation / robustness 只能决定最终 decision 是 supported 还是 blocked。
   - validation / robustness 不得改变 selected arm、threshold、feature list、score weights 或 source family set。

如果多个 arm 在 train stage 分数完全相同，tie break 必须按以下顺序：

1. lower `density_vs_e1_full_denominator`
2. higher `train_risk_on_bridge_recall_delta_vs_e1`
3. higher `train_risk_on_incremental_recall_over_e1`
4. lower `events_per_instrument_year_p95`
5. lexical `compression_arm_id`

如果 train-selected arm 在 robustness 上失败，不得换成另一个 robustness 表现更好的 arm；必须输出对应 blocked decision，例如：

```text
risk_on_r_series_bridge_degraded_blocked
risk_on_r_series_overfit_blocked
```

frontier 可以报告其他 arms 的 read-only robustness metrics，但必须标记：

```text
post_train_selection_read_only_metric = true
```

## 10. Gate contract

必须输出 patch-level decision：

```text
risk_on_r_series_density_compression_decision
```

取值：

```text
risk_on_r_series_input_blocked
risk_on_r_series_density_binding_not_confirmed
risk_on_r_series_no_compression_candidate
risk_on_r_series_density_still_blocked
risk_on_r_series_bridge_degraded_blocked
risk_on_r_series_overfit_blocked
risk_on_r_series_diagnostic_only
risk_on_r_series_density_compressed_candidate_supported_for_meta_label
```

### 10.1 Support gate

要进入 `risk_on_r_series_density_compressed_candidate_supported_for_meta_label`，selected compressed candidate pool 必须满足：

1. train risk_on incremental recall over E1 >= `+8 pct`
2. robustness risk_on incremental recall over E1 >= `+8 pct`
3. train risk_on bridge recall delta vs E1 >= `+5 pct`
4. robustness risk_on bridge recall delta vs E1 >= `+5 pct`
5. density vs E1 full denominator <= `1.00`
6. events per instrument-year p95 <= `4`
7. label completeness >= `70%`
8. next-open executable rate >= `95%`
9. validation risk_on denominator `< 30` 时只作为 diagnostic，不得因 validation risk_on pass/fail 改变 threshold。
10. `single_family_density_share <= 65%` for meta-label feature-source support。

### 10.2 Diagnostic-only states

若某 arm 满足 recall / bridge，但 density 仍 > `1.00`，decision 必须为：

```text
risk_on_r_series_density_still_blocked
```

若 density 达标但 robustness bridge delta < `+5 pct`，decision 必须为：

```text
risk_on_r_series_bridge_degraded_blocked
```

若 train pass 但 robustness recall 或 bridge 显著坍塌，必须标记：

```text
risk_on_r_series_overfit_blocked
```

## 11. Required outputs

必须输出 publishable tables：

1. `risk_on_r_series_density_binding_preflight.csv`
2. `risk_on_r_series_score_spec.csv`
3. `risk_on_r_series_source_pool_summary.csv`
4. `risk_on_r_series_compression_frontier.csv`
5. `risk_on_r_series_selected_compressed_variants.csv`
6. `risk_on_r_series_compressed_canonical_events.csv`
7. `risk_on_r_series_recall_bridge_density_by_split.csv`
8. `risk_on_r_series_threshold_sensitivity.csv`
9. `risk_on_r_series_label_quality_readout.csv`
10. `risk_on_r_series_overlap_diagnostic.csv`
11. `risk_on_r_series_gate_summary.csv`

如果 event-level score table 过大，应输出到 local cache，并在 manifest 记录 hash：

```text
outputs/local_cache/risk_on_r_series_density_compression/risk_on_r_series_event_scores.parquet
```

`risk_on_r_series_event_scores.parquet` 必须包含全部 source pool event scores；publishable `risk_on_r_series_compressed_canonical_events.csv` 至少包含 selected compressed pool 的 retained canonical events。两者都必须在 manifest 记录 hash / row count / schema。

必须输出独立中文报告：

```text
outputs/publishable/reports/risk_on_r_series_density_compression/risk_on_r_series_density_compression_report.md
```

必须输出独立 manifest：

```text
outputs/manifests/risk_on_r_series_density_compression/risk_on_r_series_density_compression_manifest.json
```

manifest 必须记录：

1. source 08 manifest path / hash
2. source publishable table paths / hashes / row counts / schemas
3. source local cache paths / hashes / row counts / schemas，若读取
4. patch requirement path / hash
5. score spec path / hash
6. selected `compression_arm_id`
7. train-only selection config / hash
8. ranker label horizon / cutoff / purge policy，若 ranker arm 被评估
9. patch output paths / hashes / row counts / schemas
10. patch local cache paths / hashes / row counts / schemas，若生成
11. input gate result
12. final decision

### 11.1 Core schemas

`risk_on_r_series_score_spec.csv` 至少包含：

1. `score_spec_id`
2. `family_id`
3. `variant_id`
4. `score_field_name`
5. `source_column`
6. `source_column_required_flag`
7. `score_direction`
8. `score_transform`
9. `normalization_scope`
10. `missing_policy`
11. `tie_break_policy`
12. `feature_asof_policy`
13. `source_column_presence_status`
14. `score_availability_status`
15. `proxy_score_used`
16. `missing_semantic_feature`
17. `recompute_required_flag`
18. `recomputed_from_source_artifacts`
19. `source_08_manifest_hash`
20. `patch_requirement_hash`

`risk_on_r_series_compression_frontier.csv` 至少包含：

1. `compression_arm_id`
2. `source_family_set`
3. `source_variant_set`
4. `threshold_policy`
5. `score_spec_id`
6. `score_spec_hash`
7. `selected_by_train_only_flag`
8. `post_train_selection_read_only_metric`
9. `compression_source_variant_policy`
10. `allow_ungated_compression_source`
11. `source_variant_fallback_reason`
12. `unscored_canonical_policy`
13. `unscored_canonical_event_count`
14. `unscored_canonical_density_share`
15. `event_count`
16. `canonical_event_count`
17. `density_vs_e1_full_denominator`
18. `density_compression_ratio_vs_raw_r_pool`
19. `raw_r_pool_definition`
20. `events_per_instrument_year_p95`
21. `train_risk_on_incremental_recall_over_e1`
22. `train_risk_on_bridge_recall_delta_vs_e1`
23. `validation_risk_on_incremental_recall_over_e1`
24. `validation_risk_on_sample_small_flag`
25. `robustness_risk_on_incremental_recall_over_e1`
26. `robustness_risk_on_bridge_recall_delta_vs_e1`
27. `label_completeness_rate`
28. `next_open_executable_rate`
29. `single_family_density_share_max`
30. `downstream_entry_family_share_35pct_pass`
31. `direct_entry_union_support_status`
32. `ranker_arm_status`
33. `gate_status`
34. `failure_reason`
35. `source_08_manifest_hash`
36. `patch_requirement_hash`

`risk_on_r_series_selected_compressed_variants.csv` 至少包含：

1. `compressed_pool_id`
2. `compression_arm_id`
3. `family_id`
4. `variant_id`
5. `source_pool_role`
6. `source_event_count_before_compression`
7. `source_event_count_after_compression`
8. `family_density_share_after_compression`
9. `train_selection_rank`
10. `selection_reason`
11. `negative_control_flag`

`risk_on_r_series_compressed_canonical_events.csv` 至少包含：

1. `compressed_pool_id`
2. `compression_arm_id`
3. `canonical_event_id`
4. `instrument`
5. `event_t0_date`
6. `event_executable_date`
7. `event_split`
8. `event_regime_bucket`
9. `episode_regime_bucket`
10. `primary_family_id`
11. `primary_variant_id`
12. `triggered_family_ids`
13. `triggered_family_variants`
14. `per_family_variant_scores`
15. `canonical_score`
16. `primary_score_family`
17. `score_spec_id`
18. `score_rank_eligible_flag`
19. `unscored_canonical_event_flag`
20. `unscored_canonical_policy`
21. `compression_keep_flag`
22. `compression_reason`
23. `raw_source_event_ids`
24. `source_08_manifest_hash`
25. `patch_requirement_hash`

`risk_on_r_series_gate_summary.csv` 至少包含：

1. `risk_on_r_series_density_compression_decision`
2. `density_binding_preflight_decision`
3. `selected_compression_arm_id`
4. `recall_gate_pass`
5. `bridge_gate_pass`
6. `density_gate_pass`
7. `p95_density_gate_pass`
8. `label_execution_gate_pass`
9. `overfit_gate_pass`
10. `gate_failures`
11. `train_risk_on_incremental_recall_over_e1`
12. `robustness_risk_on_incremental_recall_over_e1`
13. `train_risk_on_bridge_recall_delta_vs_e1`
14. `robustness_risk_on_bridge_recall_delta_vs_e1`
15. `density_vs_e1_full_denominator`
16. `events_per_instrument_year_p95`
17. `single_family_density_share_max`
18. `downstream_entry_family_share_35pct_pass`
19. `validation_risk_on_sample_small_flag`

## 12. Report requirements

报告必须用中文撰写，并至少包含：

1. 当前 R 系列 risk_on 复核结论：R1/R6/R7/R8/R2 是 density-binding，不是 bridge-binding。
2. 明确指出 R5 是 low-density low-quality negative control。
3. 解释为什么 `train_selection_max_density_vs_e1 = 0.50` 对 risk_on R 系列有害。
4. 区分 family all-variants 诊断与 variant/event-level implementation。
5. 当前 `cross_section_feature_panel.parquet` 的 31 列可用字段，以及原 score spec 中哪些字段不可得。
6. score spec：每个 R family 使用哪些 t0 可见字段、方向、normalization、missing policy、proxy flag 与 recompute flag。
7. R2 为什么默认是 non-scored core family；若执行 patch-local recompute，必须说明 recompute source。
8. R2-only unscored canonical events 的数量、density share、retention/drop policy、recall contribution 与 bridge contribution。
9. R8 为什么使用 `return_60d` / `momentum_percentile_60d` / `close_to_high_60` 作为 EMA-distance proxy。
10. compression arms 默认从 event-regime-gated variants 起步；ungated 只作为 upper bound / sensitivity。
11. compression arms 的 train-only selection 方法，以及 `selected_compression_arm_id` 如何在 train stage 冻结。
12. selected compressed pool 的 retained canonical events 是否可从 `risk_on_r_series_compressed_canonical_events.csv` 复算。
13. selected compressed pool 的 recall / bridge / density / p95 / label quality。
14. validation risk_on sample-small caveat。
15. robustness risk_on 是否仍维持 recall 与 bridge；若失败，不得换用另一个 robustness 更好的 arm。
16. 如果失败，说明是 density 仍未压够、bridge 被压坏、ranker input blocked、score field missing，还是 train-only 过拟合，并明确这些 blocked states 是可接受实验结论。
17. `single_family_density_share <= 65%` 与 downstream 35% direct-entry family-share gate 的差异。
18. 与 `requirement_patch_regime_specific_unions.md` 的关系：本 patch 是 risk_on P0 主线，regime-specific union 是消融诊断。
19. 明确说明本 patch 不是交易信号、不是模型、不是回测。

## 13. Tests

必须新增或复用测试覆盖：

1. preflight 能从 publishable tables 复现 R-series density-binding 判定。
2. R5 默认被排除，并标记 `negative_control_flag == true`。
3. input gate 在 source 08 manifest hash 不匹配、source table 缺失、schema 缺失时返回 `risk_on_r_series_input_blocked`。
4. source `market_regime_bucket` 到 output `episode_regime_bucket` 的映射被记录，且不覆盖 event `event_regime_bucket`。
5. `risk_on_r_series_score_spec.csv` 存在，并且每个 score-dependent arm 都引用 `score_spec_id` / `score_spec_hash`。
6. score spec 只能引用当前 feature panel 可用字段，除非 `recomputed_from_source_artifacts = true`。
7. R2 在无 amount / volume recompute 时，score-dependent arms 必须跳过或 fail closed，不得用 `close_to_high_60` 冒充 volume expansion score。
8. R2-only canonical events 在 score-dependent arms 中必须标记 `unscored_canonical_event_flag`，并按 `unscored_canonical_policy` 显式保留或丢弃，不得 silent drop。
9. 默认 `unscored_canonical_policy = retain_and_audit` 时，unscored canonical events 计入 density / recall / bridge / overlap evaluation。
10. deterministic compression arms 默认 `compression_source_variant_policy = event_regime_gated_first`。
11. ungated compression source 只能作为 upper bound / sensitivity，除非 config 显式开启并在 report 中说明。
12. R8 proxy score 必须标记 `proxy_score_used = true` 与 `missing_semantic_feature = ema_distance`。
13. score source column 缺失时，对应 arm fail closed，不得静默替代字段。
14. preflight 同时输出 family-level diagnostic 与 variant-level spot check。
15. compression threshold 只由 train risk_on evidence 选择。
16. train stage 必须冻结唯一 `selected_compression_arm_id`；robustness 失败时不得改选其他 arm。
17. validation / robustness 字段在 frontier 中标记为 read-only evaluation。
18. `candidate_family__all_variants` 不得作为 selected compressed pool 的直接 entry unit。
19. `risk_on_r_series_compressed_canonical_events.csv` 存在，并能复算 selected pool 的 event count / density / recall linkage。
20. event inclusion 不按 target episode membership 过滤。
21. density gate 使用 full evaluated denominator。
22. bridge delta 使用 same split / same risk_on / same window E1 baseline。
23. robustness bridge gate 使用 `>= +5 pct`，不得使用更严的 `+10 pct` 除非 config 显式覆盖并报告原因。
24. validation risk_on denominator `< 30` 时只 diagnostic。
25. 缺失 local cache 且 ranker arm 被请求时，ranker arm fail closed；deterministic arms 可继续。
26. supervised ranker 不读取 validation / robustness label 做 model selection。
27. ranker train labels 的 `event_label_observation_end_date <= train_label_cutoff_date`；无法证明 cutoff 时 ranker arm blocked。
28. `event_big_winner_120d` ranker arm 只能 diagnostic，不得与 bridge-positive target 混用。
29. patch 只写入 `outputs/local_cache/risk_on_r_series_density_compression/`，不得改写 source local cache。
30. original 08 report / manifest / publishable tables 不被覆盖。
31. independent report / manifest path 存在且 hash 可审计。

## 14. 推荐执行方式

推荐实现为独立入口：

```text
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python experiments/pending/08_risk_on_transition_recall_exploration_v0/src/run_risk_on_r_series_density_compression_patch.py --source-manifest experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/manifests/run_manifest.json
```

默认 08 full run 行为不得改变。

## 15. 验收标准

验收必须满足：

1. 原 08 report / manifest hash 不变。
2. preflight 表明确证明 R 系列 risk_on 的 binding constraint 是否为 density。
3. R5 被识别为 negative control，不得贡献 supported decision。
4. compression frontier 至少包含 baseline arms 与 deterministic compression arms。
5. `risk_on_r_series_score_spec.csv` 能证明每个 score-dependent arm 的 score 字段、方向、normalization、missing policy、proxy flag、recompute flag。
6. R2 在无 patch-local amount / volume recompute 时不进入 score-dependent arms。
7. R2-only unscored canonical events 不 silent drop；必须在 compressed canonical events 表中标记并计入 audit。
8. deterministic compression 默认从 `event_regime_gated` variants 起步；ungated 只作为 upper bound / sensitivity。
9. R8 proxy score 被显式标记，不冒充 EMA-distance 原始字段。
10. preflight 能证明 family-level all-variants 与 variant-level source pool 都通过 density-binding check。
11. `risk_on_r_series_compressed_canonical_events.csv` 能审计 selected compressed pool 的 retained events。
12. `selected_compression_arm_id` 由 train-only selection 冻结；validation / robustness 只用于 support / block。
13. 若 selected compressed pool 支持进入下一阶段，必须同时通过 robustness recall、robustness bridge、density、p95、label execution gates。
14. 若失败，decision 必须指出失败 gate，而不是复用原 selected joint union 的 bridge-blocked 结论。
15. 报告必须说明 density still blocked / bridge degraded / overfit blocked 都是可接受实验结论。
16. patch local cache 只写入 `outputs/local_cache/risk_on_r_series_density_compression/`，source local cache hash 不变。
17. 报告明确说明：对 risk_on R 系列，下一阶段重点不是换 regime selection，而是在高 bridge 候选池上做 density compression / ranker。
