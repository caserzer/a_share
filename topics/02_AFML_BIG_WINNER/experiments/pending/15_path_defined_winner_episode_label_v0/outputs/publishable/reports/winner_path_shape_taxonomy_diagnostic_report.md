# 15B Winner Path Shape Taxonomy Diagnostic

## 1. 单行裁决

15B 的裁决状态为 `15B_no_stable_path_shape_taxonomy`。本实验只做 winner realized path shape taxonomy，不授权 signal search、entry、model、entry policy 或 label deployment。

| item | value |
|---|---:|
| decision_state | `15B_no_stable_path_shape_taxonomy` |
| next_allowed_requirement | `none` |
| eligible_train_episode_cluster_n | 919 |
| material_path_type_n | 4 |
| largest_path_type_share_train | 0.3482 |
| unclassified_share_train | 0.3580 |
| validation_material_path_type_n | 1 |
| robustness_material_path_type_n | 2 |
| representative_taxonomy_disagreement_share | 0.7320 |
| tradable_shape_share | 0.3025 |
| entropy_incrementality_status | `incremental_shape_descriptor` |

Hard gates 全部通过：input、upstream lineage、price path completeness、15A adapter、label rebuild、episode cluster、train rule fit、search accounting 都为 `pass`。失败来自 taxonomy support/stability 层：`unclassified_share_train = 0.3580` 略高于 0.35，validation 只有 1 个 material path type，representative disagreement 为 0.7320 且触发 stability extreme failure。

**结论**：当前 path-defined winner 可以被描述出若干有解释力的 realized path shape，但分类还不够稳定，不能作为下一步 prediction/separability label primitive。

## 2. 为什么 15B 可以在 15A `next_allowed_requirement = none` 后启动

15A 禁止的是 separability、signal search 和 label deployment。15B 不继承 15A 的授权字段；启动依据是 15A 已经证实 fixed-horizon label 存在 material right-censoring，而 15A 的 slow-winner morphology 否定只覆盖 t0-close 截面形态，不能否定 realized forward path shape taxonomy。

15B 因此只回答 label-form 问题：`path_winner outcome` 是否能进一步拆成可解释的 `winner path type`。它不回答 t0 是否可预测，也不产生交易规则。

## 3. 数据与审计口径

本次输入审计显示 15B 直接复用 15A row-level path-defined label cache，不从 15A 聚合表反推逐行 label。

| artifact_role | read_status | row_count | schema_status | input_gate_status |
|---|---:|---:|---|---|
| stock_daily_qfq_dir | pass | 4598 | directory | pass |
| upstream_15a_path_defined_label_cache | pass | 1226145 | pass | pass |
| upstream_15a_decision | pass | 1 | pass | pass |
| upstream_15a_winner_set_difference | pass | 12 | pass | pass |
| upstream_15a_time_to_threshold | pass | 12 | pass | pass |
| upstream_15a_episode_overlap | pass | 12 | pass | pass |
| upstream_15a_search_accounting | pass | 1 | pass | pass |
| upstream_15a_lineage | pass | 5 | pass | pass |

Primary denominator 是 `winner_episode_cluster`，不是 anchor row。15B 在 `(instrument, threshold_id)` 内做 transitive interval clustering，不按 split 先切开。跨 split cluster 保留 readout，但不进入 train-only rule fitting。

Split overlap 审计已能回填真实 cluster 起止交易日：2867 个 episode cluster 的 `cluster_start_date` 与 `cluster_end_date` 全部非空，`split_overlap_status = pass`。在 selected threshold `up50pct` 下，cluster split 分布为：train 667、validation 45、robustness 218、cross_split 529。Cross-split cluster 占 36.26%，说明长 winner interval 穿越 split 边界并不罕见，因此 train-only rule fit 必须排除这些 cluster。

## 4. Rule Fit 与 Path Shape Feature

