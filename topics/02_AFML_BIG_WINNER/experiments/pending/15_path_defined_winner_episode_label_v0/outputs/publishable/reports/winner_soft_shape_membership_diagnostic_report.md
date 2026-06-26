# 15C2 Winner Soft Shape Membership Diagnostic

## 1. 单行裁决

`decision_state = 15C2_winner_shape_not_real_over_baselines`；`next_allowed_requirement = none`。

15C2 的核心结论不是 "winner 没有上涨形态"，而是：用 15B frozen morphology prototype 做 soft membership 后，形态图谱有可解释结构，但 primary sharpness 没有通过 cluster-blocked baseline。也就是说，当前 soft taxonomy 更像是对 winner cluster 内路径重复结构的描述，不足以证明存在独立、可升级的 winner shape taxonomy。

| item | value |
|---|---:|
| selected_threshold_id | `up50pct` |
| prototype_fit_population_anchor_n | 56987 |
| adapter_source_priority | 1 |
| adapter_row_count | 417131 |
| adapter_duplicate_source_row_key_n | 0 |
| adapter_hard_path_type_reproducible | true |
| sharp_share_train | 0.1479 |
| sharp_share_uplift_train | -0.0087 |
| membership_sharpness_is_real_train | false |
| out_of_prototype_residual_share_train | 0.0652 |
| low_confidence_share_train | 0.0000 |
| bridge_pair_n | 1 |
| temperature_stability_status | `pass` |
| label_deployment_authorized | false |
| signal_search_authorized | false |
| model_training_authorized | false |
| separability_search_authorized | false |

## 2. 数据 Lineage 与方法边界

15C2 没有从报告文本、图像或聚合 readout 反推逐行标签。形态来源为 15B local cache `taxonomy_assignment_panel.parquet`，并过滤到 `assignment_unit = anchor_path` 后使用。该 source 是 priority 1，逐行 hard `path_type` 可由 15B frozen deterministic rule 完全复现，因此 soft membership 与 15B hard path type 同源同特征。

15C2 的方法是把 15B 的 6 个 morphology hard type 转成 soft membership：

1. 在 `up50pct / train / eligible_primary_anchor` 上拟合 scaler：train median / IQR。
2. 每个 15B hard path type 的 prototype center = 该 type 的标准化特征中位向量。
3. 每个 anchor 到各 prototype 的欧氏距离通过 `softmax(-distance / temperature)` 转成 membership vector。
4. `mixed` / `unclassified` 不进入 prototype set，只作为 hard taxonomy 的 residual 背景。
5. `out_of_prototype_residual` 单独判断 anchor 是否离所有 prototype 都远，避免 softmax 强行分类。

本实验仍是纯 descriptive label-form diagnostic。它可以使用未来 path 来描述已发生的 winner 形态，但不能把 soft membership 升级为 t0 feature、entry signal 或 separability target。

## 3. Prototype Fit 质量

5 个 active prototype 可用，`slow_grind_winner` 在 up50 train 只有 14 个 hard anchor，低于 drop threshold，因此被 dropped，不参与 softmax 维度。这个结果本身就是一个重要信号：在当前 15B hard taxonomy 下，slow-grind 不是可稳定拟合的 up50 primary prototype。

| prototype | train hard anchors | underpopulated | dropped | median distance | p90 distance | p95 distance | fit status |
|---|---:|---|---|---:|---:|---:|---|
| smooth_trend_winner | 9964 | false | false | 1.7853 | 3.8598 | 4.9505 | pass |
| stair_step_winner | 10046 | false | false | 0.9824 | 1.7139 | 2.0640 | pass |
| jump_repricing_winner | 3294 | false | false | 1.5101 | 2.7042 | 3.2239 | pass |
| choppy_reversal_winner | 1142 | false | false | 0.8958 | 1.6430 | 1.8723 | pass |
| slow_grind_winner | 14 | true | true | nan | nan | nan | dropped_not_required |
| late_rescue_winner | 9948 | false | false | 1.2958 | 2.6631 | 3.3024 | pass |

Bootstrap stability 很强，非 dropped prototype 的 top1 assignment agreement 都接近 0.998。这说明 prototype center 本身稳定；15C2 失败不是因为 prototype 拟合抖动，而是因为真实 sharpness 在 cluster-blocked baseline 下不成立。

