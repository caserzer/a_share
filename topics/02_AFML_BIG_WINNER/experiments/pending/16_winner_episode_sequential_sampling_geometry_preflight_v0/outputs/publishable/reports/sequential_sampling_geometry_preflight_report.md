# 16A Winner Episode Sequential Sampling Geometry Preflight Report

## 1. 单行裁决

`decision_state = 16A_sampling_geometry_ready_for_sequential_label_design`；`next_allowed_requirement = requirement_16b_sequential_continuation_label_design_diagnostic.md`。

16A 只回答 sampling geometry 是否足够支撑后续 label-design diagnostic。它不定义 continuation label，不计算 forward return，不产生 entry/exit/holding/cost，不训练模型，不做 separability search，也不授权 label deployment。

| item | value |
| --- | --- |
| selected_threshold_id | up50pct |
| primary_horizon_sessions | 20 |
| recommended_sampling_unit | non_overlapping_time_blocked_sampling_geometry_step |
| recommended_horizon_candidate_set | 5;8;13;15;20 |
| stability_gate_split_buckets | train;robustness |
| stress_test_split_buckets | validation |
| split_stability_evaluable | True |
| geometry_stable_across_splits | True |
| anchor_overcount_demonstrated | True |
| sequential_label_authorized | False |

## 2. 为什么 15C2 none 后仍可启动 16A

15C2 否定的是 winner 形态作为独立离散 taxonomy 或 t0 可预测标签。16A 没有复活 15B/15C/15C2 的形态线，而是把 Episode 15 反复暴露的一个隐含假设单独拿出来审计：anchor row 是否高估有效独立样本量。

启动依据记录为 `ep15_effective_sample_and_position_dependence_not_shape_taxonomy`，且 `manual_research_plan_override = True`。这意味着 16A 的对象是样本几何，不是收益、形态分类或信号搜索。`validation` 在本实验中是 stress-test readout，不进入 split-stability hard gate；稳定性 hard gate 只看 `train` 和 `robustness`。

## 3. Lineage And Fail-closed Gates

16A 的输入门全部通过：13 个 required artifact 为 `pass`，2 个 optional appendix artifact 为 `pass`。价格路径完整性也通过：所有 up50/up100/up150 的 train、robustness、validation、cross_split episode cluster 都满足 qfq 边界与 forward-session 覆盖检查。

| gate | status | evidence |
| --- | --- | --- |
| input_artifact_gate | pass | required=13 pass, optional=2 pass |
| upstream_lineage_gate | pass | 15A/15B/15C2 lineage 可读、hash 可复验 |
| price_path_completeness_gate | pass | qfq bounds 全部通过 |
| cluster_interval_adapter_gate | pass | 15B membership adapter 字段和 interval 关系通过 |
| cluster_interval_rebuild_gate | pass | 15B §6.2 transitive clustering rebuild audit 通过 |
| episode_cluster_non_overlap_gate | pass | same threshold / same instrument cluster overlap = 0 |
| geometry_consistency_gate | pass | step formula 与 16A panel 一致 |
| search_accounting_gate | pass | forward_return/search/model/deployment 授权均为 False |

价格路径读数中，`up50pct` 的 primary split cluster 覆盖为 train 667、robustness 218、validation 45，全部为 `price_path_status = pass`。`up50pct` 另有 529 个 cross_split cluster，只进入 appendix/readout，不参与 primary stability gate。

## 4. Sampling Unit And Step Formula

16A 推荐的样本单位是 `non_overlapping_time_blocked_sampling_geometry_step`。对每个 episode cluster 与 horizon `h`：

| metric | formula | use |
| --- | --- | --- |
| nonoverlap_step_n | `ceil(episode_length_sessions / h)` | sampling geometry readout，包含 partial tail |
| full_horizon_nonoverlap_step_n | `floor(episode_length_sessions / h)` | 未来 16B 可 materialize 的完整 labelable step |
| partial_tail_step_n | `1 if episode_length_sessions % h != 0 else 0` | tail/coverage readout，不进入 labelable population |
| overlap_step_n | `max(episode_length_sessions - h + 1, 0)` | uniqueness/concurrency readout |
| coverage_share | `sum(full_steps * h) / sum(episode_length_sessions)` | full-horizon coverage audit |