Path shape 使用 qfq close，从 `entry_pos` 到 `first_threshold_hit_pos` inclusive。Hit detection 仍沿用 15A 的 qfq high，因此 close-based shape 与 high-based hit 分离审计。

| fit stage | fit unit | fit population_n |
|---|---|---:|
| medoid scaler | anchor_path | 57524 |
| taxonomy quantile | winner_episode_cluster | 660 |

核心 feature 解释：

- `path_efficiency = abs(net_log_return) / total_variation`，衡量净上涨相对路径摆动的效率。
- `max_drawdown_before_hit_abs` 与 `underwater_days_share` 同时刻画回撤深度和水下持续性。
- `directional_entropy_5state` 使用 entry-vol-scaled daily log return 的五状态归一化 entropy。
- `trend_line_r2` 用 log(close) 对 session index 的线性趋势拟合度。
- `top1/top3_positive_gain_share` 与 `large_up_day_count` 用于隔离 jump repricing；`large_up_day_share = large_up_day_count / segment_sessions`，只作 descriptive readout。

Validation / robustness 只应用冻结规则，不参与 quantile 拟合。

## 5. Selected Threshold `up50pct` Path Type 分布

### 5.1 Train 分布

| path_type | episode_cluster_n | share | winner_anchor_n | wick_hit_share | smooth_override_n |
|---|---:|---:|---:|---:|---:|
| unclassified_mixed_path | 320 | 0.3482 | 49432 | 0.5000 | 0 |
| late_rescue_winner | 252 | 0.2742 | 25137 | 0.5119 | 0 |
| stair_step_winner | 156 | 0.1697 | 37686 | 0.5449 | 0 |
| smooth_trend_winner | 111 | 0.1208 | 5617 | 0.6036 | 111 |
| jump_repricing_winner | 46 | 0.0501 | 1875 | 0.6304 | 0 |
| choppy_reversal_winner | 14 | 0.0152 | 1122 | 0.5714 | 0 |
| slow_grind_winner | 11 | 0.0120 | 4958 | 0.4545 | 0 |
| unclassified_short_path | 9 | 0.0098 | 40 | 0.4444 | 9 |

**Finding**：train 中最大类别是 `unclassified_mixed_path`，占 34.82%；加上 `unclassified_short_path` 后 unclassified share 为 35.80%，超过 35% gate。也就是说，虽然 taxonomy 能形成若干可解释类别，但仍有过多 winner episode 无法被当前 deterministic rule 稳定解释。

**Insight**：`smooth_trend_winner` 只有 111 个 episode cluster，占 12.08%；`stair_step_winner` 为 156 个，占 16.97%；`slow_grind_winner` 只有 11 个。真正接近“可持有捕获型”的形态总 share 为 30.25%，不是主导部分。winner outcome 的大头仍然是 mixed 或 late rescue。

### 5.2 Validation 与 robustness 分布

| split_bucket | path_type | episode_cluster_n | share | winner_anchor_n |
|---|---|---:|---:|---:|
| validation | unclassified_mixed_path | 58 | 0.3558 | 11651 |
| validation | late_rescue_winner | 45 | 0.2761 | 6552 |
| validation | stair_step_winner | 28 | 0.1718 | 8518 |
| validation | smooth_trend_winner | 13 | 0.0798 | 218 |
| validation | jump_repricing_winner | 11 | 0.0675 | 899 |
| validation | slow_grind_winner | 5 | 0.0307 | 582 |
| robustness | unclassified_mixed_path | 190 | 0.5040 | 28830 |
| robustness | stair_step_winner | 101 | 0.2679 | 24002 |
| robustness | smooth_trend_winner | 39 | 0.1034 | 1759 |
| robustness | jump_repricing_winner | 33 | 0.0875 | 2061 |

**Finding**：validation 只有 1 个 material path type，robustness 有 2 个。Validation material gate 因此失败。Robustness 的 `unclassified_mixed_path` 占比升至 50.40%，说明 out-of-train 后，规则更容易把 path 推回 mixed bucket。