| prototype | median center shift | p90 center shift | top1 agreement | stability |
|---|---:|---:|---:|---|
| smooth_trend_winner | 0.0039 | 0.0176 | 0.9983 | pass |
| stair_step_winner | 0.0022 | 0.0075 | 0.9989 | pass |
| jump_repricing_winner | 0.0057 | 0.0173 | 0.9981 | pass |
| choppy_reversal_winner | 0.0017 | 0.0113 | 0.9975 | pass |
| slow_grind_winner | nan | nan | nan | dropped_not_required |
| late_rescue_winner | 0.0012 | 0.0129 | 0.9989 | pass |

## 4. Primary Up50 Train Sharpness

| metric | value |
|---|---:|
| anchor_n | 56987 |
| sharp_share | 0.1479 |
| mean_membership_entropy | 0.7320 |
| mean_top1_membership | 0.4864 |
| mean_top2_membership_gap | 0.1965 |
| out_of_prototype_residual_share | 0.0652 |
| low_confidence_share | 0.0000 |

Anchor-level quantiles reveal why hard discrete taxonomy 不成立：median top1 membership 只有 0.4773，低于 0.50 sharpness threshold；median membership entropy 为 0.7474，说明多数 winner anchor 不是清晰落在单一 prototype 上，而是在多个 prototype 之间分摊。

| quantile | top1_membership | membership_entropy | top2_gap | top1_distance_percentile |
|---:|---:|---:|---:|---:|
| 0.10 | 0.3632 | 0.5482 | 0.0338 | 0.1492 |
| 0.25 | 0.4104 | 0.6473 | 0.0851 | 0.3643 |
| 0.50 | 0.4773 | 0.7474 | 0.1772 | 0.6165 |
| 0.75 | 0.5592 | 0.8262 | 0.2884 | 0.8223 |
| 0.90 | 0.6265 | 0.8791 | 0.3928 | 0.9282 |
| 0.95 | 0.6529 | 0.9064 | 0.4481 | 0.9613 |

## 5. Random / Permutation Baselines

Column shuffle 与 hard-label permutation 都显示真实数据比破坏后的数据更 sharp；但 episode-cluster-blocked shuffle 没有通过，且 random sharp share 反而略高于真实值。

| baseline | real sharp | random sharp | sharp uplift | entropy reduction | pass |
|---|---:|---:|---:|---:|---|
| column_shuffle_joint_break | 0.1479 | 0.0002 | 0.1476 | 0.1476 | true |
| hard_label_permutation_refit | 0.1479 | 0.0000 | 0.1479 | 0.2679 | true |
| episode_cluster_blocked_shuffle | 0.1479 | 0.1566 | -0.0087 | 0.0000 | false |

关键 insight：soft membership 的形态结构不是纯 softmax 几何假象，也不是 hard label 随机对应产生的假象；但是它没有脱离 winner episode cluster 的重复结构。换句话说，soft membership 目前更适合描述 "同一 winner episode 内路径体验如何混合"，不能证明 "winner 形态本身可独立分类"。

这也是最终裁决为 `15C2_winner_shape_not_real_over_baselines` 的直接原因。

## 6. Hard Type 与 Soft Mass 的差异

15B hard taxonomy 在 up50 train 下有大量 unresolved / mixed；15C2 soft membership 把这些 mixed anchor 分摊到 active prototypes 上。Soft mass 的主轴是 `stair_step`，其次是 `choppy` 与 `late_rescue`。

| prototype | soft_mass_mean | top1_share | high_membership_50 | high_membership_70 | hard_path_type_share_15b |
|---|---:|---:|---:|---:|---:|
| stair_step_winner | 0.2883 | 0.4256 | 0.1642 | 0.0006 | 0.1763 |
| choppy_reversal_winner | 0.2212 | 0.1631 | 0.0165 | 0.0000 | 0.0200 |
| late_rescue_winner | 0.1871 | 0.1665 | 0.0863 | 0.0000 | 0.1746 |
| jump_repricing_winner | 0.1518 | 0.1005 | 0.0381 | 0.0000 | 0.0578 |
| smooth_trend_winner | 0.1517 | 0.1442 | 0.1165 | 0.0023 | 0.1748 |
| slow_grind_winner | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0002 |