核心防错点：h20 train 的 `nonoverlap_step_n = 20,871`，但 `full_horizon_nonoverlap_step_n = 20,245`。差额 `626` 是 partial tail，不是可贴 label 的完整 20-session step。

## 5. Primary H20 Split Geometry

| threshold_id | split | anchor_n | episode_cluster_n | nonoverlap_step_n_h20 | full_horizon_step_n_h20 | partial_tail_step_n_h20 | anchor_to_episode_ratio | anchor_to_nonoverlap_ratio | anchor_to_full_horizon_ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| up50pct | train | 57,524 | 667 | 20,871 | 20,245 | 626 | 86.2429 | 2.7562 | 2.8414 |
| up50pct | robustness | 11,302 | 218 | 2,707 | 2,496 | 211 | 51.8440 | 4.1751 | 4.5280 |
| up50pct | validation | 1,083 | 45 | 708 | 664 | 44 | 24.0667 | 1.5297 | 1.6310 |

Finding：把 anchor row 当作独立样本会系统性高估样本数。train 上 57,524 个 anchor 最终只对应 20,245 个完整 h20 non-overlap step，anchor-to-full-horizon ratio 为 2.8414；robustness 的 overcount 更强，为 4.5280。这个现象说明 Episode 15 的很多“样本量”其实来自同一 cluster 内密集 anchor，而不是独立 episode continuation observation。

## 6. Horizon Grid

| threshold_id | split | h | episode_cluster_n | median_episode_length_sessions | step_n_nonoverlap | full_horizon_step_n | partial_tail_step_n | coverage_share |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| up50pct | train | 5 | 667 | 512.0 | 82,446 | 81,906 | 540 | 0.9968 |
| up50pct | train | 8 | 667 | 512.0 | 51,657 | 51,062 | 595 | 0.9943 |
| up50pct | train | 13 | 667 | 512.0 | 31,901 | 31,281 | 620 | 0.9898 |
| up50pct | train | 15 | 667 | 512.0 | 27,705 | 27,078 | 627 | 0.9886 |
| up50pct | train | 20 | 667 | 512.0 | 20,871 | 20,245 | 626 | 0.9855 |
| up50pct | robustness | 5 | 218 | 203.5 | 10,452 | 10,280 | 172 | 0.9917 |
| up50pct | robustness | 8 | 218 | 203.5 | 6,579 | 6,385 | 194 | 0.9855 |
| up50pct | robustness | 13 | 218 | 203.5 | 4,082 | 3,881 | 201 | 0.9734 |
| up50pct | robustness | 15 | 218 | 203.5 | 3,556 | 3,354 | 202 | 0.9706 |
| up50pct | robustness | 20 | 218 | 203.5 | 2,707 | 2,496 | 211 | 0.9631 |
| up50pct | validation | 5 | 45 | 148.0 | 2,766 | 2,729 | 37 | 0.9935 |
| up50pct | validation | 8 | 45 | 148.0 | 1,739 | 1,698 | 41 | 0.9891 |
| up50pct | validation | 13 | 45 | 148.0 | 1,080 | 1,036 | 44 | 0.9806 |
| up50pct | validation | 15 | 45 | 148.0 | 937 | 895 | 42 | 0.9775 |
| up50pct | validation | 20 | 45 | 148.0 | 708 | 664 | 44 | 0.9669 |

Finding：horizon 越长，full-horizon coverage 下降但没有崩塌。primary h20 在 train 仍保留 98.55% episode-session coverage，在 robustness 保留 96.31%，validation 保留 96.69%。这说明 h20 的样本量下降主要来自 block length 变长，而不是 tail censoring 失控。

## 7. Effective Sample And Uniqueness

overlap uniqueness 只在同一 instrument 内计算，跨 instrument window 独立。non-overlap uniqueness 按定义为 1，因此 primary effective sample 使用 full-horizon non-overlap step。

| threshold_id | split | h | episode_cluster_n | anchor_n | overlap_step_n | average_uniqueness_overlap | full_horizon_step_n | effective_sample_overlap | effective_sample_nonoverlap | effective_to_anchor_ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| up50pct | train | 20 | 667 | 57,524 | 398,255 | 0.0516 | 20,245 | 20,532.15 | 20,245.00 | 0.3519 |
| up50pct | robustness | 20 | 218 | 11,302 | 47,866 | 0.0540 | 2,496 | 2,587.10 | 2,496.00 | 0.2208 |
| up50pct | validation | 20 | 45 | 1,083 | 12,887 | 0.0530 | 664 | 683.30 | 664.00 | 0.6131 |

