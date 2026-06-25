# 14A Full-Native Sparse State-Change Event Utility Preflight Report

## 结论

本次 14A full-native sparse state-change event utility preflight 的最终裁决是：

```text
decision_state = 14A_diagnostic_cohort_signal_only_no_utility
next_allowed_requirement = none
active_winner_entry_search_authorized = false
confirmatory_status = false
primary_failure_reason = cohort_signal_no_same_event_utility
gate_failure = same_event_utility_50bps_failed
```

解释：14A 找到了可构造的 sparse state-change events，也找到了若干 raw opportunity surface；但是在严格 PIT cohort rank 之后，候选 operating arm 不能把机会稳定转成 50bps after-cost、same-event full-denominator utility。最好的 operating arm 是：

```text
raw_event_arm_id = F4_board_relative_strength_rank_jump__ret60_jump3
cohort_arm_id = C3
rank_cutoff_id = top20pct
```

这个 arm 在 train 上有轻微正的 same-event utility，在 validation 上仍为负，在 robustness 上虽然 same-event utility 为正，但 cohort selection 反而弱于 raw-all-events。按 14A contract，这不足以打开 14B confirmatory sparse-event requirement。

## 数据与 lineage 复核

14A 使用 13A native cache 作为主 row-level source，并保留了 12A7g selected label lineage。输入、adapter、label rebuild 都通过：

| 项目 | 结果 |
|---|---:|
| PIT executable daily rows | 1,140,000 |
| PIT membership daily rows | 1,140,500 |
| qfq 本地文件数 | 4,598 |
| benchmark index rows | 6,843 |
| 13A native rebuild panel rows | 431,239 |
| 14A feature panel rows | 408,715 |
| sparse event panel rows | 66,881 |
| cohort-normalized event panel rows | 25,776 |

Split 覆盖：

| panel | train | validation | robustness |
|---|---:|---:|---:|
| native rebuild | 232,640 | 63,527 | 135,072 |
| feature panel | 216,794 | 61,307 | 130,614 |

Entry-anchor label rebuild audit 使用 deterministic hash sample 抽样 500 行，并用 raw qfq bars 重算 13A next-open entry anchored label。关键字段全部一致：

| field | compared_row_n | mismatch_n | status |
|---|---:|---:|---|
| upper_first | 500 | 0 | pass |
| lower_first | 500 | 0 | pass |
| same_bar_conflict | 500 | 0 | pass |
| winner_positive | 500 | 0 | pass |
| upper_barrier | 500 | 0 | pass |
| lower_barrier | 500 | 0 | pass |
| horizon_close_return | 500 | 0 | pass |
| overall | 8,000 | 0 | pass |

这点很重要：本次失败不是因为 label cache 漂移、entry anchor 不一致或 adapter 把 13A 字段映射错了。失败发生在 event utility transport 层。

## Gate Summary

| gate | status | 含义 |
|---|---|---|
| input_gate_status | pass | 必需输入存在且 schema 可读 |
| upstream_lineage_gate_status | pass | 12A7g / 13A lineage 与 label rebuild 通过 |
| native_universe_gate_status | pass | native universe 可用 |
| native_label_portability_gate_status | pass | selected label 可在 native universe 上评估 |
| sparse_event_construction_gate_status | pass | frozen 16 个参数臂可构造 sparse events |
| density_duplicate_gate_status | pass | 至少存在一个全 split density / duplicate 合格 arm |
| raw_opportunity_surface_gate_status | pass | train raw opportunity surface 存在 |
| cohort_availability_gate_status | pass | PIT cohort rank arms 可计算 |
| cohort_transport_gate_status | fail | cohort selection 没有在 train/validation/robustness 都优于 raw-all-events |
| badside_veto_gate_status | pass | selected operating arm 没有增加 bad-side exposure |
| same_event_utility_50bps_gate_status | fail | validation same-event utility 为负 |
| morphology_rediscovery_gate_status | fail | train / validation 与 13A 已知 morphology 高重叠 |
| validation_stress_gate_status | fail | validation stress split 没有正 after-cost utility |
| search_accounting_gate_status | pass | 6 families / 16 parameter grid / 3 operating arms 的 train-only search 约束成立 |

## Sparse Event Construction