**Insight**：这种失败不是简单样本不足。Validation 中 late/stair/smooth 的排序与 train 接近，但 materiality 不足；robustness 中 mixed 过高。问题更像是 taxonomy rule 对不同市场阶段的覆盖不够稳定，而不是 path shape 完全不可分。

## 6. 跨阈值敏感性

Train split 下，阈值越高，late rescue 与 stair-step 的占比越高，mixed 占比下降。

| threshold_id | top path_type | top share | second path_type | second share | smooth_share |
|---|---|---:|---|---:|---:|
| up50pct | unclassified_mixed_path | 0.3482 | late_rescue_winner | 0.2742 | 0.1208 |
| up100pct | late_rescue_winner | 0.3789 | stair_step_winner | 0.2949 | 0.0626 |
| up150pct | late_rescue_winner | 0.4394 | stair_step_winner | 0.3135 | 0.0333 |

**Finding**：`threshold_sensitivity_path_type_rank_stability = 0.7665`，rank 稳定性中等偏高，但更高阈值把样本推向更长、更曲折、更 late-rescue 的路径。

**Insight**：这说明 “winner” 的定义阈值本身会改变 path shape composition。若后续继续研究，应避免把 `up50pct` 上的 smooth / stair 结构直接外推到 `up100pct` / `up150pct`。

## 7. Path Shape 指标中位数

Train `up50pct` 各 path type 的 medoid episode feature median 如下。

| path_type | episode_n | efficiency | max_dd_abs | underwater | entropy | trend_r2 | time_to_hit | top3_gain_share | pullback_5pct |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| unclassified_mixed_path | 320 | 0.1008 | 0.2803 | 0.9291 | 0.9621 | 0.1983 | 193.0 | 0.1312 | 3.0 |
| late_rescue_winner | 252 | 0.0224 | 0.5331 | 0.9869 | 0.9535 | 0.1244 | 1032.5 | 0.0372 | 4.0 |
| stair_step_winner | 156 | 0.1208 | 0.2077 | 0.8881 | 0.9696 | 0.5706 | 157.5 | 0.1383 | 4.0 |
| smooth_trend_winner | 111 | 0.3879 | 0.0994 | 0.5926 | 0.9241 | 0.7841 | 30.0 | 0.3737 | 2.0 |
| jump_repricing_winner | 46 | 0.2831 | 0.1476 | 0.7703 | 0.9362 | 0.4634 | 45.5 | 0.3636 | 2.0 |
| choppy_reversal_winner | 14 | 0.0431 | 0.4602 | 0.9636 | 0.9856 | 0.0491 | 390.5 | 0.0669 | 5.5 |
| slow_grind_winner | 11 | 0.0700 | 0.1621 | 0.9489 | 0.9763 | 0.5959 | 730.0 | 0.0511 | 4.0 |
| unclassified_short_path | 9 | 0.8604 | 0.0282 | 0.1250 | 0.3494 | 0.9352 | 6.0 | 0.6928 | 0.0 |

**Finding**：类别之间确实有经济解释：

- `smooth_trend_winner` 的 efficiency 最高、drawdown 最浅、trend_r2 最高、time_to_hit 最短。
- `late_rescue_winner` 的 time_to_hit 中位数为 1032.5 sessions，max drawdown 达 53.31%，几乎全程 underwater。
- `choppy_reversal_winner` 的 entropy 最高、trend_r2 极低、pullback 最多。
- `stair_step_winner` 与 `slow_grind_winner` 都有较高 underwater share，但 stair-step 的 trend_r2 更高、time_to_hit 更短。

**Insight**：形态维度比 fast/slow 更有信息。尤其 `late_rescue_winner` 与 `smooth_trend_winner` 都能最终 hit threshold，但路径质量完全不同；把它们合并成同一个 winner label 会把 “可持有捕获” 和 “长期熬出结果” 混在一起。