Insight：overlap window 的 raw count 很大，但 average uniqueness 约 0.052，只能折算到约 20k 的 effective sample。这个结果支持 16A 的关键判断：后续 continuation label 不能回到 anchor-level 或 fully-overlapping step-level 作为独立样本，应使用 non-overlapping time-blocked step。

## 8. Anchor Overcount

| threshold_id | split | h | median_overcount_ratio | p90_overcount_ratio | anchor_weighted_overcount_ratio | anchor_to_labelable_step_ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| up50pct | train | 20 | 2.5000 | 9.0000 | 2.7562 | 2.8414 |
| up50pct | robustness | 20 | 2.5000 | 9.8389 | 4.1751 | 4.5280 |
| up50pct | validation | 20 | 1.8000 | 7.5500 | 1.5297 | 1.6310 |

Finding：overcount 不是少数 outlier 造成的。train 和 robustness 的 median overcount 都是 2.5，p90 接近或超过 9。这是 cluster 内 anchor 密集化的结构性问题。

## 9. Threshold Sensitivity

| threshold_id | primary_horizon_sessions | eligible_anchor_n | episode_cluster_n | full_horizon_step_n | effective_sample_nonoverlap | effective_to_anchor_ratio | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| up50pct | 20 | 69,909 | 930 | 23,405 | 23,405.00 | 0.3348 | pass |
| up100pct | 20 | 35,534 | 479 | 15,258 | 15,258.00 | 0.4294 | pass |
| up150pct | 20 | 20,262 | 293 | 9,585 | 9,585.00 | 0.4731 | pass |

Insight：阈值越高，anchor_n 和 cluster_n 下降，但 effective_to_anchor_ratio 上升。这符合直觉：更高 threshold 留下的 winner episode 更少、更稀疏，cluster 内 anchor 重复度下降。16A 仍固定选择 `up50pct`，因为它是 15A 预注册的最低 material censoring threshold；up100/up150 只作为 sensitivity readout。

## 10. Non-overlap And Bound Audits

same-threshold / same-instrument cluster overlap audit 全部通过。全体 `up50pct` 有 1,459 个 cluster，`same_threshold_instrument_overlap_pair_n = 0`，`max_same_threshold_instrument_concurrency = 1`。`up100pct` 和 `up150pct` 同样为 0 overlap。

qfq bounds 也全部通过：cluster_start_pos 非负、cluster_end_pos 在 qfq row 内，且 eligible anchor 满足 `cluster_end_pos - entry_pos + 1 <= available_forward_sessions`。因此 16A 的 geometry 结果不是由缺失价格路径、越界 episode 或跨 split overlap 造成。

## 11. Findings And AFML Insight

16A 的核心发现不是“样本量不够”，而是“anchor-level 样本量口径不可用”。在 train 上，57,524 个 anchor 被压缩为 667 个 episode cluster 和 20,245 个 h20 full-horizon non-overlap step；有效样本仍然足够进入 label-design diagnostic，但远小于 anchor 数。

对 AFML 来说，这一步的含义是：后续 label 只能在 event-time block 上定义，并且必须保留 lineage、qfq bounds、step materialization 和 known-failed morphology audit。16A 只能授权 16B 继续设计 continuation label diagnostic，不能授权交易标签、入场规则、模型训练或部署。

## 12. Next Boundary

允许进入的唯一后续文件是 `requirement_16b_sequential_continuation_label_design_diagnostic.md`。16B 必须继续沿用 16A 的 non-overlapping full-horizon step population，不能使用 partial tail，也不能把 anchor row 当作独立样本。

## 13. Downstream Handoff Readout

16B 已按 16A 的 sampling unit 完成 handoff 验证：primary h20 materialized step count 与 16A full-horizon count 完全一致，train 为 20,245，robustness 为 2,496，validation 为 664；partial tail 没有进入 16B labelable population。

后续 16B 裁决为 `16B_continuation_label_ready_for_separability_diagnostic`，只允许进入 `requirement_16c_sequential_continuation_separability_diagnostic.md`。这不改变 16A 的边界：16A 本身仍只授权 label-design diagnostic，不授权 entry、model、separability execution 或 deployment。