14A 生成完整 frozen grid：6 个 family，16 个 parameter arms。重跑后 sparse event construction 数字如下：

| family | parameter_n | raw_transition_n | accepted_event_n | duplicate_suppressed_n | suppressed_rate |
|---|---:|---:|---:|---:|---:|
| F1 residual_cusum_break | 4 | 29,863 | 16,358 | 13,505 | 45.2% |
| F2 compression_to_directional_expansion | 2 | 13,264 | 4,806 | 8,458 | 63.8% |
| F3 controlled_damage_first_reclaim | 2 | 69,157 | 9,886 | 59,271 | 85.7% |
| F4 board_relative_strength_rank_jump | 4 | 34,215 | 14,458 | 19,757 | 57.7% |
| F5 participation_ignition_with_price_control | 2 | 61,459 | 16,645 | 44,814 | 72.9% |
| F6 low_volatility_range_expansion_first_trigger | 2 | 12,864 | 4,728 | 8,136 | 63.2% |

Density / duplicate gate 是第一个强过滤器。48 个 split-arm density rows 中，45 个因为 duplicate fraction 失败，只有 3 个 pass；按 “raw arm 必须所有 split pass” 的 contract，唯一能进入 cohort normalization 的 raw arm 是：

```text
F4_board_relative_strength_rank_jump__ret60_jump3
max_event_density_per_instrument_year = 0.423755
duplicate_episode_fraction = 0.229002
```

Insight：很多 event family 看起来有 raw opportunity，但触发太密集、episode 重复太高，不能作为 14A 的 primary cohort transport 对象。这个结果把 14A 的问题从 “有没有信号” 缩小为 “唯一密度合格的 F4 rank-jump 信号能否被 cohort rank 转成 utility”。

## Raw Opportunity Surface

Train split 上 raw readout 的前几名如下。`utility_per_event_mean_50bps` 是扣除 50bps cost buffer 后的 path utility return；换算成 bp 可乘以 10,000。

| raw_event_arm_id | train_event_n | winner_lift | fast_fail_uplift | utility_50bps | raw_status | badside |
|---|---:|---:|---:|---:|---|---|
| F5 participation window60 ratio2p0 | 3,471 | +0.0602 | -0.0107 | +0.00697 | pass | pass |
| F6 low-vol range ratio1p5 | 1,394 | +0.1210 | +0.0758 | +0.00468 | pass | fail |
| F2 compression expansion ratio1p5 | 1,414 | +0.1186 | +0.0783 | +0.00411 | pass | fail |
| F6 low-vol range ratio2p0 | 902 | +0.1275 | +0.0667 | +0.00395 | pass | fail |
| F2 compression expansion ratio2p0 | 918 | +0.1250 | +0.0715 | +0.00346 | pass | fail |
| F4 board rank ret60 jump3 | 1,061 | +0.0179 | -0.0656 | +0.00298 | pass | pass |
| F4 board rank ret60 jump2 | 1,903 | +0.0125 | -0.0414 | +0.00209 | pass | pass |
| F4 board rank ret20 jump3 | 2,149 | -0.0051 | -0.0133 | -0.00497 | pass | pass |

F5/F6/F2 的 raw utility 更强，但它们没有通过 full split density / duplicate 或 bad-side 约束。唯一可进入 cohort transport 的 F4 ret60 jump3 原始机会较弱，但更稀疏、更干净：

| split | event_n | winner_rate | winner_lift | fast_fail_uplift | utility_0bps | utility_50bps |
|---|---:|---:|---:|---:|---:|---:|
| train | 1,061 | 0.1631 | +0.0179 | -0.0656 | +0.00798 | +0.00298 |
| validation | 553 | 0.0705 | -0.0254 | -0.1280 | -0.01658 | -0.02158 |
| robustness | 534 | 0.2285 | +0.0921 | -0.1067 | +0.02931 | +0.02431 |

Insight：raw surface 的问题不是完全没有机会，而是机会非常 regime-dependent。F4 ret60 jump3 在 robustness 表现强，在 validation 明显失效。这与 validation stress gate 的失败一致。

## PIT Cohort Transport

Train-only selection 后，operating arms 限制在最多 3 个。被选中的 3 个 operating arms 全部来自同一 raw arm `F4_board_relative_strength_rank_jump__ret60_jump3`：