## 8. Entropy 的作用

Entropy incrementality readout 没有发现 abs Spearman >= 0.80 的冗余 pair，因此状态为 `incremental_shape_descriptor`。

| feature_pair | train_corr | validation_corr | robustness_corr |
|---|---:|---:|---:|
| entropy::time_to_threshold | 0.1068 | 0.2034 | 0.3134 |
| entropy::path_efficiency | -0.0984 | -0.2149 | -0.2468 |
| entropy::max_drawdown_abs | 0.0639 | 0.1852 | 0.1179 |
| entropy::underwater_share | 0.0619 | 0.1629 | 0.2140 |
| entropy::top1_gain_share | -0.1071 | -0.2043 | -0.2721 |
| entropy::top3_gain_share | -0.1151 | -0.2113 | -0.2815 |
| entropy::trend_r2 | -0.0485 | -0.1393 | -0.0811 |
| entropy::realized_volatility | -0.1529 | -0.1396 | -0.2403 |
| entropy::realized_entropy_variant | 0.2906 | NA | NA |

No-entropy ablation 在 `up50pct` 下只改变少量 assignment：

| split_bucket | episode_cluster_n | changed_by_entropy_n | changed_share |
|---|---:|---:|---:|
| train | 919 | 30 | 0.0326 |
| validation | 163 | 6 | 0.0368 |
| robustness | 377 | 8 | 0.0212 |

**Finding**：entropy 不是 duration、drawdown、gain concentration 的简单换名；但它对最终分类的边际影响较小，train 只有 3.26% assignment 被 entropy 改变。

**Insight**：entropy 适合作为 path shape descriptor 和 choppy/混合路径的辅助判别，不适合单独定义 winner 类型。后续如果使用 entropy，应把它作为多特征规则中的一维，而不是直接用 “低 entropy = 好 winner”。

## 9. Wick-Hit 与 Close Path 口径风险

Hit detection 使用 qfq high，path shape 使用 qfq close。本次 selected threshold train 的总体 `wick_hit_only_share` 为 0.5299。

| path_type | wick_hit_share |
|---|---:|
| smooth_trend_winner | 0.6036 |
| jump_repricing_winner | 0.6304 |
| choppy_reversal_winner | 0.5714 |
| low_efficiency predicate hits | 0.5336 |
| all train up50 | 0.5299 |

**Finding**：wick-hit 很普遍，但没有系统性集中污染 choppy/low-efficiency 判定。`choppy_reversal_winner` 的 wick share 0.5714 高于总体 0.5299，但差距不大；low-efficiency predicate hits 为 0.5336，几乎等于总体。

**Insight**：当前 choppy 占比小且没有明显 wick-hit 污染，因此 choppy 的主要风险不是 high/close 口径差，而是样本太少、代表性不足。下一步如果重测，可把 wick-hit-only 单独隔离，但它不是当前 no-stable 裁决的主因。

## 10. Cluster 内异质性与代表 anchor 风险

Representative audit 显示 selected threshold `up50pct` 下共有 1459 个 episode cluster。Cluster 内不同 anchor path type 的分歧很高：

| metric | p25 | median | p75 | p90 |
|---|---:|---:|---:|---:|
| cluster_anchor_n | 15.0 | 63.0 | 217.5 | 388.2 |
| cluster_internal_path_type_entropy | 0.2006 | 0.6744 | 0.8070 | 0.9153 |
| cluster_dominant_path_type_share | 0.5000 | 0.6611 | 0.9679 | 1.0000 |

Cluster distinct path type count 分布：

| distinct_path_type_n | cluster_n |
|---:|---:|
| 1 | 339 |
| 2 | 217 |
| 3 | 274 |
| 4 | 233 |
| 5 | 185 |
| 6 | 148 |
| 7 | 62 |
| 8 | 1 |