读法：

1. `stair_step` 的 hard share 只有 0.1763，但 soft top1 share 到 0.4256，说明大量 hard-mixed winner 在 feature space 上更接近 stair-step。
2. `choppy_reversal` hard share 只有 0.0200，但 soft mass 有 0.2212，这是最明显的 hard-to-soft reallocation。
3. `smooth_trend` hard share 与 soft mass 接近，但 high membership >= 0.70 只有 0.0023，说明真正非常纯的 smooth winner 极少。
4. `slow_grind` 在当前 up50 winner 中几乎不存在，不应作为 primary shape。

## 7. Outcome Entry Phase 结构

Outcome-relative phase 的分层最有解释力，但它使用未来 cluster interval，只能是 descriptor。

| outcome phase | anchors | top proto | sharp | entropy | residual | smooth | stair | jump | choppy | late |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mid_cluster_entry | 20538 | stair | 0.0833 | 0.7514 | 0.0668 | 0.1089 | 0.3304 | 0.1170 | 0.2532 | 0.1906 |
| early_cluster_entry | 17763 | late | 0.1420 | 0.7101 | 0.0753 | 0.0774 | 0.2353 | 0.0813 | 0.2961 | 0.3098 |
| breakout_cluster_entry | 11065 | stair | 0.1181 | 0.7683 | 0.0499 | 0.1931 | 0.3645 | 0.2053 | 0.1498 | 0.0872 |
| late_cluster_entry | 7621 | smooth | 0.3788 | 0.6782 | 0.0594 | 0.3799 | 0.1876 | 0.3321 | 0.0639 | 0.0365 |

Outcome phase 的经济含义很清楚：

1. `early_cluster_entry` 更偏 `late_rescue + choppy`，因为早进 cluster 的 anchor 会经历更多先回撤、后修复的路径。
2. `mid_cluster_entry` 与 `breakout_cluster_entry` 更偏 `stair_step`，但 entropy 仍高，说明它们不是单一路径。
3. `late_cluster_entry` 是最清晰的分层：sharp share 达 0.3788，soft mass 主要集中在 `smooth` 与 `jump`。这说明在行情后段进入的 anchor，经常只看到最后一段顺畅/跳涨的 repricing，而不是完整 episode。

这支持一个重要判断：winner path shape 很大程度是 "entry position within realized episode" 的函数，而不是一个可以忽略 entry zone 的固定 winner 类型。

## 8. PIT Entry Phase 结构

PIT phase 的区分力弱得多。所有 PIT bucket 的 top prototype 都是 `stair`，不同 phase 之间 soft mass 变化有限。

| pit phase | anchors | top proto | sharp | entropy | residual | smooth | stair | jump | choppy | late |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| undetermined_pit | 22041 | stair | 0.1541 | 0.7255 | 0.0523 | 0.1507 | 0.2843 | 0.1542 | 0.2240 | 0.1868 |
| mid_trend_pit | 13305 | stair | 0.1314 | 0.7421 | 0.0761 | 0.1425 | 0.3022 | 0.1408 | 0.2211 | 0.1934 |
| late_chase_pit | 9907 | stair | 0.1478 | 0.7445 | 0.1036 | 0.1680 | 0.2813 | 0.1593 | 0.2037 | 0.1877 |
| early_base_pit | 8368 | stair | 0.1732 | 0.7191 | 0.0485 | 0.1591 | 0.2694 | 0.1649 | 0.2256 | 0.1810 |
| breakout_pit | 3366 | stair | 0.1096 | 0.7297 | 0.0348 | 0.1284 | 0.3271 | 0.1243 | 0.2432 | 0.1769 |

Insight：PIT morphology 目前只能提供很粗的 t0 状态分桶，不能把 realized winner shape 的主要结构拆出来。它能解释一些残差差异，例如 `late_chase_pit` residual 较高、`breakout_pit` stair/choppy 较高，但不足以形成 winner shape primitive。

## 9. Path-Type 共现谱