| cohort | cutoff | split | selected_n | same_event_utility_50bps | same_event_delta_50bps | winner_lift | fast_fail_uplift |
|---|---|---|---:|---:|---:|---:|---:|
| C3 | top20pct | train | 198 | +0.00356 | +0.00058 | +0.0137 | -0.0214 |
| C3 | top20pct | validation | 152 | -0.00372 | +0.01785 | -0.0311 | -0.0476 |
| C3 | top20pct | robustness | 111 | +0.00902 | -0.01530 | +0.1229 | -0.0098 |
| C3 | top10pct | train | 125 | +0.00342 | +0.00044 | +0.0289 | -0.0390 |
| C3 | top10pct | validation | 92 | -0.00198 | +0.01960 | -0.0379 | -0.0430 |
| C3 | top10pct | robustness | 49 | +0.00280 | -0.02151 | +0.0981 | -0.0405 |
| C4 | top20pct | train | 194 | +0.00180 | -0.00118 | +0.0483 | -0.0213 |
| C4 | top20pct | validation | 143 | -0.00411 | +0.01747 | +0.0064 | +0.0155 |
| C4 | top20pct | robustness | 114 | +0.00369 | -0.02063 | -0.0092 | +0.0125 |

Best selected arm `C3 / top20pct` 的 full denominator accounting：

| split | raw_event_n | selected_n | selected_fraction | raw_all_utility_50bps | same_event_utility_50bps | selected_entry_diag_utility_50bps | delta_vs_raw |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 1,061 | 198 | 18.7% | +0.00298 | +0.00356 | +0.01907 | +0.00058 |
| validation | 553 | 152 | 27.5% | -0.02158 | -0.00372 | -0.01355 | +0.01785 |
| robustness | 534 | 111 | 20.8% | +0.02431 | +0.00902 | +0.04337 | -0.01530 |

这里有一个关键 AFML 解释：如果只看 selected-entry diagnostic utility，robustness 是 +0.04337，看起来很强；但 14A 的 primary metric 是 same-event full-denominator utility，skipped events 以 0 计入 denominator。按这个口径，robustness 的 cohort selection 从 raw-all-events 的 +0.02431 降到 +0.00902，说明 cohort rank 在强行情区间反而漏掉了太多有效机会。

Validation 的改善方向是对的：从 raw 的 -0.02158 改到 same-event -0.00372，但仍未转正。因此 `same_event_utility_50bps_gate_status = fail`。

## Morphology Rediscovery

Selected arm 的 morphology gate 也失败。Required overlap sources 的读数如下：

| split | overlap_source | selected_overlap_rate | overlap_utility_50bps | non_overlap_utility_50bps | non_overlap_winner_lift | morphology_score | status |
|---|---|---:|---:|---:|---:|---:|---|
| train | 13A volatility bottom20 | 0.136 | -0.00319 | +0.02258 | +0.1696 | 0.803 | fail |
| train | 13A volatility-range compression | 0.788 | +0.02657 | -0.00879 | +0.1667 | 0.803 | fail |
| train | broad drawdown/reversal proxy | 0.803 | +0.03367 | -0.04045 | +0.0256 | 0.803 | fail |
| validation | 13A volatility bottom20 | 0.138 | -0.01029 | -0.01407 | +0.0382 | 0.750 | fail |
| validation | 13A volatility-range compression | 0.750 | -0.01729 | -0.00234 | +0.0789 | 0.750 | fail |
| validation | broad drawdown/reversal proxy | 0.750 | -0.01367 | -0.01317 | +0.0526 | 0.750 | fail |
| robustness | 13A volatility bottom20 | 0.081 | +0.07745 | +0.04037 | +0.3235 | 0.856 | pass |
| robustness | 13A volatility-range compression | 0.856 | +0.02754 | +0.13738 | +0.6250 | 0.856 | pass |
| robustness | broad drawdown/reversal proxy | 0.829 | +0.03369 | +0.09026 | +0.4737 | 0.856 | pass |

Robustness 虽然 morphology score 高，但 non-overlap utility 也强，所以单独看 robustness 可以通过 morphology independence。但 train 和 validation 中，selected rows 与 13A compression / drawdown-reversal proxy 的重叠过高，且 non-overlap utility 不稳定，触发 `fail_morphology_rediscovery`。