**Finding**：`representative_taxonomy_disagreement_share = 0.7320`。也就是说，earliest、shortest、medoid 三种代表 anchor 经常给出不同 taxonomy。多数 cluster 内部并不是单一形态；median internal entropy 为 0.6744，p75 达 0.8070。

**Insight**：这是本次最关键的失败信号。即使 medoid 是比 earliest/shortest 更合理的代表，很多 market episode 内部仍包含不同 entry anchor 定义下的不同路径。`winner_episode_cluster` 去重解决了重复计数问题，但没有完全解决 “同一段行情对不同 entry 的路径体验不同” 这个问题。后续若继续，可能需要把 cluster 切成更细的 entry-zone / phase，而不是只选单一 medoid。

## 11. 稳定性与 Support Gate

| stability item | value |
|---|---:|
| js_divergence_train_validation | 0.0052 |
| js_divergence_train_robustness | 0.1179 |
| representative_taxonomy_disagreement_share | 0.7320 |
| cluster_internal_path_type_entropy_median | 0.6253 |
| cluster_internal_path_type_entropy_p75 | 0.7919 |
| cluster_dominant_path_type_share_median | 0.7430 |
| cluster_dominant_path_type_share_p25 | 0.5357 |
| slow_fast_path_type_composition_delta | 0.4071 |
| threshold_sensitivity_path_type_rank_stability | 0.7665 |
| stability_extreme_failure | true |

Support gate 结果：

| support gate | value |
|---|---|
| representative_disagreement_support_gate | false |
| validation_material_path_type_support_gate | false |
| robustness_material_path_type_support_gate | true |

**Finding**：split distribution 的 JS divergence 不高，说明 aggregate path type share 看起来并不剧烈漂移；真正失败来自 representative disagreement 和 validation materiality。也就是说，宏观分布表面稳定，但微观 episode 内部不稳定。

**Insight**：不能只看 base-rate 稳定性。一个 taxonomy 可以在 aggregate share 上稳定，但如果同一 episode 内不同 anchor 的 path type 高度分歧，它仍不适合作为 label primitive。15C 如果基于当前 taxonomy 直接做 separability，会把 label noise 带进 t0 prediction。

## 12. Findings Summary

1. **Path shape taxonomy 有解释力，但还不是 label**
   Smooth、late rescue、stair-step、choppy 的指标中位数符合直觉，说明 realized path shape 不是随机噪音。

2. **当前失败不是 hard data failure**
   所有 lineage/input/adapter/price path/rule fit/search accounting gates 都 pass。失败发生在 taxonomy support 与 stability 层。

3. **Unclassified share 仍过高**
   Train unclassified share 为 35.80%，略高于 35% gate；robustness 中 mixed share 达 50.40%。

4. **Cluster 内异质性是主问题**
   Representative disagreement 73.20%，说明单个 medoid 代表整个 episode 的稳定性不足。

5. **Entropy 有增量信息，但不是主裁决轴**
   Entropy 与 duration/drawdown/concentration 不高度冗余，但 no-entropy ablation 只改变 2%-4% assignment。

6. **Smooth winner 样本不够主导**
   `smooth_trend_winner` train share 只有 12.08%，tradable shape share 为 30.25%。即使将 smooth/stair/slow 视为候选，也不能认为顺畅 winner 样本充足。

## 13. 后续边界

由于当前 decision 不是 `15B_path_shape_taxonomy_supported_for_label_revision`，没有任何 path type 被授权进入 15C。`smooth_trend_winner`、`slow_grind_winner`、`stair_step_winner` 可以作为后续人工讨论候选；`jump_repricing_winner`、`late_rescue_winner`、`unclassified_*` 当前只能作为 descriptive readout。

只有当后续 taxonomy 能同时降低 unclassified share、降低 representative disagreement，并在 validation/robustness 形成足够 material path types 时，才应考虑新建 separability diagnostic。当前 path-defined winner 仍不适合作为后续预测标签直接使用。