| pair | anchor_share | mean_top2_gap | bridge_pair |
|---|---:|---:|---|
| choppy_reversal <-> stair_step | 0.3690 | 0.2266 | false |
| choppy_reversal <-> late_rescue | 0.2583 | 0.1448 | true |
| jump_repricing <-> smooth_trend | 0.2218 | 0.2148 | false |
| jump_repricing <-> stair_step | 0.1271 | 0.2011 | false |
| late_rescue <-> stair_step | 0.0130 | 0.0519 | false |
| smooth_trend <-> stair_step | 0.0109 | 0.1445 | false |

共现谱说明 winner shape 更像连续谱，而不是离散标签：

1. 最大 pair 是 `choppy <-> stair`，占 36.90%，但 gap 0.2266，未过 bridge criterion。这批 anchor 多数仍偏 stair，只是带有 choppy 成分。
2. 唯一 bridge pair 是 `choppy <-> late_rescue`，占 25.83%，gap 0.1448。这是硬分类里最容易被压成 mixed 的真实连续谱。
3. `jump <-> smooth` 占 22.18%，gap 0.2148，略高于 bridge gap threshold。这说明跳涨与顺畅趋势之间也有连续关系，但当前 rule 下还不够桥接。

如果后续只是为了描述 winner 形态，最可靠的二级结构不是 6 个离散类，而是三个连续轴：

1. `stair/choppy` continuation axis；
2. `choppy/late_rescue` rescue axis；
3. `smooth/jump` repricing axis。

## 10. Split Confirmation

| split | anchors | sharp | entropy | top1 | residual | smooth | stair | jump | choppy | late |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 56987 | 0.1479 | 0.7320 | 0.4864 | 0.0652 | 0.1517 | 0.2883 | 0.1518 | 0.2212 | 0.1871 |
| robustness | 11179 | 0.1218 | 0.7656 | 0.4724 | 0.1119 | 0.1777 | 0.3193 | 0.2127 | 0.1744 | 0.1160 |
| validation | 1065 | 0.2178 | 0.6791 | 0.5029 | 0.0817 | 0.1820 | 0.1839 | 0.2177 | 0.2046 | 0.2118 |

Split readout 的稳定性是 pass，但 composition 有明显漂移：

1. Train 以 `stair` 为主，soft mass 0.2883。
2. Robustness 仍偏 `stair`，但 `jump` 上升到 0.2127，`late` 下降到 0.1160。
3. Validation 样本很小，只有 1065 anchors，soft mass 在 `smooth/stair/jump/choppy/late` 之间更平均。

这说明 soft map 可以作为 descriptive atlas，但不能把 train composition 当作稳定可部署 label distribution。

## 11. Threshold Sensitivity

| threshold | train anchors | top proto | sharp | entropy | residual | smooth | stair | jump | choppy | late |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| up50pct | 56987 | stair | 0.1479 | 0.7320 | 0.0652 | 0.1517 | 0.2883 | 0.1518 | 0.2212 | 0.1871 |
| up100pct | 29613 | stair | 0.0688 | 0.7477 | 0.1582 | 0.0860 | 0.3494 | 0.0797 | 0.2609 | 0.2240 |
| up150pct | 16461 | stair | 0.0425 | 0.7636 | 0.3123 | 0.0655 | 0.3579 | 0.0623 | 0.2755 | 0.2387 |

阈值越高，`stair/choppy/late` 占比越高，`smooth/jump` 占比越低，但 residual 也大幅上升。Up150 的 residual share 达 0.3123，已经超过 15C2 support gate 的 0.25。

这意味着高阈值 winner 并没有在 up50 prototype space 中变得更 "干净"；相反，它们更偏离 up50 frozen prototype。不能用 up100/up150 的 descriptive pattern 反推 up50 winner taxonomy，也不能把高阈值 winner 当成更纯的训练标签。

## 12. Episode Cluster 层结构

Up50 train 共有 663 个 winner episode clusters，覆盖 56987 个 eligible anchors。Cluster-level median entropy 0.7370，和 anchor-level entropy 接近，说明混合不是单个 anchor 噪音，而是在 cluster 层也普遍存在。