Insight：F4 board-rank jump 不是完全独立的新 winner-entry mechanism。它在关键 split 上很大程度仍在重新发现已有 compression / drawdown-reversal morphology。换句话说，cohort rank 在统计上像是在 “挑选已知形态的子集”，而不是证明一个新的、可迁移的 sparse state-change alpha。

## Findings

1. **14A 找到了 raw opportunity，但没有找到 deployable utility。**
   F5/F6/F2 在 train 上有更高 raw utility 和 winner lift，但 density / duplicate / bad-side 约束阻止它们进入 primary cohort transport。唯一 density 合格的 F4 ret60 jump3 utility 较弱，并且 validation 为负。

2. **Cohort rank 是有用的诊断过滤器，但不是可授权交易入口。**
   C3/top20pct 在 validation 把 utility 从 -0.02158 改善到 -0.00372，说明 rank 能减少一部分坏边；但它没有把 validation 推正，也在 robustness 把 +0.02431 的 raw utility 压低到 +0.00902。

3. **Selected-entry diagnostic 不能替代 same-event denominator。**
   best arm 在 robustness 的 selected-entry utility 是 +0.04337，但 same-event utility 只有 +0.00902，并且低于 raw-all-events。若删除 skipped events 后看起来变好，那只是 denominator shrinkage，不是 14A 要求的 utility transport。

4. **Morphology independence 不足。**
   Train / validation 的 selected rows 与 13A volatility-range compression、broad drawdown/reversal proxy 重叠达到 0.75-0.80。这个读数支持 “重新发现旧 morphology” 的解释，而不是新 event family 的独立发现。

5. **Validation stress split 是核心失败点。**
   F4 ret60 jump3 raw 在 robustness 很强，但 validation raw utility 和 cohort utility 都为负。14A 的目标是 active winner-entry signal；如果 validation 这样的压力区间不能转正，就不能进入 confirmatory 14B。

## Insight

AFML 视角下，这次结果应被读作 “signal shape exists, but actionability fails”。也就是：

- state-change event 可以构造；
- event 与 winner opportunity 有局部相关；
- rank normalization 能改善部分坏样本；
- 但 full-denominator、after-cost、cross-split utility 没有成立；
- morphology gate 显示它没有摆脱 13A 已失败的 compression / reversal 影子。

因此 14A 不应继续主动 winner-entry event mining。更合理的后续方向有两类：

1. **降级为 participation / defense overlay。**
   F4 ret60 jump3 和 C3 rank 仍有信息含量，尤其对 bad-side 有一定压制作用；但它更适合作为是否参与、是否降仓、是否过滤坏 entry 的 meta-feature，而不是单独开仓 event。

2. **另开新 thesis，而不是在同一 morphology 上继续调参。**
   如果继续寻找 winner-entry，需要换掉与 compression / drawdown-reversal 高重叠的机制，并在 requirement 中预注册新的 morphology independence gate。否则会重复 13A/13A3/13C 已经暴露的问题：winner lift 可以局部出现，但 utility transport 不成立。

## Output Inventory

本次 publishable tables 已生成：

- `input_artifact_audit.csv`
- `upstream_lineage_audit.csv`
- `cache_schema_adapter_audit.csv`
- `native_label_portability_audit.csv`
- `row_level_rebuild_audit.csv`
- `sparse_event_family_formula_spec.csv`
- `sparse_event_parameter_grid_audit.csv`
- `sparse_event_generation_audit.csv`
- `sparse_event_density_audit.csv`
- `sparse_event_raw_readout.csv`
- `sparse_event_badside_utility_audit.csv`
- `sparse_event_uniqueness_density_audit.csv`
- `pit_cohort_normalization_dictionary.csv`
- `pit_cohort_rank_availability_audit.csv`
- `pit_cohort_normalized_utility_readout.csv`
- `cohort_normalization_transport_audit.csv`
- `morphology_rediscovery_audit.csv`
- `validation_stress_interpretation_audit.csv`
- `search_multiplicity_audit.csv`
- `full_native_sparse_state_change_event_utility_decision.csv`

Local cache 已生成：

- `native_rebuild_panel.parquet`
- `state_change_feature_panel.parquet`
- `sparse_event_panel.parquet`
- `pit_cohort_normalized_event_panel.parquet`