| quantile | cluster_anchor_n | cluster_entropy | within_dispersion | sharp_anchor_share | residual_share |
|---:|---:|---:|---:|---:|---:|
| 0.10 | 3.0 | 0.5231 | 0.0055 | 0.0000 | 0.0000 |
| 0.25 | 13.0 | 0.6138 | 0.0174 | 0.0000 | 0.0000 |
| 0.50 | 45.0 | 0.7370 | 0.0633 | 0.1002 | 0.0000 |
| 0.75 | 130.5 | 0.8288 | 0.1157 | 0.2933 | 0.0717 |
| 0.90 | 243.8 | 0.8658 | 0.1340 | 0.6950 | 0.1817 |
| 0.95 | 299.0 | 0.8783 | 0.1406 | 0.9987 | 0.3333 |

按 cluster top prototype 聚合：

| cluster top proto | cluster_n | anchor_n | mean_entropy | mean_sharp |
|---|---:|---:|---:|---:|
| stair | 227 | 33185 | 0.8141 | 0.0831 |
| late | 166 | 9624 | 0.6384 | 0.2432 |
| choppy | 92 | 6334 | 0.7249 | 0.0371 |
| smooth | 125 | 4912 | 0.6200 | 0.5669 |
| jump | 53 | 2932 | 0.7548 | 0.1341 |

Cluster-level insight：

1. `stair` top clusters 覆盖最多 anchors，但 mean entropy 0.8141、mean sharp 0.0831，说明 stair 是最大的吸收型中心，却不是最清晰类型。
2. `smooth` top clusters 数量不多、anchor 覆盖也不大，但 mean sharp 0.5669，是最清晰的一类描述性形态。
3. `late` clusters 的 entropy 较低、sharp 较高，说明 late-rescue 在 cluster 层比 anchor-level hard taxonomy 更有辨识度。
4. 大 cluster 多数仍是高 entropy 混合体，不支持用 episode cluster medoid 直接代表整段 winner shape。

## 13. Known-Failure Overlap

| prototype | state | high-member n | high state share | baseline share | delta | status |
|---|---|---:|---:|---:|---:|---|
| smooth_trend | compression | 6638 | 0.1204 | 0.2000 | -0.0796 | independent |
| smooth_trend | drawdown_reversal | 6638 | 0.1749 | 0.2002 | -0.0253 | independent |
| stair_step | compression | 9359 | 0.1658 | 0.2000 | -0.0342 | independent |
| stair_step | drawdown_reversal | 9359 | 0.1540 | 0.2002 | -0.0462 | independent |
| jump_repricing | compression | 2169 | 0.1425 | 0.2000 | -0.0575 | independent |
| jump_repricing | drawdown_reversal | 2169 | 0.1992 | 0.2002 | -0.0010 | independent |
| choppy_reversal | compression | 942 | 0.0817 | 0.2000 | -0.1183 | independent |
| choppy_reversal | drawdown_reversal | 942 | 0.0849 | 0.2002 | -0.1153 | independent |
| late_rescue | compression | 4919 | 0.1974 | 0.2000 | -0.0026 | independent |
| late_rescue | drawdown_reversal | 4919 | 0.3049 | 0.2002 | 0.1048 | rediscovered_known_failure |
| slow_grind | compression | 0 | nan | 0.2000 | nan | inconclusive_too_sparse |
| slow_grind | drawdown_reversal | 0 | nan | 0.2002 | nan | inconclusive_too_sparse |

Known-failure 结果有两层含义：

1. Capture-friendly prototypes (`smooth`, `stair`, `slow`) 没有全部 rediscover known failure，所以 decision 不需要降级到 known-failure-overlap。
2. `late_rescue` 明确 rediscover drawdown-reversal state，delta = +0.1048。这符合经济直觉：late rescue 本质上包含先回撤、再修复的结构。因此 late-rescue 不能被解释为全新的独立上涨形态。

## 14. Temperature Stability

Temperature 只改变 softmax 尺度，不改变定性裁决。Primary temperature = 1.0。

| temperature | anchors | sharp_share | entropy | mean_top1 | decision_under_temperature | matches_primary |
|---:|---:|---:|---:|---:|---|---|
| 0.5 | 56987 | 0.6444 | 0.5116 | 0.6509 | 15C2_winner_shape_not_real_over_baselines | true |
| 1.0 | 56987 | 0.1479 | 0.7320 | 0.4864 | 15C2_winner_shape_not_real_over_baselines | true |
| 2.0 | 56987 | 0.0000 | 0.8931 | 0.3589 | 15C2_winner_shape_not_real_over_baselines | true |

数值 sharpness 对 temperature 极其敏感：0.5 时 sharp share 0.6444，2.0 时为 0.0000。但 decision 不翻转，因为 cluster-blocked baseline 已经否定 primary real-over-baseline。这进一步说明：用 softmax sharpness 做 label support 时，必须依赖 baseline decision，而不能只看某个 temperature 下的 sharp share。

## 15. Findings

1. 15C2 成功把 15B hard-mixed 的一部分结构拆开了。Up50 train 中 `stair` soft mass 0.2883、`choppy` 0.2212、`late` 0.1871，说明 winner path 不是完全无结构。

2. 但是 15C2 没能证明这种结构独立于 episode cluster repetition。Cluster-blocked baseline 的 random sharp share 为 0.1566，高于真实 0.1479，primary sharpness 不成立。

3. 当前 winner shape 更像连续谱，不像稳定离散 taxonomy。最清楚的 bridge 是 `choppy <-> late_rescue`，占 25.83%；最大吸收 pair 是 `choppy <-> stair`，占 36.90%。

4. Outcome entry zone 是最强解释变量。Late-cluster entry 的 sharp share 达 0.3788，并偏 `smooth/jump`；early-cluster entry 偏 `late/choppy`。这说明 "同一个 winner episode 从哪里进入" 会显著改变观察到的上涨形态。

5. PIT phase 不能有效替代 outcome phase。PIT 各 bucket 的 top proto 都是 `stair`，composition 变化弱，仍不能形成 t0 可分 winner shape。

6. 高阈值 winner 不是更纯的 up50 shape。Up150 的 residual share 达 0.3123，说明用 up50 prototype 去投影高阈值 winner 时，很多 anchor 已经离 prototype 太远。

7. `smooth` 是最清晰但覆盖较小的 descriptive type；`stair` 覆盖最大但 entropy 高；`late_rescue` 有解释力但部分 rediscover drawdown-reversal；`slow_grind` 在当前 up50 primary 下不可用。

## 16. Insight：后续如何划分 Winner 形态

如果目标只是把已发生的 winner 形态区分开，而不是做 t0 separability，那么当前证据支持的不是 "6 类硬标签"，而是一个两层描述框架：

第一层保留 continuous soft coordinates：

```text
winner_shape_vector =
  [smooth, stair, jump, choppy, late]
```

`slow` 暂时不进入 primary 坐标，因为 train hard anchors 只有 14。这个 vector 比 hard label 更忠实，因为大多数 winner anchor 的 median top1 membership 只有 0.4773，强行硬分会丢信息。

第二层只给研究阅读用的 coarse descriptor：

| descriptor | soft pattern | interpretation |
|---|---|---|
| smooth/jump repricing | smooth + jump high | 后段或快速 repricing，late_cluster_entry 中最明显 |
| stair/choppy continuation | stair + choppy high | 覆盖最大，但不够 sharp，是多数 mixed winner 的主轴 |
| choppy/late rescue | choppy + late high | 最清晰 bridge pair，描述先曲折再修复 |
| late rescue / drawdown repair | late high and drawdown overlap high | 有经济含义，但部分 rediscover known failure |
| out-of-prototype residual | top1 distance percentile >= 0.95 | 不应强行解释为已有 winner shape |

这套划分应该被称为 descriptive winner-shape atlas，而不是 deployable taxonomy。它可以用于解释 winner path、挑代表样本、比较不同 threshold / entry zone 的形态组成；但不能用于 label deployment、signal search 或 model training。

## 17. 最终授权边界

15C2 不授权：

- label deployment；
- signal search；
- entry / exit / holding policy；
- model training；
- separability search；
- 把 soft membership 升级为 t0 feature；
- 用 outcome phase 构造 t0 rule；
- 用 up100 / up150 的 descriptive pattern 覆盖 up50 primary decision。

最终 next step 仍为 `none`。当前最稳妥的研究判断是：winner 确实有可描述的形态连续谱，但在当前 15B feature/prototype/cluster 设置下，它还不是一个独立、稳定、可部署的离散 winner taxonomy。
